from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from src.business_tools import LISBON_TZ, RetailBusinessTools


ToolHandler = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    caveats: list[str]
    examples: list[str]
    sensitivity: str = "business"


class ToolRegistry:
    def __init__(self, tools: RetailBusinessTools) -> None:
        self.tools = tools
        self._handlers: dict[str, ToolHandler] = {
            "get_business_snapshot": self._get_business_snapshot,
            "get_today_sales": self._get_today_sales,
            "get_daily_sales_series": self._get_daily_sales_series,
            "get_month_sales": self._get_month_sales,
            "get_sales_by_category": self._get_sales_by_category,
            "get_stock_value": self._get_stock_value,
            "get_stock_value_by_category": self._get_stock_value_by_category,
            "get_low_stock": self._get_low_stock,
            "get_key_financials": self._get_key_financials,
            "get_purchase_summary": self._get_purchase_summary,
            "get_open_bills": self._get_open_bills,
            "get_open_customer_invoices": self._get_open_customer_invoices,
            "get_recent_orders": self._get_recent_orders,
            "get_profitability_snapshot": self._get_profitability_snapshot,
            "get_product_replenishment_insight": self._get_product_replenishment_insight,
            "get_sales_performance_breakdown": self._get_sales_performance_breakdown,
            "get_top_and_bottom_products": self._get_top_and_bottom_products,
            "get_margin_by_product_category_brand": self._get_margin_by_product_category_brand,
            "get_price_cost_exceptions": self._get_price_cost_exceptions,
            "get_stock_cover_and_velocity": self._get_stock_cover_and_velocity,
            "get_dead_and_aged_stock": self._get_dead_and_aged_stock,
            "get_purchase_vs_sales_analysis": self._get_purchase_vs_sales_analysis,
            "get_supplier_purchase_history": self._get_supplier_purchase_history,
            "get_working_capital_snapshot": self._get_working_capital_snapshot,
            "get_financial_risk_alerts": self._get_financial_risk_alerts,
            "get_daily_owner_briefing": self._get_daily_owner_briefing,
            "get_recommendation_for_question": self._get_recommendation_for_question,
        }
        self._definitions = self._build_definitions()

    @property
    def names(self) -> list[str]:
        return list(self._handlers.keys())

    @property
    def definitions(self) -> dict[str, ToolDefinition]:
        return self._definitions

    def describe(self) -> str:
        rows = []
        for definition in self._definitions.values():
            rows.append(
                json.dumps(
                    {
                        "name": definition.name,
                        "description": definition.description,
                        "parameters": definition.parameters,
                        "caveats": definition.caveats,
                        "examples": definition.examples,
                        "sensitivity": definition.sensitivity,
                    },
                    ensure_ascii=False,
                )
            )
        return "\n".join(rows)

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        if name not in self._handlers:
            raise ValueError(f"Unknown tool: {name}")
        validated = self._validate_arguments(name, arguments or {})
        return self._handlers[name](validated)

    def _build_definitions(self) -> dict[str, ToolDefinition]:
        days = {"type": "integer", "default": 30, "minimum": 1, "maximum": 365}
        limit = {"type": "integer", "default": 12, "minimum": 1, "maximum": 100}
        year = {"type": "integer", "required": False, "minimum": 2020, "maximum": 2100}
        month = {"type": "integer", "required": False, "minimum": 1, "maximum": 12}
        return {
            "get_business_snapshot": ToolDefinition(
                "get_business_snapshot",
                "Broad current overview for daily briefing, business health, and what to watch.",
                {},
                ["Composes several live Odoo reads."],
                ["How is the business doing?", "What should I watch today?"],
            ),
            "get_today_sales": ToolDefinition(
                "get_today_sales",
                "Current day sales total and order count from POS and sale orders.",
                {},
                [],
                ["How much did we sell today?"],
            ),
            "get_daily_sales_series": ToolDefinition(
                "get_daily_sales_series",
                "Daily sales totals and order counts for a chart or trend.",
                {"days": {**days, "default": 7, "maximum": 31}},
                [],
                ["Show sales trend for the last 7 days."],
            ),
            "get_month_sales": ToolDefinition(
                "get_month_sales",
                "Sales total and order count for a specific month or current month.",
                {"year": year, "month": month},
                [],
                ["How much did we sell this month?"],
            ),
            "get_sales_by_category": ToolDefinition(
                "get_sales_by_category",
                "Today sales grouped by product category.",
                {"limit": limit},
                ["Currently focused on POS category mix for the selected day."],
                ["What categories sold today?"],
            ),
            "get_stock_value": ToolDefinition(
                "get_stock_value",
                "Current stock valuation, quantity, availability, and location split.",
                {},
                ["Uses Odoo stock.quant valuation."],
                ["What is our stock value?"],
            ),
            "get_stock_value_by_category": ToolDefinition(
                "get_stock_value_by_category",
                "Current stock valuation grouped by product category.",
                {"limit": limit},
                [],
                ["Which categories hold the most stock value?"],
            ),
            "get_low_stock": ToolDefinition(
                "get_low_stock",
                "Sellable active products at or below a quantity threshold.",
                {"threshold": {"type": "number", "default": 2, "minimum": 0, "maximum": 100}, "limit": limit},
                [],
                ["What is low stock?"],
            ),
            "get_key_financials": ToolDefinition(
                "get_key_financials",
                "YTD sales, today/month sales, stock value, purchases, receivables, and payables.",
                {},
                [],
                ["Give me key financials."],
            ),
            "get_purchase_summary": ToolDefinition(
                "get_purchase_summary",
                "Purchase order spend and recent purchase orders.",
                {"year": year, "month": month},
                [],
                ["How much did we purchase this month?"],
            ),
            "get_open_bills": ToolDefinition(
                "get_open_bills",
                "Unpaid or partially paid vendor bills and supplier payable exposure.",
                {"limit": limit},
                ["Avoid exposing unnecessary supplier detail in public channels."],
                ["What do we owe suppliers?"],
            ),
            "get_open_customer_invoices": ToolDefinition(
                "get_open_customer_invoices",
                "Unpaid or partially paid customer invoices and receivable exposure.",
                {"limit": limit},
                ["Avoid customer personal data."],
                ["How much do customers owe us?"],
            ),
            "get_recent_orders": ToolDefinition(
                "get_recent_orders",
                "Latest POS and sale orders without customer personal data.",
                {"limit": limit},
                ["No customer PII is returned."],
                ["Show recent orders."],
            ),
            "get_profitability_snapshot": ToolDefinition(
                "get_profitability_snapshot",
                "Estimated sales, purchases, stock, working capital, and gross margin indicators.",
                {"year": year, "month": month},
                ["Profitability is estimated from product standard costs, not statutory profit."],
                ["Are we profitable this month?"],
            ),
            "get_product_replenishment_insight": ToolDefinition(
                "get_product_replenishment_insight",
                "Product-family buy/no-buy recommendation using recent sales and current stock.",
                {"query": {"type": "string", "required": True}, "days": {**days, "default": 120}, "limit": limit},
                ["Product matching depends on Odoo product naming."],
                ["Should we buy more kids wetsuits?"],
            ),
            "get_sales_performance_breakdown": ToolDefinition(
                "get_sales_performance_breakdown",
                "Sales by period, channel, category, brand, product, weekday, hour, and trend versus the previous period.",
                {"days": days, "limit": limit},
                ["Margin included here is estimated."],
                ["What is selling well over the last 30 days?"],
            ),
            "get_top_and_bottom_products": ToolDefinition(
                "get_top_and_bottom_products",
                "Best sellers, slow movers, growing products, and declining products.",
                {"days": days, "limit": limit},
                [],
                ["Which products are winning and losing?"],
            ),
            "get_margin_by_product_category_brand": ToolDefinition(
                "get_margin_by_product_category_brand",
                "Estimated gross margin by product, category, and brand using sale revenue and product standard cost.",
                {"days": days, "limit": limit},
                ["Requires reliable product standard_price values."],
                ["Where am I losing margin?"],
            ),
            "get_price_cost_exceptions": ToolDefinition(
                "get_price_cost_exceptions",
                "Products with missing cost, zero sale price, sale price below cost, or unusually low unit margin.",
                {"limit": limit, "low_margin_pct": {"type": "number", "default": 25, "minimum": 0, "maximum": 100}},
                ["Uses list price and standard cost."],
                ["Which products have bad cost or price data?"],
            ),
            "get_stock_cover_and_velocity": ToolDefinition(
                "get_stock_cover_and_velocity",
                "Current stock, recent sales velocity, days of cover, and stockout/overstock risk by product, category, and brand.",
                {"days": {**days, "default": 90}, "limit": limit},
                ["Days of cover uses recent sales velocity."],
                ["Which products are at risk of stockout?"],
            ),
            "get_dead_and_aged_stock": ToolDefinition(
                "get_dead_and_aged_stock",
                "Inventory with high value but low or no recent sales, plus stock age buckets.",
                {"days": {**days, "default": 120}, "limit": limit},
                ["Stock age depends on Odoo stock quant dates."],
                ["Which categories have too much stock?"],
            ),
            "get_purchase_vs_sales_analysis": ToolDefinition(
                "get_purchase_vs_sales_analysis",
                "Compare purchases with sales for the same period by category and brand.",
                {"days": days, "limit": limit},
                [],
                ["Are purchases too high compared with sales?"],
            ),
            "get_supplier_purchase_history": ToolDefinition(
                "get_supplier_purchase_history",
                "Recent purchase spend by supplier and recent purchase orders.",
                {"days": {**days, "default": 120, "maximum": 730}, "limit": limit},
                ["Supplier names may be commercially sensitive."],
                ["Which suppliers have we bought from recently?"],
            ),
            "get_working_capital_snapshot": ToolDefinition(
                "get_working_capital_snapshot",
                "Stock value, receivables, payables, purchases, sales, and cash pressure indicators.",
                {},
                [],
                ["How is cash tied up in stock and invoices?"],
            ),
            "get_financial_risk_alerts": ToolDefinition(
                "get_financial_risk_alerts",
                "Overdue/open exposure, purchase spikes, margin data issues, and stock risks.",
                {"limit": limit},
                ["Alerts are decision support, not accounting advice."],
                ["What financial risks need attention?"],
            ),
            "get_daily_owner_briefing": ToolDefinition(
                "get_daily_owner_briefing",
                "Composed daily briefing with sales, stock, purchases, financials, margin caveats, and priorities.",
                {},
                ["Calls multiple underlying tools."],
                ["What should Jhonny focus on today?"],
            ),
            "get_recommendation_for_question": ToolDefinition(
                "get_recommendation_for_question",
                "Higher-level recommendation tool that maps the user's question to evidence, decision, confidence, and next action.",
                {"query": {"type": "string", "required": True}, "days": {**days, "default": 90}},
                ["Uses deterministic heuristics over curated Odoo tools."],
                ["What should I do about stock this week?"],
            ),
        }

    def _validate_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        definition = self._definitions[name]
        validated: dict[str, Any] = {}
        for key, spec in definition.parameters.items():
            required = bool(spec.get("required", False))
            if key not in arguments or arguments.get(key) in (None, ""):
                if required:
                    raise ValueError(f"Tool {name} requires argument: {key}")
                if "default" in spec:
                    validated[key] = spec["default"]
                continue
            value = arguments[key]
            expected = spec.get("type")
            if expected == "integer":
                value = int(value)
            elif expected == "number":
                value = float(value)
            elif expected == "string":
                value = str(value)
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            if minimum is not None and isinstance(value, (int, float)) and value < minimum:
                value = minimum
            if maximum is not None and isinstance(value, (int, float)) and value > maximum:
                value = maximum
            validated[key] = value
        return validated

    def _get_today_sales(self, _: dict[str, Any]) -> dict[str, Any]:
        return self.tools.today_sales()

    def _get_business_snapshot(self, _: dict[str, Any]) -> dict[str, Any]:
        return self.tools.business_snapshot()

    def _get_daily_sales_series(self, arguments: dict[str, Any]) -> dict[str, Any]:
        days = int(arguments.get("days") or 7)
        return self.tools.daily_sales_series(days=days)

    def _get_month_sales(self, arguments: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(LISBON_TZ)
        year = int(arguments.get("year") or now.year)
        month = int(arguments.get("month") or now.month)
        return self.tools.month_sales(year, month)

    def _get_sales_by_category(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 12)
        return self.tools.sales_by_category(limit=limit)

    def _get_stock_value(self, _: dict[str, Any]) -> dict[str, Any]:
        return self.tools.stock_value()

    def _get_stock_value_by_category(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(arguments.get("limit") or 12)
        return self.tools.stock_value_by_category(limit=limit)

    def _get_low_stock(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        threshold = float(arguments.get("threshold") or 2)
        limit = int(arguments.get("limit") or 25)
        return self.tools.low_stock(threshold=threshold, limit=limit)

    def _get_key_financials(self, _: dict[str, Any]) -> dict[str, Any]:
        return self.tools.key_financials()

    def _get_purchase_summary(self, arguments: dict[str, Any]) -> dict[str, Any]:
        year = int(arguments["year"]) if arguments.get("year") else None
        month = int(arguments["month"]) if arguments.get("month") else None
        return self.tools.purchase_summary(year=year, month=month)

    def _get_open_bills(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 12)
        return self.tools.open_bills(limit=limit)

    def _get_open_customer_invoices(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 12)
        return self.tools.open_customer_invoices(limit=limit)

    def _get_recent_orders(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 10)
        return self.tools.recent_orders(limit=limit)

    def _get_profitability_snapshot(self, arguments: dict[str, Any]) -> dict[str, Any]:
        year = int(arguments["year"]) if arguments.get("year") else None
        month = int(arguments["month"]) if arguments.get("month") else None
        return self.tools.profitability_snapshot(year=year, month=month)

    def _get_product_replenishment_insight(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "")
        days = int(arguments.get("days") or 120)
        limit = int(arguments.get("limit") or 12)
        return self.tools.product_replenishment_insight(query=query, days=days, limit=limit)

    def _get_sales_performance_breakdown(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.sales_performance_breakdown(
            days=int(arguments.get("days") or 30),
            limit=int(arguments.get("limit") or 12),
        )

    def _get_top_and_bottom_products(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.top_and_bottom_products(
            days=int(arguments.get("days") or 30),
            limit=int(arguments.get("limit") or 10),
        )

    def _get_margin_by_product_category_brand(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.margin_by_product_category_brand(
            days=int(arguments.get("days") or 30),
            limit=int(arguments.get("limit") or 12),
        )

    def _get_price_cost_exceptions(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.price_cost_exceptions(
            limit=int(arguments.get("limit") or 25),
            low_margin_pct=float(arguments.get("low_margin_pct") or 25),
        )

    def _get_stock_cover_and_velocity(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.stock_cover_and_velocity(
            days=int(arguments.get("days") or 90),
            limit=int(arguments.get("limit") or 25),
        )

    def _get_dead_and_aged_stock(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.dead_and_aged_stock(
            days=int(arguments.get("days") or 120),
            limit=int(arguments.get("limit") or 20),
        )

    def _get_purchase_vs_sales_analysis(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.purchase_vs_sales_analysis(
            days=int(arguments.get("days") or 30),
            limit=int(arguments.get("limit") or 12),
        )

    def _get_supplier_purchase_history(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.supplier_purchase_history(
            days=int(arguments.get("days") or 120),
            limit=int(arguments.get("limit") or 12),
        )

    def _get_working_capital_snapshot(self, _: dict[str, Any]) -> dict[str, Any]:
        return self.tools.working_capital_snapshot()

    def _get_financial_risk_alerts(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.financial_risk_alerts(limit=int(arguments.get("limit") or 10))

    def _get_daily_owner_briefing(self, _: dict[str, Any]) -> dict[str, Any]:
        return self.tools.daily_owner_briefing()

    def _get_recommendation_for_question(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.recommendation_for_question(
            query=str(arguments.get("query") or ""),
            days=int(arguments.get("days") or 90),
        )
