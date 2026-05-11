from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from src.business_tools import LISBON_TZ, RetailBusinessTools
from src.llm_client import ChatMessage, LLMClient, LLMNotConfiguredError
from src.tool_registry import ToolRegistry


def format_euro(value: float | int) -> str:
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"EUR {formatted}"


def sales_chart_payload(series: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "bar",
        "title": "Sales by day",
        "subtitle": f"{series['start_date']} to {series['end_date']}",
        "x_key": "label",
        "y_key": "amount",
        "currency": "EUR",
        "points": series["points"],
    }


class RetailAgent:
    """Jhonny Surf assistant grounded in curated Odoo business tools."""

    def __init__(self, tools: RetailBusinessTools, llm: LLMClient | None = None) -> None:
        self.tools = tools
        self.registry = ToolRegistry(tools)
        self.llm = llm

    def answer(self, question: str, channel: str = "app") -> dict[str, Any]:
        normalized = question.lower().strip()

        if not normalized:
            return {
                "answer": self._help_answer(channel),
                "tool": "help",
                "intent": "help",
            }

        conversational = self._answer_conversational(question, channel)
        if conversational is not None:
            return conversational

        if self.llm is not None:
            try:
                return self._answer_with_llm(question, channel)
            except (LLMNotConfiguredError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
                fallback = self._answer_with_rules(question)
                fallback["llm_error"] = str(exc)
                fallback["llm_provider"] = "fallback"
                return fallback

        result = self._answer_with_rules(question)
        result["llm_provider"] = "not_configured"
        return result

    def _answer_with_llm(self, question: str, channel: str) -> dict[str, Any]:
        assert self.llm is not None

        tool_budget = 4
        max_iterations = 2
        tool_results: dict[str, Any] = {}
        tool_arguments: dict[str, Any] = {}
        trace: list[dict[str, Any]] = []

        for iteration in range(max_iterations):
            remaining = tool_budget - len(trace)
            if remaining <= 0:
                break

            selections = self._select_tools(
                question,
                channel,
                observed_results=tool_results,
                remaining_tools=remaining,
                allow_empty=iteration > 0,
            )
            if not selections:
                break

            new_tool_called = False
            for selection in selections[:remaining]:
                tool_name = selection["tool_name"]
                arguments = self._normalize_tool_arguments(tool_name, selection.get("arguments") or {}, question)
                trace_key = json.dumps({"tool": tool_name, "arguments": arguments}, sort_keys=True)
                if any(item.get("trace_key") == trace_key for item in trace):
                    continue
                started = time.perf_counter()
                result = self.registry.call(tool_name, arguments)
                latency_ms = round((time.perf_counter() - started) * 1000)
                tool_results[tool_name] = result
                tool_arguments[tool_name] = arguments
                trace.append(
                    {
                        "trace_key": trace_key,
                        "iteration": iteration + 1,
                        "tool": tool_name,
                        "arguments": arguments,
                        "latency_ms": latency_ms,
                        "result_summary": self._summarize_tool_result(result),
                    }
                )
                new_tool_called = True

            if not new_tool_called:
                break

        if not tool_results:
            fallback_arguments = {"query": question, "days": 90}
            started = time.perf_counter()
            result = self.registry.call("get_recommendation_for_question", fallback_arguments)
            tool_results["get_recommendation_for_question"] = result
            tool_arguments["get_recommendation_for_question"] = fallback_arguments
            trace.append(
                {
                    "trace_key": "fallback_recommendation",
                    "iteration": 1,
                    "tool": "get_recommendation_for_question",
                    "arguments": fallback_arguments,
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                    "result_summary": self._summarize_tool_result(result),
                }
            )

        public_trace = [{key: value for key, value in item.items() if key != "trace_key"} for item in trace]
        answer = self._write_answer(question, channel, tool_results, public_trace)

        return {
            "answer": answer,
            "tool": ", ".join(tool_results.keys()),
            "tool_arguments": tool_arguments,
            "data": tool_results,
            "evidence": self._evidence_summary(tool_results),
            "tool_trace": public_trace,
            "visualization": self._visualization_for_tools(tool_results),
            "llm_provider": self.llm.provider,
            "intent": "business_question",
        }

    def _select_tools(
        self,
        question: str,
        channel: str,
        observed_results: dict[str, Any],
        remaining_tools: int,
        allow_empty: bool,
    ) -> list[dict[str, Any]]:
        assert self.llm is not None
        content = self._complete_tool_selection(
            question,
            channel,
            observed_results,
            remaining_tools,
            allow_empty,
        )
        try:
            return self._parse_tool_selection(content, remaining_tools, allow_empty)
        except (ValueError, json.JSONDecodeError):
            repair_prompt = (
                "Return corrected JSON only. Use this shape: "
                '{"tools":[{"tool_name":"get_daily_owner_briefing","arguments":{}}]}. '
                "If the observed data is enough, return {\"tools\":[]}."
            )
            repaired = self.llm.complete(
                [
                    ChatMessage(role="system", content=repair_prompt),
                    ChatMessage(role="user", content=f"Bad tool JSON: {content}"),
                ],
                temperature=0,
            )
            return self._parse_tool_selection(repaired, remaining_tools, allow_empty)

    def _complete_tool_selection(
        self,
        question: str,
        channel: str,
        observed_results: dict[str, Any],
        remaining_tools: int,
        allow_empty: bool,
    ) -> str:
        assert self.llm is not None
        observed_json = json.dumps(self._compact_observed_results(observed_results), ensure_ascii=False)
        return self.llm.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "You are the planner for Jhonny Surf's AI business assistant. The store sells surf gear, wetsuits, surfboards, apparel, footwear and lifestyle goods. "
                        "Pick the BEST tool from the list below to answer Jhonny's question. "
                        "Return only valid JSON: {\"tools\":[{\"tool_name\":\"...\",\"arguments\":{...}}]}. "
                        f"Choose at most {remaining_tools} tools. Do not answer the user. "
                        "\n\nDECISION RULES (read in order — first matching rule wins):\n"
                        "1. If the question mentions a SPECIFIC product TYPE (wetsuit, fato, boots, botas, fins, leash, t-shirt, hoodie, jacket, shorts, calção, surfboard, prancha, bodyboard, backpack, mochila, bottle, garrafa, cap, hat, boné, sandals, chinelos, etc.) "
                        "or a SPECIFIC BRAND (Rip Curl, O'Neill, Billabong, Roark, Katin, FCS, Futures, Firewire, Channel Islands, Blundstone, UGG, Yeti, Patagonia, Dakine, NMD, Knockaround, Xcel, Deflow, Suntribe, etc.) "
                        "or a SPECIFIC SKU/code, USE search_products_by_name with the relevant English keyword as query. "
                        "Examples: 'quantos fatos tenho' -> search_products_by_name(query='wetsuit'). 'stock UGG' -> search_products_by_name(query='UGG'). 'tenho board shorts' -> search_products_by_name(query='boardshorts'). "
                        "2. For the WHOLE store stock value -> get_stock_value. For value BY category -> get_stock_value_by_category. \n"
                        "3. For sales TODAY -> get_today_sales. THIS WEEK or trend -> get_daily_sales_series. THIS or PAST MONTH -> get_month_sales. \n"
                        "4. For best/worst sellers -> get_top_and_bottom_products. For sales BY CATEGORY today -> get_sales_by_category. \n"
                        "5. For 'should I buy/reorder' questions about a product family -> get_product_replenishment_insight. For low stock alert -> get_low_stock. \n"
                        "6. For supplier/vendor spend -> get_supplier_purchase_history. For open vendor bills/payables -> get_open_bills. For customer receivables -> get_open_customer_invoices. \n"
                        "7. For overall snapshot, KPIs, financial health -> get_key_financials or get_business_snapshot. For daily summary -> get_daily_owner_briefing. \n"
                        "8. For margin/profitability questions -> get_margin_by_product_category_brand or get_profitability_snapshot. \n"
                        "9. For cash flow -> get_working_capital_snapshot. For risk alerts -> get_financial_risk_alerts. \n"
                        "\nPORTUGUESE-TO-ENGLISH PRODUCT GLOSSARY (the Odoo data is in English; translate before searching):\n"
                        "  fato/fatos -> wetsuit | botas -> boots | calção/calções -> shorts or boardshorts | "
                        "chinelos -> sandals | mochila -> backpack | garrafa -> bottle | óculos -> sunglasses | "
                        "boné -> cap or hat | meias -> socks | prancha/pranchas -> surfboard | sapatos -> shoes (use boots/sandals if not found) | "
                        "cinto -> belt | carteira -> wallet | toalha -> towel | vestido -> dress | saia -> skirt | poncho -> poncho | colete -> vest\n"
                        "\nALWAYS prefer search_products_by_name when there is ANY product/brand keyword in the question.\n"
                        "\nIf observed tool data is already enough and empty allowed, return {\"tools\":[]}. "
                        f"Empty tools allowed: {allow_empty}. "
                        "\n\nAvailable tools (full schema):\n"
                        f"{self.registry.describe()}"
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=(
                        f"Channel: {channel}\n"
                        f"Question: {question}\n"
                        f"Observed tool data summary: {observed_json}"
                    ),
                ),
            ],
            temperature=0,
        )

    def _parse_tool_selection(self, content: str, remaining_tools: int, allow_empty: bool) -> list[dict[str, Any]]:
        parsed = _parse_json_object(content)
        raw_tools = parsed.get("tools")
        if raw_tools is None:
            raw_tools = [{"tool_name": parsed.get("tool_name"), "arguments": parsed.get("arguments") or {}}]
        if not isinstance(raw_tools, list):
            raise ValueError("LLM tools response must be an array.")
        if not raw_tools:
            if allow_empty:
                return []
            raise ValueError("LLM must select at least one tool.")

        selections: list[dict[str, Any]] = []
        for item in raw_tools[:remaining_tools]:
            if not isinstance(item, dict):
                raise ValueError("Each selected tool must be an object.")
            tool_name = item.get("tool_name")
            if tool_name not in self.registry.names:
                raise ValueError(f"LLM selected invalid tool: {tool_name}")
            arguments = item.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError("LLM tool arguments must be an object.")
            selections.append({"tool_name": tool_name, "arguments": arguments})
        return selections

    def _write_answer(
        self,
        question: str,
        channel: str,
        tool_results: dict[str, Any],
        tool_trace: list[dict[str, Any]],
    ) -> str:
        assert self.llm is not None
        max_length = "2 frases curtas" if channel == "whatsapp" else "um parágrafo conciso"
        return self.llm.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "És o assistente de negócio da Jhonny Surf, uma loja de surf em Portugal que usa Odoo. "
                        "RESPONDE SEMPRE EM PORTUGUÊS DE PORTUGAL, mesmo que a pergunta venha em inglês ou noutra língua. "
                        "Não uses português do Brasil — usa formas europeias: 'stock' (não 'estoque'), 'fato' (não 'roupa'), 'a faturar' (não 'faturando'), 'tens' (não 'você tem'), etc. "
                        "Trata o utilizador por 'tu' (informal). "
                        "O teu trabalho é transformar dados do Odoo em decisões claras de dono de loja sobre vendas, compras, stocks, faturas, recebimentos, pagamentos, rentabilidade e prioridades operacionais. "
                        "Responde APENAS com base no JSON dos resultados das tools. NÃO inventes números. "
                        "Se os dados forem insuficientes, diz exatamente o que falta e o que ainda assim podes concluir. "
                        "Formata valores como 'EUR 1.234,56' (separador de milhares . e decimal ,) e usa 'EUR' em vez do símbolo €. "
                        "Evita dados pessoais de clientes. "
                        "Para rentabilidade, marca claramente as estimativas (não apresentes margem estimada como lucro contabilístico). "
                        "Quando fizeres uma recomendação, justifica-a com a evidência dos dados em linguagem simples. "
                        "Se a app fornecer uma visualização, resume o significado de negócio do gráfico. "
                        f"Mantém a resposta com no máximo {max_length} e termina com uma recomendação prática quando fizer sentido."
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=(
                        f"Question: {question}\n"
                        f"Tool trace: {json.dumps(tool_trace, ensure_ascii=False)}\n"
                        f"Tool result JSON: {json.dumps(tool_results, ensure_ascii=False)}"
                    ),
                ),
            ],
            temperature=0.1,
        ).strip()

    def _answer_conversational(self, question: str, channel: str) -> dict[str, Any] | None:
        normalized = question.lower().strip(" .!?")
        normalized_words = normalized.replace(",", " ").replace("?", " ").replace("!", " ").split()
        normalized_phrase = " ".join(normalized_words)
        greetings = {"hi", "hello", "hey", "ola", "olá", "bom dia", "boa tarde", "boa noite"}
        wellbeing = {"how are you", "how are you doing", "tudo bem", "como estas", "como está"}
        identity_phrases = ["who are you", "what are you", "quem es", "quem és"]
        help_phrases = ["what can you do", "help", "ajuda", "how can you help"]

        has_greeting = any(word in greetings for word in normalized_words) or normalized_phrase in greetings
        has_wellbeing = any(phrase in normalized_phrase for phrase in wellbeing)

        if has_greeting and has_wellbeing:
            return {
                "answer": "Olá Jhonny, estou pronto para ajudar com a loja. Pergunta-me o que vendeste hoje, que stock está em risco, se as compras estão altas, ou em que te deves focar.",
                "tool": "conversation",
                "intent": "small_talk",
                "llm_provider": self.llm.provider if self.llm else "not_required",
            }
        if normalized in greetings or normalized_phrase in greetings:
            return {
                "answer": "Olá Jhonny, sou o teu assistente AI da Jhonny Surf. Posso ajudar-te a verificar vendas, stock, compras, margens, riscos financeiros e o que precisa de atenção hoje.",
                "tool": "conversation",
                "intent": "greeting",
                "llm_provider": self.llm.provider if self.llm else "not_required",
            }
        if normalized in wellbeing or normalized_phrase in wellbeing:
            return {
                "answer": "Estou pronto para ajudar com a loja. Pergunta-me o que vendeste hoje, que stock está em risco, se as compras estão altas, ou em que te deves focar.",
                "tool": "conversation",
                "intent": "small_talk",
                "llm_provider": self.llm.provider if self.llm else "not_required",
            }
        if any(phrase in normalized for phrase in identity_phrases):
            return {
                "answer": "Sou o assistente AI de negócio da Jhonny Surf, ligado a tools do Odoo para te ajudar com vendas, stock, compras, financials, margens, marcas, categorias, custos e preços.",
                "tool": "conversation",
                "intent": "identity",
                "llm_provider": self.llm.provider if self.llm else "not_required",
            }
        if any(phrase == normalized or phrase in normalized for phrase in help_phrases):
            return {
                "answer": self._help_answer(channel),
                "tool": "help",
                "intent": "help",
                "llm_provider": self.llm.provider if self.llm else "not_required",
            }
        # Only ask for clarification if it's truly an empty / single-word vague greeting.
        # "Top sellers", "Stock UGG", "Vendas hoje", etc. (2 words) are legitimate business questions.
        BUSINESS_HINTS = [
            "sale", "sales", "stock", "buy", "purchase", "margin", "profit", "cost", "price",
            "venda", "vendas", "fatur", "compr", "lucro", "marg", "preco", "preço",
            "top", "best", "worst", "low", "dead", "high", "open", "owe", "due", "client", "cliente",
            "supplier", "fornecedor", "vendor", "invoice", "fatura", "bill", "report",
            "wetsuit", "fato", "boots", "botas", "shorts", "cap", "boné", "bone",
            "rip curl", "o'neill", "billabong", "fcs", "futures", "yeti", "ugg", "roark",
            "katin", "blundstone", "firewire", "patagonia", "dakine", "channel", "nmd",
            "knockaround", "xcel", "rhythm", "deflow", "fins", "leash", "deck", "boardbag",
            "surfboard", "bodyboard", "shirt", "hoodie", "jacket",
        ]
        if len(normalized.split()) <= 1 and not any(term in normalized for term in BUSINESS_HINTS):
            return {
                "answer": "Diz-me sobre que parte do negócio queres saber: vendas, stock, compras, margens, ou riscos financeiros?",
                "tool": "clarification",
                "intent": "ambiguous",
                "llm_provider": self.llm.provider if self.llm else "not_required",
            }
        return None

    def _help_answer(self, channel: str) -> str:
        if channel == "whatsapp":
            return "Posso ajudar-te com vendas, stock, compras, margens e prioridades do dia da Jhonny Surf. Experimenta: 'em que me devo focar hoje?'"
        return (
            "Sou o assistente AI de negócio da Jhonny Surf. Pergunta-me sobre performance de vendas, cobertura de stock, o que comprar, margem por marca/categoria, problemas de preço/custo, compras vs vendas, recebimentos, pagamentos, ou em que te deves focar hoje."
        )

    def _normalize_tool_arguments(self, tool_name: str, arguments: dict[str, Any], question: str) -> dict[str, Any]:
        if tool_name in {"get_product_replenishment_insight", "get_recommendation_for_question"} and not arguments.get("query"):
            arguments = {**arguments, "query": question}
        return arguments

    def _summarize_tool_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, list):
            return {"type": "list", "items": len(result)}
        if isinstance(result, dict):
            summary: dict[str, Any] = {"type": "dict", "keys": list(result.keys())[:8]}
            for key in (
                "recommendation",
                "decision",
                "decision_signal",
                "total_amount",
                "sales_total",
                "purchase_total",
                "estimated_gross_margin_pct",
            ):
                if key in result:
                    summary[key] = result[key]
            return summary
        return {"type": type(result).__name__}

    def _compact_observed_results(self, tool_results: dict[str, Any]) -> dict[str, Any]:
        return {name: self._summarize_tool_result(result) for name, result in tool_results.items()}

    def _evidence_summary(self, tool_results: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"tool": name, "summary": self._summarize_tool_result(result)}
            for name, result in tool_results.items()
        ]

    def _visualization_for_tools(self, tool_results: dict[str, Any]) -> dict[str, Any] | None:
        series = tool_results.get("get_daily_sales_series")
        if isinstance(series, dict) and isinstance(series.get("points"), list):
            return sales_chart_payload(series)
        return None

    def _answer_with_rules(self, question: str) -> dict[str, Any]:
        normalized = question.lower().strip()

        # PT->EN translation map for product types and a list of known brands.
        # If any of these appears in the question, route to search_products_by_name
        # BEFORE any of the generic stock/sales rules below.
        _PT_EN_MAP = {
            "fato": "wetsuit", "fatos": "wetsuit", "wetsuit": "wetsuit", "wetsuits": "wetsuit",
            "botas": "boots", "boots": "boots",
            "chinelos": "sandals", "sandals": "sandals", "sandalia": "sandals", "sandalias": "sandals",
            "calcao": "boardshorts", "calção": "boardshorts", "calcoes": "boardshorts", "calções": "boardshorts",
            "shorts": "shorts", "boardshorts": "boardshorts", "boardshort": "boardshorts",
            "mochila": "backpack", "mochilas": "backpack", "backpack": "backpack", "backpacks": "backpack",
            "garrafa": "bottle", "garrafas": "bottle", "bottle": "bottle", "bottles": "bottle",
            "oculos": "sunglasses", "óculos": "sunglasses", "sunglasses": "sunglasses",
            "bone": "cap", "boné": "cap", "cap": "cap", "hat": "hat", "chapeu": "hat", "chapéu": "hat",
            "meias": "socks", "socks": "socks",
            "prancha": "surfboard", "pranchas": "surfboard", "surfboard": "surfboard", "surfboards": "surfboard",
            "fins": "fins", "leash": "leash", "leashes": "leash",
            "deck": "deck", "decks": "deck", "boardbag": "boardbag", "boardbags": "boardbag",
            "bodyboard": "bodyboard", "bodyboards": "bodyboard",
            "t-shirt": "shirt", "t-shirts": "shirt", "tshirt": "shirt", "tshirts": "shirt", "shirt": "shirt",
            "hoodie": "hoodie", "hoodies": "hoodie", "jacket": "jacket", "jackets": "jacket",
            "wax": "wax", "neoprene": "neoprene", "poncho": "poncho", "ponchos": "poncho",
        }
        _BRANDS = [
            "rip curl", "ripcurl", "o'neill", "oneill", "billabong", "xcel", "patagonia",
            "fcs", "futures", "deflow", "dakine", "channel islands", "channel",
            "firewire", "nmd", "devoted", "roark", "katin", "rhythm",
            "blundstone", "ugg", "yeti", "chug", "knockaround", "suntribe",
        ]

        product_query = None
        for kw in sorted(_PT_EN_MAP, key=len, reverse=True):
            if kw in normalized:
                product_query = _PT_EN_MAP[kw]
                break
        if not product_query:
            for brand in _BRANDS:
                if brand in normalized:
                    product_query = brand
                    break

        if product_query and ("stock" in normalized or "tenho" in normalized or "have" in normalized
                              or "quantos" in normalized or "quantas" in normalized or "how many" in normalized):
            try:
                result = self.tools.search_products_by_name(query=product_query, limit=50)
                qty = result.get("total_qty_available", 0)
                value = result.get("total_retail_value_eur", 0)
                matched = result.get("match_count", 0)
                return {
                    "answer": (
                        f"Tens {qty:.0f} unidades em stock de produtos relacionados com '{product_query}' "
                        f"({matched} variantes), valor de retalho {format_euro(value)}."
                    ),
                    "tool": "search_products_by_name",
                    "data": {"search_products_by_name": result},
                }
            except Exception:
                pass

        if any(value in normalized for value in ["visual", "chart", "graph", "trend", "representation"]) and (
            "sale" in normalized or "sell" in normalized
        ):
            days = 30 if "month" in normalized or "30" in normalized else 7
            series = self.tools.daily_sales_series(days=days)
            best_day = series.get("best_day") or {}
            return {
                "answer": (
                    f"Sales over the last {series['days']} days total {format_euro(series['total_amount'])} "
                    f"from {series['total_orders']} orders. Average daily sales are "
                    f"{format_euro(series['average_daily_sales'])}; the strongest day was "
                    f"{best_day.get('label', 'n/a')} with {format_euro(best_day.get('amount') or 0)}."
                ),
                "tool": "daily_sales_series",
                "data": series,
                "visualization": sales_chart_payload(series),
            }

        if any(value in normalized for value in ["focus", "priority", "priorities", "briefing", "watch", "attention"]):
            result = self.tools.daily_owner_briefing()
            return {
                "answer": (
                    f"Today: sales are {format_euro(result['today_sales']['total_amount'])} and month sales are "
                    f"{format_euro(result['month_sales']['total_amount'])}. {result['recommendation']}"
                ),
                "tool": "daily_owner_briefing",
                "data": result,
                "evidence": [{"tool": "daily_owner_briefing", "summary": self._summarize_tool_result(result)}],
            }

        if any(value in normalized for value in ["how is", "business doing"]):
            result = self.tools.business_snapshot()
            financials = result["financials"]
            return {
                "answer": (
                    f"Jhonny Surf has {format_euro(financials['today_sales']['total_amount'])} in sales today, "
                    f"{format_euro(financials['month_sales']['total_amount'])} this month, "
                    f"and {format_euro(financials['stock']['value'])} tied in stock. "
                    "Watch low-stock items, open receivables, and purchase spend before adding more inventory."
                ),
                "tool": "business_snapshot",
                "data": result,
            }

        if any(value in normalized for value in ["buy more", "should jhonny buy", "should we buy", "replenish", "reorder"]):
            result = self.tools.product_replenishment_insight(question)
            top = result["top_products"][:3]
            product_lines = (
                " Top movers: "
                + "; ".join(
                    f"{item['sku']} sold {item['sold_qty']} units, stock {item['qty_available']}"
                    for item in top
                )
                if top
                else ""
            )
            cover = result.get("estimated_days_of_stock_cover")
            cover_text = f" Estimated stock cover is {cover} days." if cover is not None else ""
            return {
                "answer": (
                    f"{result['recommendation']} In the last {result['period_days']} days, matching products sold "
                    f"{result['total_sold_qty']} units for {format_euro(result['total_revenue'])}, with "
                    f"{result['total_available_qty']} units currently available.{cover_text}{product_lines}"
                ),
                "tool": "product_replenishment_insight",
                "data": result,
            }

        if any(value in normalized for value in ["cost", "price data", "below cost", "missing cost", "bad price"]):
            result = self.tools.price_cost_exceptions()
            return {
                "answer": (
                    f"I found {sum(result['summary'].values())} price/cost exception signals in sampled products. "
                    "Fix missing costs, zero prices, and products priced below cost before trusting margin."
                ),
                "tool": "price_cost_exceptions",
                "data": result,
            }

        if "profit" in normalized or "margin" in normalized or "profitable" in normalized:
            if "brand" in normalized or "category" in normalized or "where" in normalized or "losing" in normalized:
                result = self.tools.margin_by_product_category_brand()
                categories = result["by_category"][:3]
                lines = "; ".join(
                    f"{item['category']} margin {item['estimated_gross_margin_pct']}%"
                    for item in categories
                )
                return {
                    "answer": (
                        f"Estimated margin by category is available for review. {lines}. "
                        "Treat this as an estimate from standard cost and fix missing cost lines first."
                    ),
                    "tool": "margin_by_product_category_brand",
                    "data": result,
                }
            result = self.tools.profitability_snapshot()
            margin = result["estimated_margin"]
            margin_text = (
                f"Estimated gross profit is {format_euro(margin['estimated_gross_profit'])} "
                f"with an estimated gross margin of {margin['estimated_gross_margin_pct']}%."
                if margin.get("available")
                else "Odoo did not provide enough cost data to estimate gross margin reliably."
            )
            return {
                "answer": (
                    f"For {result['period']}, sales are {format_euro(result['sales']['total_amount'])} "
                    f"and purchases are {format_euro(result['purchases']['amount'])}. {margin_text}"
                ),
                "tool": "profitability_snapshot",
                "data": result,
            }

        if "purchase" in normalized and ("sale" in normalized or "higher" in normalized or "more" in normalized):
            result = self.tools.purchase_vs_sales_analysis()
            return {
                "answer": (
                    f"For the last {result['period_days']} days, purchases are {format_euro(result['purchase_total'])} "
                    f"and sales are {format_euro(result['sales_total'])}. "
                    f"Signal: {result['decision_signal'].replace('_', ' ')}."
                ),
                "tool": "purchase_vs_sales_analysis",
                "data": result,
            }

        if "purchase" in normalized or "buying" in normalized or "bought" in normalized:
            result = self.tools.purchase_summary()
            return {
                "answer": (
                    f"Purchases for {result['period']} are {format_euro(result['amount'])} "
                    f"across {result['count']} purchase orders."
                ),
                "tool": "purchase_summary",
                "data": result,
            }

        if "bill" in normalized or "supplier" in normalized or "payable" in normalized or "owe suppliers" in normalized:
            result = self.tools.open_bills()
            return {
                "answer": (
                    f"Open supplier bills total {format_euro(result['total_open_payable'])} "
                    f"across {result['count']} unpaid or partially paid bills."
                ),
                "tool": "open_bills",
                "data": result,
            }

        if "receivable" in normalized or "customers owe" in normalized or "customer invoices" in normalized:
            result = self.tools.open_customer_invoices()
            return {
                "answer": (
                    f"Open customer receivables total {format_euro(result['total_open_receivable'])} "
                    f"across {result['count']} unpaid or partially paid invoices."
                ),
                "tool": "open_customer_invoices",
                "data": result,
            }

        if "recent order" in normalized or "latest order" in normalized:
            result = self.tools.recent_orders()
            orders = result["orders"][:5]
            lines = [f"{item['reference']}: {format_euro(item['amount'])} ({item['source']})" for item in orders]
            return {
                "answer": "Latest orders:\n" + "\n".join(lines),
                "tool": "recent_orders",
                "data": result,
            }

        if any(value in normalized for value in ["stock cover", "stockout", "overstock", "dead stock", "too much stock"]):
            result = self.tools.stock_cover_and_velocity()
            risks = result["risk_counts"]
            return {
                "answer": (
                    f"Stock risk review found {risks['stockout_risk']} stockout risks, "
                    f"{risks['low_cover']} low-cover items, and {risks['no_recent_sales']} items with no recent sales. "
                    "Prioritize replenishment only where recent sales exist."
                ),
                "tool": "stock_cover_and_velocity",
                "data": result,
            }

        if "low stock" in normalized or "reorder" in normalized:
            items = self.tools.low_stock(limit=8)
            if not items:
                return {"answer": "No low-stock products found in the current threshold.", "tool": "low_stock"}
            lines = [
                f"{item['sku']} - {item['name']} ({item['qty_available']} units)"
                for item in items[:5]
            ]
            return {
                "answer": "Top low-stock products:\n" + "\n".join(lines),
                "tool": "low_stock",
                "data": items,
            }

        if "category" in normalized and "sale" in normalized:
            result = self.tools.sales_by_category()
            categories = result["categories"][:5]
            lines = [
                f"{item['category']}: {format_euro(item['amount'])}"
                for item in categories
            ]
            return {
                "answer": f"Today's sales by category total {format_euro(result['total'])}.\n" + "\n".join(lines),
                "tool": "sales_by_category",
                "data": result,
            }

        if "stock value" in normalized or ("stock" in normalized and "value" in normalized):
            result = self.tools.stock_value()
            return {
                "answer": (
                    f"Current stock value is {format_euro(result['value'])} "
                    f"across {result['quantity']:,.0f} units."
                ),
                "tool": "stock_value",
                "data": result,
            }

        if "stock" in normalized:
            result = self.tools.stock_value()
            return {
                "answer": (
                    f"Jhonny has {result['available']:,.0f} available units in stock. "
                    f"The Odoo stock valuation is {format_euro(result['value'])}."
                ),
                "tool": "stock",
                "data": result,
            }

        if "month" in normalized or "may" in normalized or "monthly" in normalized:
            now = datetime.now(LISBON_TZ)
            result = self.tools.month_sales(now.year, now.month)
            return {
                "answer": (
                    f"Sales this month are {format_euro(result['total_amount'])} "
                    f"from {result['total_count']} orders."
                ),
                "tool": "month_sales",
                "data": result,
            }

        if "financial" in normalized or "finance" in normalized or "business" in normalized:
            result = self.tools.key_financials()
            return {
                "answer": (
                    f"2026 sales YTD are {format_euro(result['ytd_sales']['total_amount'])}. "
                    f"Current stock value is {format_euro(result['stock']['value'])}. "
                    f"YTD purchases are {format_euro(result['ytd_purchases']['amount'])}."
                ),
                "tool": "key_financials",
                "data": result,
            }

        if "today" in normalized or "sale" in normalized or "sell" in normalized:
            result = self.tools.today_sales()
            return {
                "answer": (
                    f"Today's sales are {format_euro(result['total_amount'])} "
                    f"from {result['total_count']} orders."
                ),
                "tool": "today_sales",
                "data": result,
            }

        return {
            "answer": (
                "Posso responder a perguntas como: Quanto vendi hoje? "
                "Qual é o valor do meu stock? Que categorias venderam hoje? O que está com stock baixo?"
            ),
            "tool": "fallback",
        }


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise json.JSONDecodeError("No JSON object found", content, 0)
    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("JSON was not an object", content, 0)
    return parsed
