from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import RetailAgent  # noqa: E402
from src.tool_registry import ToolRegistry  # noqa: E402


class FakeTools:
    def daily_owner_briefing(self) -> dict[str, Any]:
        return {
            "today_sales": {"total_amount": 100.0},
            "month_sales": {"total_amount": 1000.0},
            "recommendation": "Review low-cover products before buying more.",
        }

    def price_cost_exceptions(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "summary": {
                "missing_cost": 2,
                "zero_price": 1,
                "price_below_cost": 1,
                "low_margin": 3,
            },
            "exceptions": [],
        }

    def margin_by_product_category_brand(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "by_category": [
                {"category": "Wetsuits", "estimated_gross_margin_pct": 41.2},
                {"category": "Boards", "estimated_gross_margin_pct": 28.4},
            ]
        }

    def purchase_vs_sales_analysis(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "period_days": 30,
            "purchase_total": 1200.0,
            "sales_total": 900.0,
            "decision_signal": "purchases_above_sales",
        }

    def stock_cover_and_velocity(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "risk_counts": {
                "stockout_risk": 1,
                "low_cover": 2,
                "overstock": 1,
                "no_recent_sales": 4,
                "healthy": 10,
            }
        }


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> None:
    fake_tools = FakeTools()
    agent = RetailAgent(fake_tools)  # type: ignore[arg-type]
    registry = ToolRegistry(fake_tools)  # type: ignore[arg-type]

    required_tools = {
        "get_sales_performance_breakdown",
        "get_margin_by_product_category_brand",
        "get_price_cost_exceptions",
        "get_stock_cover_and_velocity",
        "get_dead_and_aged_stock",
        "get_purchase_vs_sales_analysis",
        "get_supplier_purchase_history",
        "get_working_capital_snapshot",
        "get_financial_risk_alerts",
        "get_daily_owner_briefing",
        "get_recommendation_for_question",
    }
    missing_tools = sorted(required_tools - set(registry.names))
    if missing_tools:
        raise AssertionError(f"Missing registry tools: {missing_tools}")

    cases = [
        ("hi", "greeting", "conversation"),
        ("how are you?", "small_talk", "conversation"),
        ("Hi, how are you?", "small_talk", "conversation"),
        ("what can you do?", "help", "help"),
        ("ok", "ambiguous", "clarification"),
        ("what should Jhonny focus on today?", None, "daily_owner_briefing"),
        ("which products have bad cost or price data?", None, "price_cost_exceptions"),
        ("are purchases too high compared with sales?", None, "purchase_vs_sales_analysis"),
        ("which products have stockout risk?", None, "stock_cover_and_velocity"),
    ]

    results = []
    for question, expected_intent, expected_tool in cases:
        response = agent.answer(question)
        if expected_intent is not None:
            assert_equal(response.get("intent"), expected_intent, question)
        assert_equal(response.get("tool"), expected_tool, question)
        results.append(
            {
                "question": question,
                "intent": response.get("intent"),
                "tool": response.get("tool"),
            }
        )

    print(json.dumps({"status": "ok", "cases": results}, indent=2))


if __name__ == "__main__":
    main()
