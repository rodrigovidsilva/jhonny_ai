from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from src.odoo_client import OdooClient


LISBON_TZ = ZoneInfo("Europe/Lisbon")


def _date_range(day: date) -> tuple[str, str]:
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def _month_range(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def _year_range(year: int) -> tuple[str, str]:
    return f"{year}-01-01 00:00:00", f"{year + 1}-01-01 00:00:00"


def _many2one_name(value: Any, fallback: str = "Unknown") -> str:
    if isinstance(value, list) and len(value) > 1:
        return str(value[1])
    return fallback


def _parse_odoo_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value).replace("T", " ").split("+", 1)[0].split(".", 1)[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _sum_group(client: OdooClient, model: str, domain: list[Any], field: str) -> float:
    rows = client.execute_kw(model, "read_group", [domain, [f"{field}:sum"], []], {"lazy": False})
    return float((rows[0].get(field) if rows else 0) or 0)


def _query_terms(query: str) -> list[str]:
    terms = [part.strip().lower() for part in query.replace("?", " ").replace(",", " ").split()]
    mapped: list[str] = []
    for term in terms:
        if term in {"buy", "more", "should", "jhonny", "for", "the", "a", "an", "of", "or", "not"}:
            continue
        if term in {"kids", "kid", "children", "child", "junior", "juniors"}:
            mapped.extend(["grom", "groms", "junior", "kids", "kid"])
        elif term in {"wetsuits"}:
            mapped.append("wetsuit")
        else:
            mapped.append(term)
    return list(dict.fromkeys(mapped))


class RetailBusinessTools:
    """Curated read-only tools that the app, agent, and WhatsApp channel can share."""

    def __init__(self, client: OdooClient) -> None:
        self.client = client

    def sales_summary(self, start: str, end: str) -> dict[str, Any]:
        domain = [["date_order", ">=", start], ["date_order", "<", end]]
        pos_amount = _sum_group(self.client, "pos.order", domain, "amount_total")
        sale_amount = _sum_group(self.client, "sale.order", domain, "amount_total")
        pos_count = self.client.search_count("pos.order", domain)
        sale_count = self.client.search_count("sale.order", domain)

        return {
            "start": start,
            "end": end,
            "total_amount": round(pos_amount + sale_amount, 2),
            "total_count": pos_count + sale_count,
            "pos_amount": round(pos_amount, 2),
            "pos_count": pos_count,
            "sale_order_amount": round(sale_amount, 2),
            "sale_order_count": sale_count,
        }

    def today_sales(self, today: date | None = None) -> dict[str, Any]:
        day = today or datetime.now(LISBON_TZ).date()
        start, end = _date_range(day)
        result = self.sales_summary(start, end)
        result["date"] = day.isoformat()
        return result

    def month_sales(self, year: int, month: int) -> dict[str, Any]:
        start, end = _month_range(year, month)
        result = self.sales_summary(start, end)
        result["year"] = year
        result["month"] = month
        return result

    def monthly_sales(self, year: int) -> list[dict[str, Any]]:
        months: list[dict[str, Any]] = []
        current_month = datetime.now(LISBON_TZ).month if year == datetime.now(LISBON_TZ).year else 12
        for month in range(1, current_month + 1):
            summary = self.month_sales(year, month)
            months.append(
                {
                    "month": datetime(year, month, 1).strftime("%b"),
                    "amount": summary["total_amount"],
                    "orders": summary["total_count"],
                }
            )
        return months

    def daily_sales_series(self, days: int = 7, end_day: date | None = None) -> dict[str, Any]:
        capped_days = max(1, min(days, 31))
        final_day = end_day or datetime.now(LISBON_TZ).date()
        start_day = final_day - timedelta(days=capped_days - 1)
        points: list[dict[str, Any]] = []
        for offset in range(capped_days):
            day = start_day + timedelta(days=offset)
            summary = self.today_sales(day)
            points.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%a %d"),
                    "amount": summary["total_amount"],
                    "orders": summary["total_count"],
                    "pos_amount": summary["pos_amount"],
                    "sale_order_amount": summary["sale_order_amount"],
                }
            )

        total_amount = round(sum(point["amount"] for point in points), 2)
        total_orders = sum(int(point["orders"]) for point in points)
        best_day = max(points, key=lambda point: point["amount"]) if points else None
        return {
            "start_date": start_day.isoformat(),
            "end_date": final_day.isoformat(),
            "days": capped_days,
            "total_amount": total_amount,
            "total_orders": total_orders,
            "average_daily_sales": round(total_amount / capped_days, 2),
            "best_day": best_day,
            "points": points,
        }

    def stock_value(self) -> dict[str, Any]:
        domain = [["location_id.usage", "=", "internal"], ["quantity", ">", 0]]
        value = _sum_group(self.client, "stock.quant", domain, "value")
        quantity = _sum_group(self.client, "stock.quant", domain, "quantity")
        available = _sum_group(self.client, "stock.quant", domain, "available_quantity")

        locations = self.client.search_read(
            "stock.quant",
            domain=domain,
            fields=["location_id", "quantity", "available_quantity", "value"],
            limit=20000,
        )
        by_location: dict[str, dict[str, float]] = defaultdict(
            lambda: {"value": 0.0, "quantity": 0.0, "available": 0.0}
        )
        for row in locations:
            location = _many2one_name(row.get("location_id"), "Unknown location")
            by_location[location]["value"] += float(row.get("value") or 0)
            by_location[location]["quantity"] += float(row.get("quantity") or 0)
            by_location[location]["available"] += float(row.get("available_quantity") or 0)

        location_rows = [
            {
                "location": key,
                "value": round(item["value"], 2),
                "quantity": round(item["quantity"], 2),
                "available": round(item["available"], 2),
            }
            for key, item in by_location.items()
        ]
        location_rows.sort(key=lambda item: item["value"], reverse=True)

        return {
            "value": round(value, 2),
            "quantity": round(quantity, 2),
            "available": round(available, 2),
            "locations": location_rows,
        }

    def stock_value_by_category(self, limit: int = 12) -> list[dict[str, Any]]:
        rows = self.client.search_read(
            "stock.quant",
            domain=[["location_id.usage", "=", "internal"], ["quantity", ">", 0]],
            fields=["product_categ_id", "quantity", "available_quantity", "value"],
            limit=20000,
        )
        by_category: dict[str, dict[str, float]] = defaultdict(
            lambda: {"value": 0.0, "quantity": 0.0, "available": 0.0}
        )
        for row in rows:
            category = _many2one_name(row.get("product_categ_id"), "Uncategorized")
            by_category[category]["value"] += float(row.get("value") or 0)
            by_category[category]["quantity"] += float(row.get("quantity") or 0)
            by_category[category]["available"] += float(row.get("available_quantity") or 0)

        categories = [
            {
                "category": key,
                "value": round(item["value"], 2),
                "quantity": round(item["quantity"], 2),
                "available": round(item["available"], 2),
            }
            for key, item in by_category.items()
        ]
        categories.sort(key=lambda item: item["value"], reverse=True)
        return categories[:limit]

    def stock_analytics(self, limit: int = 12) -> dict[str, Any]:
        rows = self.client.search_read(
            "stock.quant",
            domain=[["location_id.usage", "=", "internal"], ["quantity", ">", 0]],
            fields=["product_id", "product_categ_id", "quantity", "available_quantity", "value", "in_date", "create_date"],
            limit=50000,
        )
        product_ids = sorted(
            {
                row["product_id"][0]
                for row in rows
                if isinstance(row.get("product_id"), list)
            }
        )
        brand_field = self._available_product_brand_field()
        product_fields = ["id", "name", "default_code", "categ_id", "product_tmpl_id"]
        if brand_field:
            product_fields.append(brand_field)
        products: dict[int, dict[str, Any]] = {}
        for offset in range(0, len(product_ids), 200):
            batch = product_ids[offset : offset + 200]
            for product in self.client.search_read(
                "product.product",
                domain=[["id", "in", batch]],
                fields=product_fields,
                limit=200,
            ):
                products[int(product["id"])] = product

        template_ids = sorted(
            {
                product["product_tmpl_id"][0]
                for product in products.values()
                if isinstance(product.get("product_tmpl_id"), list)
                and (not brand_field or not product.get(brand_field))
            }
        )
        template_brands: dict[int, Any] = {}
        if brand_field and template_ids:
            for offset in range(0, len(template_ids), 200):
                batch = template_ids[offset : offset + 200]
                for template in self.client.search_read(
                    "product.template",
                    domain=[["id", "in", batch]],
                    fields=["id", brand_field],
                    limit=200,
                ):
                    template_brands[int(template["id"])] = template.get(brand_field)

        by_brand: dict[str, dict[str, float]] = defaultdict(
            lambda: {"value": 0.0, "quantity": 0.0, "available": 0.0}
        )
        by_category: dict[str, dict[str, float]] = defaultdict(
            lambda: {"value": 0.0, "quantity": 0.0, "available": 0.0}
        )
        age_buckets: dict[str, dict[str, float]] = {
            "0-30 days": {"value": 0.0, "quantity": 0.0},
            "31-90 days": {"value": 0.0, "quantity": 0.0},
            "91-180 days": {"value": 0.0, "quantity": 0.0},
            "181-365 days": {"value": 0.0, "quantity": 0.0},
            "365+ days": {"value": 0.0, "quantity": 0.0},
            "Unknown age": {"value": 0.0, "quantity": 0.0},
        }
        now = datetime.now(LISBON_TZ)
        brand_aliases = self._brand_aliases()

        for row in rows:
            product_ref = row.get("product_id")
            product_id = product_ref[0] if isinstance(product_ref, list) else None
            product = (products.get(int(product_id)) if product_id else {}) or {}
            template_ref = product.get("product_tmpl_id")
            template_id = template_ref[0] if isinstance(template_ref, list) else None
            brand = self._product_brand_name(
                product,
                brand_field,
                template_brands.get(int(template_id)) if template_id else None,
                brand_aliases,
            )
            category = _many2one_name(row.get("product_categ_id") or product.get("categ_id"), "Uncategorized")
            value = float(row.get("value") or 0)
            quantity = float(row.get("quantity") or 0)
            available = float(row.get("available_quantity") or 0)
            by_brand[brand]["value"] += value
            by_brand[brand]["quantity"] += quantity
            by_brand[brand]["available"] += available
            by_category[category]["value"] += value
            by_category[category]["quantity"] += quantity
            by_category[category]["available"] += available

            stock_date = _parse_odoo_datetime(row.get("in_date") or row.get("create_date"))
            if not stock_date:
                bucket = "Unknown age"
            else:
                age_days = max(0, (now.replace(tzinfo=None) - stock_date).days)
                if age_days <= 30:
                    bucket = "0-30 days"
                elif age_days <= 90:
                    bucket = "31-90 days"
                elif age_days <= 180:
                    bucket = "91-180 days"
                elif age_days <= 365:
                    bucket = "181-365 days"
                else:
                    bucket = "365+ days"
            age_buckets[bucket]["value"] += value
            age_buckets[bucket]["quantity"] += quantity

        def ranked(source: dict[str, dict[str, float]], key_name: str) -> list[dict[str, Any]]:
            result = [
                {
                    key_name: key,
                    "value": round(item["value"], 2),
                    "quantity": round(item["quantity"], 2),
                    "available": round(item.get("available", 0), 2),
                }
                for key, item in source.items()
            ]
            result.sort(key=lambda item: item["value"], reverse=True)
            return result[:limit]

        return {
            "brand_field": brand_field,
            "by_brand": ranked(by_brand, "brand"),
            "by_category": ranked(by_category, "category"),
            "by_age": [
                {"bucket": key, "value": round(item["value"], 2), "quantity": round(item["quantity"], 2)}
                for key, item in age_buckets.items()
            ],
        }

    def sales_by_category(self, day: date | None = None, limit: int = 12) -> dict[str, Any]:
        target_day = day or datetime.now(LISBON_TZ).date()
        start, end = _date_range(target_day)
        orders = self.client.search_read(
            "pos.order",
            domain=[["date_order", ">=", start], ["date_order", "<", end]],
            fields=["id"],
            limit=10000,
        )
        order_ids = [order["id"] for order in orders]
        if not order_ids:
            return {"date": target_day.isoformat(), "total": 0.0, "categories": []}

        lines = self.client.search_read(
            "pos.order.line",
            domain=[["order_id", "in", order_ids]],
            fields=["product_id", "qty", "price_subtotal_incl"],
            limit=20000,
        )
        product_ids = sorted(
            {
                line["product_id"][0]
                for line in lines
                if isinstance(line.get("product_id"), list)
            }
        )
        products: dict[int, dict[str, Any]] = {}
        for offset in range(0, len(product_ids), 200):
            batch = product_ids[offset : offset + 200]
            for product in self.client.search_read(
                "product.product",
                domain=[["id", "in", batch]],
                fields=["id", "categ_id"],
                limit=200,
            ):
                products[int(product["id"])] = product

        by_category: dict[str, dict[str, float]] = defaultdict(
            lambda: {"amount": 0.0, "quantity": 0.0, "lines": 0.0}
        )
        for line in lines:
            product_ref = line.get("product_id")
            product_id = product_ref[0] if isinstance(product_ref, list) else None
            category = _many2one_name(products.get(product_id, {}).get("categ_id"), "Uncategorized")
            by_category[category]["amount"] += float(line.get("price_subtotal_incl") or 0)
            by_category[category]["quantity"] += float(line.get("qty") or 0)
            by_category[category]["lines"] += 1

        categories = [
            {
                "category": key,
                "amount": round(item["amount"], 2),
                "quantity": round(item["quantity"], 2),
                "lines": int(item["lines"]),
            }
            for key, item in by_category.items()
        ]
        categories.sort(key=lambda item: item["amount"], reverse=True)
        return {
            "date": target_day.isoformat(),
            "total": round(sum(item["amount"] for item in categories), 2),
            "categories": categories[:limit],
        }

    def sales_analytics_breakdowns(
        self,
        days: int | None = None,
        start_day: date | None = None,
        end_day: date | None = None,
        limit: int = 12,
    ) -> dict[str, Any]:
        final_day = end_day or datetime.now(LISBON_TZ).date()
        first_day = start_day or (final_day - timedelta(days=max(1, days or 30) - 1))
        start, end = (
            datetime.combine(first_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.combine(final_day, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )

        pos_orders = self.client.search_read(
            "pos.order",
            domain=[["date_order", ">=", start], ["date_order", "<", end]],
            fields=["id", "date_order"],
            limit=30000,
        )
        sale_orders = self.client.search_read(
            "sale.order",
            domain=[["date_order", ">=", start], ["date_order", "<", end]],
            fields=["id", "date_order"],
            limit=30000,
        )
        pos_order_dates = {int(row["id"]): row.get("date_order") for row in pos_orders}
        sale_order_dates = {int(row["id"]): row.get("date_order") for row in sale_orders}

        pos_lines = (
            self.client.search_read(
                "pos.order.line",
                domain=[["order_id", "in", list(pos_order_dates)]],
                fields=["order_id", "product_id", "qty", "price_subtotal_incl"],
                limit=80000,
            )
            if pos_order_dates
            else []
        )
        sale_lines = (
            self.client.search_read(
                "sale.order.line",
                domain=[["order_id", "in", list(sale_order_dates)]],
                fields=["order_id", "product_id", "product_uom_qty", "price_subtotal"],
                limit=80000,
            )
            if sale_order_dates
            else []
        )

        product_ids = sorted(
            {
                line["product_id"][0]
                for line in [*pos_lines, *sale_lines]
                if isinstance(line.get("product_id"), list)
            }
        )
        brand_field = self._available_product_brand_field()
        brand_aliases = self._brand_aliases()
        product_fields = ["id", "name", "default_code", "categ_id", "standard_price", "product_tmpl_id"]
        if brand_field:
            product_fields.append(brand_field)

        products: dict[int, dict[str, Any]] = {}
        for offset in range(0, len(product_ids), 200):
            batch = product_ids[offset : offset + 200]
            for product in self.client.search_read(
                "product.product",
                domain=[["id", "in", batch]],
                fields=product_fields,
                limit=200,
            ):
                products[int(product["id"])] = product
        template_ids = sorted(
            {
                product["product_tmpl_id"][0]
                for product in products.values()
                if isinstance(product.get("product_tmpl_id"), list)
                and (not brand_field or not product.get(brand_field))
            }
        )
        template_brands: dict[int, Any] = {}
        if brand_field and template_ids:
            for offset in range(0, len(template_ids), 200):
                batch = template_ids[offset : offset + 200]
                for template in self.client.search_read(
                    "product.template",
                    domain=[["id", "in", batch]],
                    fields=["id", brand_field],
                    limit=200,
                ):
                    template_brands[int(template["id"])] = template.get(brand_field)

        by_category: dict[str, dict[str, float]] = defaultdict(
            lambda: {"amount": 0.0, "quantity": 0.0, "lines": 0.0}
        )
        by_brand: dict[str, dict[str, float]] = defaultdict(
            lambda: {"amount": 0.0, "quantity": 0.0, "lines": 0.0}
        )
        by_product: dict[str, dict[str, float]] = defaultdict(
            lambda: {"amount": 0.0, "quantity": 0.0, "lines": 0.0}
        )
        by_weekday: dict[str, dict[str, float]] = defaultdict(
            lambda: {"amount": 0.0, "quantity": 0.0, "orders": 0.0}
        )
        by_hour: dict[int, dict[str, float]] = defaultdict(
            lambda: {"amount": 0.0, "quantity": 0.0, "orders": 0.0}
        )
        estimated_cost = 0.0
        costed_lines = 0

        def add_line(line: dict[str, Any], order_dates: dict[int, Any], amount_field: str, qty_field: str) -> None:
            nonlocal estimated_cost, costed_lines
            order_ref = line.get("order_id")
            order_id = order_ref[0] if isinstance(order_ref, list) else None
            order_dt = _parse_odoo_datetime(order_dates.get(int(order_id))) if order_id else None
            product_ref = line.get("product_id")
            product_id = product_ref[0] if isinstance(product_ref, list) else None
            product = (products.get(int(product_id)) if product_id else {}) or {}
            amount = float(line.get(amount_field) or 0)
            qty = float(line.get(qty_field) or 0)
            standard_cost = float(product.get("standard_price") or 0)
            category = _many2one_name(product.get("categ_id"), "Uncategorized")
            template_ref = product.get("product_tmpl_id")
            template_id = template_ref[0] if isinstance(template_ref, list) else None
            brand = self._product_brand_name(
                product,
                brand_field,
                template_brands.get(int(template_id)) if template_id else None,
                brand_aliases,
            )
            product_name = str(product.get("name") or _many2one_name(product_ref, "Unknown product"))
            if standard_cost:
                estimated_cost += standard_cost * qty
                costed_lines += 1

            by_category[category]["amount"] += amount
            by_category[category]["quantity"] += qty
            by_category[category]["lines"] += 1
            by_brand[brand]["amount"] += amount
            by_brand[brand]["quantity"] += qty
            by_brand[brand]["lines"] += 1
            by_product[product_name]["amount"] += amount
            by_product[product_name]["quantity"] += qty
            by_product[product_name]["lines"] += 1

            if order_dt:
                weekday = order_dt.strftime("%a")
                by_weekday[weekday]["amount"] += amount
                by_weekday[weekday]["quantity"] += qty
                by_weekday[weekday]["orders"] += 1
                by_hour[order_dt.hour]["amount"] += amount
                by_hour[order_dt.hour]["quantity"] += qty
                by_hour[order_dt.hour]["orders"] += 1

        for line in pos_lines:
            add_line(line, pos_order_dates, "price_subtotal_incl", "qty")
        for line in sale_lines:
            add_line(line, sale_order_dates, "price_subtotal", "product_uom_qty")

        def ranked_rows(source: dict[str, dict[str, float]], label_key: str) -> list[dict[str, Any]]:
            rows = [
                {
                    label_key: key,
                    "amount": round(value["amount"], 2),
                    "quantity": round(value["quantity"], 2),
                    "lines": int(value.get("lines", value.get("orders", 0))),
                }
                for key, value in source.items()
            ]
            rows.sort(key=lambda item: item["amount"], reverse=True)
            return rows[:limit]

        weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        hour_rows = [
            {
                "hour": hour,
                "label": f"{hour:02d}:00",
                "amount": round(by_hour[hour]["amount"], 2),
                "quantity": round(by_hour[hour]["quantity"], 2),
                "orders": int(by_hour[hour]["orders"]),
            }
            for hour in range(24)
        ]
        weekday_rows = [
            {
                "weekday": weekday,
                "amount": round(by_weekday[weekday]["amount"], 2),
                "quantity": round(by_weekday[weekday]["quantity"], 2),
                "orders": int(by_weekday[weekday]["orders"]),
            }
            for weekday in weekday_order
        ]

        total_amount = round(sum(item["amount"] for item in by_category.values()), 2)
        estimated_gross_profit = round(total_amount - estimated_cost, 2)
        estimated_margin_pct = round((estimated_gross_profit / total_amount * 100) if total_amount else 0.0, 1)

        return {
            "start_date": first_day.isoformat(),
            "end_date": final_day.isoformat(),
            "brand_field": brand_field,
            "total_amount": total_amount,
            "estimated_cost": round(estimated_cost, 2),
            "estimated_gross_profit": estimated_gross_profit,
            "estimated_gross_margin_pct": estimated_margin_pct,
            "costed_lines": costed_lines,
            "sales_by_category": ranked_rows(by_category, "category"),
            "sales_by_brand": ranked_rows(by_brand, "brand"),
            "sales_by_product": ranked_rows(by_product, "product"),
            "sales_by_weekday": weekday_rows,
            "sales_by_hour": hour_rows,
        }

    def _available_product_brand_field(self) -> str | None:
        candidates = [
            "x_studio_marcas",
            "product_brand_id",
            "brand_id",
            "x_brand_id",
            "x_studio_brand",
            "x_studio_brand_id",
            "manufacturer_id",
        ]
        try:
            fields = self.client.execute_kw(
                "product.product",
                "fields_get",
                [candidates],
                {"attributes": ["string", "type"]},
            )
            for field in candidates:
                if field in fields:
                    return field
        except Exception:
            return None
        return None

    def _product_brand_name(
        self,
        product: dict[str, Any],
        brand_field: str | None,
        template_brand: Any = None,
        brand_aliases: dict[str, str] | None = None,
    ) -> str:
        if brand_field and product.get(brand_field):
            value = product.get(brand_field)
            if isinstance(value, list) and len(value) > 1:
                return self._normalize_brand_name(str(value[1]))
            if isinstance(value, str):
                return self._normalize_brand_name(value)
        if template_brand:
            if isinstance(template_brand, list) and len(template_brand) > 1:
                return self._normalize_brand_name(str(template_brand[1]))
            if isinstance(template_brand, str):
                return self._normalize_brand_name(template_brand)
        inferred = self._infer_brand_from_product_text(product, brand_aliases or {})
        if inferred:
            return inferred
        return "Unknown brand"

    def _normalize_brand_name(self, value: str) -> str:
        raw = value.strip()
        compact = "".join(ch for ch in raw.upper() if ch.isalnum())
        canonical = {
            "ONEILL": "O'Neill",
            "RIPCURL": "Rip Curl",
            "BILLABONG": "Billabong",
            "ROARK": "Roark",
            "YETI": "Yeti",
            "OCEANEARTH": "Ocean & Earth",
            "CHANNELISLAND": "Channel Islands",
            "QUIKSILVER": "Quiksilver",
            "QUICKSILVER": "Quiksilver",
            "CSKINS": "C-Skins",
            "FIREWIRE": "Firewire",
            "FCS": "FCS",
            "JSS": "JSS",
            "NMD": "NMD",
            "NSP": "NSP",
            "XCEL": "XCEL",
        }
        if compact in canonical:
            return canonical[compact]
        if raw.isupper() and len(raw) <= 4:
            return raw
        return raw.title()

    def _brand_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        try:
            rows = self.client.search_read("x_marcas", fields=["display_name", "x_name"], limit=500)
        except Exception:
            rows = []
        for row in rows:
            brand = self._normalize_brand_name(str(row.get("x_name") or row.get("display_name") or ""))
            key = "".join(ch for ch in brand.upper() if ch.isalnum())
            if key:
                aliases[key] = brand
        aliases.update(
            {
                "ONEILL": "O'Neill",
                "ONEIL": "O'Neill",
                "RIPCURL": "Rip Curl",
                "DB": "Db",
                "D B": "Db",
                "DBBAGS": "Db",
                "CHANNELISLANDS": "Channel Islands",
                "CHANNELISLAND": "Channel Islands",
                "OCEANEARTH": "Ocean & Earth",
            }
        )
        return aliases

    def _infer_brand_from_product_text(self, product: dict[str, Any], brand_aliases: dict[str, str]) -> str | None:
        text = " ".join(
            str(value or "")
            for value in [
                product.get("name"),
                product.get("default_code"),
                _many2one_name(product.get("product_tmpl_id"), ""),
            ]
        )
        compact_text = "".join(ch for ch in text.upper() if ch.isalnum())
        words = text.upper().replace("-", " ").replace("_", " ").replace("/", " ").split()
        for alias, brand in sorted(brand_aliases.items(), key=lambda item: len(item[0]), reverse=True):
            if len(alias) <= 2:
                if alias in words:
                    return brand
                continue
            if alias in compact_text:
                return brand
        return None

    def low_stock(self, threshold: float = 2, limit: int = 25) -> list[dict[str, Any]]:
        products = self.client.search_read(
            "product.product",
            domain=[
                ["sale_ok", "=", True],
                ["active", "=", True],
                ["qty_available", ">", 0],
                ["qty_available", "<=", threshold],
            ],
            fields=["default_code", "name", "qty_available", "virtual_available", "list_price"],
            limit=limit,
        )
        return [
            {
                "sku": product.get("default_code") or "no-sku",
                "name": product.get("name"),
                "qty_available": product.get("qty_available"),
                "forecast": product.get("virtual_available"),
                "price": product.get("list_price"),
            }
            for product in products
        ]

    def search_products_by_name(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Search active products whose name OR sku matches the query (case-insensitive).
        Returns total stock + price across all matching variants. Ideal for questions like
        "how many wetsuits do I have?" or "do I sell board shorts?".

        Tries multiple variants of the query (original, singular, individual words) and
        merges results to be robust to Portuguese/English plurals and multi-word queries.
        """
        clean_query = (query or "").strip()
        if not clean_query:
            return {"query": "", "match_count": 0, "total_qty_available": 0.0, "products": []}

        # Build query variants to try (most specific first).
        variants: list[str] = []
        seen: set[str] = set()

        def add(q: str) -> None:
            q = q.strip()
            if q and len(q) >= 3 and q.lower() not in seen:
                seen.add(q.lower())
                variants.append(q)

        add(clean_query)
        # Singular forms (drop trailing s if length > 3) — handles plurals in PT/EN.
        if clean_query.lower().endswith("s") and len(clean_query) > 3:
            add(clean_query[:-1])
        # Individual words (>= 3 chars), useful for multi-word queries.
        for word in clean_query.split():
            add(word)
            if word.lower().endswith("s") and len(word) > 3:
                add(word[:-1])

        # Try each variant in order, stop on first that returns results.
        products: list[dict[str, Any]] = []
        used_variant = clean_query
        for variant in variants:
            products = self.client.search_read(
                "product.product",
                domain=[
                    ["active", "=", True],
                    "|",
                    ["name", "ilike", variant],
                    ["default_code", "ilike", variant],
                ],
                fields=["default_code", "name", "qty_available", "virtual_available", "list_price", "categ_id"],
                limit=limit,
            )
            if products:
                used_variant = variant
                break

        total_qty = sum(float(p.get("qty_available") or 0) for p in products)
        total_value = sum(float(p.get("qty_available") or 0) * float(p.get("list_price") or 0) for p in products)

        return {
            "query": clean_query,
            "matched_variant": used_variant,
            "match_count": len(products),
            "total_qty_available": round(total_qty, 2),
            "total_retail_value_eur": round(total_value, 2),
            "products": [
                {
                    "sku": product.get("default_code") or "no-sku",
                    "name": product.get("name"),
                    "category": (product.get("categ_id") or [None, None])[1],
                    "qty_available": product.get("qty_available"),
                    "forecast": product.get("virtual_available"),
                    "price_eur": product.get("list_price"),
                }
                for product in products
            ],
        }

    def product_replenishment_insight(
        self,
        query: str,
        days: int = 120,
        limit: int = 12,
    ) -> dict[str, Any]:
        terms = _query_terms(query)
        primary = "wetsuit" if "wetsuit" in terms else (terms[0] if terms else query)
        products = self.client.search_read(
            "product.product",
            domain=[["sale_ok", "=", True], ["active", "=", True], ["name", "ilike", primary]],
            fields=["id", "default_code", "name", "qty_available", "virtual_available", "list_price"],
            limit=500,
        )

        def matches(product: dict[str, Any]) -> bool:
            haystack = f"{product.get('default_code') or ''} {product.get('name') or ''}".lower()
            if any(term in {"grom", "groms", "junior", "kids", "kid"} for term in terms):
                return primary in haystack and any(
                    child_term in haystack for child_term in ("grom", "groms", "junior", "kids", "kid")
                )
            return all(term in haystack for term in terms[:3]) if terms else True

        matched_products = [product for product in products if matches(product)]
        product_ids = [int(product["id"]) for product in matched_products]
        end = datetime.now(LISBON_TZ)
        start = end - timedelta(days=days)
        start_text = start.strftime("%Y-%m-%d %H:%M:%S")
        end_text = end.strftime("%Y-%m-%d %H:%M:%S")

        by_product: dict[int, dict[str, Any]] = {}
        for product in matched_products:
            product_id = int(product["id"])
            by_product[product_id] = {
                "sku": product.get("default_code") or "no-sku",
                "name": product.get("name"),
                "qty_available": float(product.get("qty_available") or 0),
                "forecast": float(product.get("virtual_available") or 0),
                "list_price": float(product.get("list_price") or 0),
                "sold_qty": 0.0,
                "revenue": 0.0,
                "lines": 0,
            }

        if product_ids:
            pos_orders = self.client.search_read(
                "pos.order",
                domain=[["date_order", ">=", start_text], ["date_order", "<", end_text]],
                fields=["id"],
                limit=20000,
            )
            pos_order_ids = [row["id"] for row in pos_orders]
            if pos_order_ids:
                for line in self.client.search_read(
                    "pos.order.line",
                    domain=[["order_id", "in", pos_order_ids], ["product_id", "in", product_ids]],
                    fields=["product_id", "qty", "price_subtotal_incl"],
                    limit=40000,
                ):
                    product_ref = line.get("product_id")
                    product_id = product_ref[0] if isinstance(product_ref, list) else None
                    if product_id in by_product:
                        by_product[product_id]["sold_qty"] += float(line.get("qty") or 0)
                        by_product[product_id]["revenue"] += float(line.get("price_subtotal_incl") or 0)
                        by_product[product_id]["lines"] += 1

            sale_orders = self.client.search_read(
                "sale.order",
                domain=[["date_order", ">=", start_text], ["date_order", "<", end_text]],
                fields=["id"],
                limit=20000,
            )
            sale_order_ids = [row["id"] for row in sale_orders]
            if sale_order_ids:
                for line in self.client.search_read(
                    "sale.order.line",
                    domain=[["order_id", "in", sale_order_ids], ["product_id", "in", product_ids]],
                    fields=["product_id", "product_uom_qty", "price_subtotal"],
                    limit=40000,
                ):
                    product_ref = line.get("product_id")
                    product_id = product_ref[0] if isinstance(product_ref, list) else None
                    if product_id in by_product:
                        by_product[product_id]["sold_qty"] += float(line.get("product_uom_qty") or 0)
                        by_product[product_id]["revenue"] += float(line.get("price_subtotal") or 0)
                        by_product[product_id]["lines"] += 1

        rows = list(by_product.values())
        rows.sort(key=lambda item: (item["sold_qty"], item["revenue"]), reverse=True)
        total_sold = sum(row["sold_qty"] for row in rows)
        total_revenue = sum(row["revenue"] for row in rows)
        total_available = sum(row["qty_available"] for row in rows)
        daily_velocity = total_sold / days if days else 0
        days_of_cover = total_available / daily_velocity if daily_velocity else None

        if not rows:
            recommendation = "No matching sellable products were found in Odoo, so do not place a buy until the product naming/category is checked."
            decision = "check_data"
        elif total_sold <= 0:
            recommendation = "Do not buy more yet. Odoo shows matching stock but no recent sales for this product family in the review window."
            decision = "do_not_buy_yet"
        elif days_of_cover is not None and days_of_cover < 45:
            recommendation = "Buy a controlled replenishment. Recent sales exist and available stock cover is below 45 days."
            decision = "buy_controlled"
        elif total_available <= 2 and total_sold > 0:
            recommendation = "Buy a small replenishment. Sales exist and current available stock is very low."
            decision = "buy_small"
        else:
            recommendation = "Do not overbuy now. Sales exist, but available stock appears to cover near-term demand."
            decision = "hold_or_small_buy"

        return {
            "query": query,
            "period_days": days,
            "matched_products": len(rows),
            "total_sold_qty": round(total_sold, 2),
            "total_revenue": round(total_revenue, 2),
            "total_available_qty": round(total_available, 2),
            "estimated_days_of_stock_cover": round(days_of_cover, 1) if days_of_cover is not None else None,
            "decision": decision,
            "recommendation": recommendation,
            "top_products": [
                {
                    **row,
                    "sold_qty": round(row["sold_qty"], 2),
                    "revenue": round(row["revenue"], 2),
                    "qty_available": round(row["qty_available"], 2),
                    "forecast": round(row["forecast"], 2),
                }
                for row in rows[:limit]
            ],
        }

    def sales_performance_breakdown(self, days: int = 30, limit: int = 12) -> dict[str, Any]:
        capped_days = max(1, min(days, 365))
        final_day = datetime.now(LISBON_TZ).date()
        first_day = final_day - timedelta(days=capped_days - 1)
        previous_final = first_day - timedelta(days=1)
        previous_first = previous_final - timedelta(days=capped_days - 1)
        current_start, current_end = (
            datetime.combine(first_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.combine(final_day, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        previous_start, previous_end = (
            datetime.combine(previous_first, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.combine(previous_final, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        current = self.sales_summary(current_start, current_end)
        previous = self.sales_summary(previous_start, previous_end)
        current_amount = float(current["total_amount"])
        previous_amount = float(previous["total_amount"])
        change_amount = current_amount - previous_amount
        change_pct = (change_amount / previous_amount * 100) if previous_amount else None
        analytics = self.sales_analytics_breakdowns(
            start_day=first_day,
            end_day=final_day,
            limit=limit,
        )
        return {
            "period_days": capped_days,
            "current_period": {
                "start_date": first_day.isoformat(),
                "end_date": final_day.isoformat(),
                "sales": current,
            },
            "previous_period": {
                "start_date": previous_first.isoformat(),
                "end_date": previous_final.isoformat(),
                "sales": previous,
            },
            "trend": {
                "change_amount": round(change_amount, 2),
                "change_pct": round(change_pct, 1) if change_pct is not None else None,
                "direction": "up" if change_amount > 0 else ("down" if change_amount < 0 else "flat"),
            },
            "breakdowns": {
                "by_category": analytics["sales_by_category"],
                "by_brand": analytics["sales_by_brand"],
                "by_product": analytics["sales_by_product"],
                "by_weekday": analytics["sales_by_weekday"],
                "by_hour": analytics["sales_by_hour"],
            },
            "margin_estimate": {
                "estimated_cost": analytics["estimated_cost"],
                "estimated_gross_profit": analytics["estimated_gross_profit"],
                "estimated_gross_margin_pct": analytics["estimated_gross_margin_pct"],
                "costed_lines": analytics["costed_lines"],
                "caveat": "Gross margin is estimated from product standard costs, not statutory profit.",
            },
        }

    def top_and_bottom_products(self, days: int = 30, limit: int = 10) -> dict[str, Any]:
        capped_days = max(1, min(days, 365))
        final_day = datetime.now(LISBON_TZ).date()
        first_day = final_day - timedelta(days=capped_days - 1)
        previous_final = first_day - timedelta(days=1)
        previous_first = previous_final - timedelta(days=capped_days - 1)
        current = self.sales_analytics_breakdowns(start_day=first_day, end_day=final_day, limit=max(limit * 3, 20))
        previous = self.sales_analytics_breakdowns(start_day=previous_first, end_day=previous_final, limit=max(limit * 3, 20))
        current_products = current["sales_by_product"]
        previous_by_product = {row["product"]: row for row in previous["sales_by_product"]}

        trend_rows: list[dict[str, Any]] = []
        for row in current_products:
            previous_amount = float(previous_by_product.get(row["product"], {}).get("amount") or 0)
            current_amount = float(row.get("amount") or 0)
            trend_rows.append(
                {
                    **row,
                    "previous_amount": round(previous_amount, 2),
                    "change_amount": round(current_amount - previous_amount, 2),
                }
            )

        growth = sorted(trend_rows, key=lambda item: item["change_amount"], reverse=True)
        decline = sorted(trend_rows, key=lambda item: item["change_amount"])
        slow_movers = sorted(
            [row for row in current_products if float(row.get("quantity") or 0) <= 2],
            key=lambda item: (float(item.get("amount") or 0), float(item.get("quantity") or 0)),
        )
        return {
            "period_days": capped_days,
            "start_date": first_day.isoformat(),
            "end_date": final_day.isoformat(),
            "top_products": current_products[:limit],
            "slow_movers": slow_movers[:limit],
            "growth_products": growth[:limit],
            "declining_products": decline[:limit],
            "caveat": "Product trend is based on available POS and sale order lines in the selected window.",
        }

    def margin_by_product_category_brand(self, days: int = 30, limit: int = 12) -> dict[str, Any]:
        capped_days = max(1, min(days, 365))
        final_day = datetime.now(LISBON_TZ).date()
        first_day = final_day - timedelta(days=capped_days - 1)
        start, end = (
            datetime.combine(first_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.combine(final_day, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        lines, products, brand_field, template_brands, brand_aliases = self._sales_product_rows(start, end)
        by_product: dict[str, dict[str, float]] = defaultdict(
            lambda: {"revenue": 0.0, "quantity": 0.0, "estimated_cost": 0.0, "lines": 0.0, "missing_cost_lines": 0.0}
        )
        by_category: dict[str, dict[str, float]] = defaultdict(
            lambda: {"revenue": 0.0, "quantity": 0.0, "estimated_cost": 0.0, "lines": 0.0, "missing_cost_lines": 0.0}
        )
        by_brand: dict[str, dict[str, float]] = defaultdict(
            lambda: {"revenue": 0.0, "quantity": 0.0, "estimated_cost": 0.0, "lines": 0.0, "missing_cost_lines": 0.0}
        )

        for line in lines:
            product = products.get(int(line["product_id"]), {})
            qty = float(line["quantity"])
            revenue = float(line["revenue"])
            standard_cost = float(product.get("standard_price") or 0)
            estimated_cost = standard_cost * qty
            category = _many2one_name(product.get("categ_id"), "Uncategorized")
            template_ref = product.get("product_tmpl_id")
            template_id = template_ref[0] if isinstance(template_ref, list) else None
            brand = self._product_brand_name(
                product,
                brand_field,
                template_brands.get(int(template_id)) if template_id else None,
                brand_aliases,
            )
            product_label = f"{product.get('default_code') or 'no-sku'} - {product.get('name') or line['product_name']}"
            for bucket in (by_product[product_label], by_category[category], by_brand[brand]):
                bucket["revenue"] += revenue
                bucket["quantity"] += qty
                bucket["estimated_cost"] += estimated_cost
                bucket["lines"] += 1
                if standard_cost <= 0:
                    bucket["missing_cost_lines"] += 1

        def ranked(source: dict[str, dict[str, float]], label_key: str) -> list[dict[str, Any]]:
            rows = []
            for key, item in source.items():
                gross_profit = item["revenue"] - item["estimated_cost"]
                margin_pct = (gross_profit / item["revenue"] * 100) if item["revenue"] else 0.0
                rows.append(
                    {
                        label_key: key,
                        "revenue": round(item["revenue"], 2),
                        "quantity": round(item["quantity"], 2),
                        "estimated_cost": round(item["estimated_cost"], 2),
                        "estimated_gross_profit": round(gross_profit, 2),
                        "estimated_gross_margin_pct": round(margin_pct, 1),
                        "lines": int(item["lines"]),
                        "missing_cost_lines": int(item["missing_cost_lines"]),
                    }
                )
            rows.sort(key=lambda item: item["revenue"], reverse=True)
            return rows[:limit]

        return {
            "period_days": capped_days,
            "start_date": first_day.isoformat(),
            "end_date": final_day.isoformat(),
            "brand_field": brand_field,
            "by_product": ranked(by_product, "product"),
            "by_category": ranked(by_category, "category"),
            "by_brand": ranked(by_brand, "brand"),
            "caveats": [
                "Gross margin is estimated from product standard costs.",
                "Rows with missing cost lines should be reviewed before making pricing decisions.",
            ],
        }

    def price_cost_exceptions(self, limit: int = 25, low_margin_pct: float = 25.0) -> dict[str, Any]:
        brand_field = self._available_product_brand_field()
        brand_aliases = self._brand_aliases()
        fields = ["id", "default_code", "name", "list_price", "standard_price", "categ_id", "product_tmpl_id"]
        if brand_field:
            fields.append(brand_field)
        products = self.client.search_read(
            "product.product",
            domain=[["sale_ok", "=", True], ["active", "=", True]],
            fields=fields,
            limit=10000,
        )
        template_ids = [
            product["product_tmpl_id"][0]
            for product in products
            if brand_field and isinstance(product.get("product_tmpl_id"), list) and not product.get(brand_field)
        ]
        template_brands = self._template_brands(brand_field, template_ids)
        exceptions: list[dict[str, Any]] = []
        summary = {"missing_cost": 0, "zero_price": 0, "price_below_cost": 0, "low_margin": 0}
        for product in products:
            price = float(product.get("list_price") or 0)
            cost = float(product.get("standard_price") or 0)
            reasons: list[str] = []
            if cost <= 0:
                reasons.append("missing_cost")
            if price <= 0:
                reasons.append("zero_price")
            if price > 0 and cost > price:
                reasons.append("price_below_cost")
            margin_pct = ((price - cost) / price * 100) if price else None
            if margin_pct is not None and cost > 0 and margin_pct < low_margin_pct:
                reasons.append("low_margin")
            if not reasons:
                continue
            for reason in set(reasons):
                summary[reason] += 1
            template_ref = product.get("product_tmpl_id")
            template_id = template_ref[0] if isinstance(template_ref, list) else None
            exceptions.append(
                {
                    "sku": product.get("default_code") or "no-sku",
                    "product": product.get("name"),
                    "category": _many2one_name(product.get("categ_id"), "Uncategorized"),
                    "brand": self._product_brand_name(
                        product,
                        brand_field,
                        template_brands.get(int(template_id)) if template_id else None,
                        brand_aliases,
                    ),
                    "sale_price": round(price, 2),
                    "cost": round(cost, 2),
                    "estimated_unit_margin_pct": round(margin_pct, 1) if margin_pct is not None else None,
                    "reasons": reasons,
                }
            )
        exceptions.sort(key=lambda item: (len(item["reasons"]), item["sale_price"]), reverse=True)
        return {
            "checked_products": len(products),
            "summary": summary,
            "exceptions": exceptions[:limit],
            "caveat": "Uses product list price and standard cost; actual discounts and accounting costs may differ.",
        }

    def stock_cover_and_velocity(self, days: int = 90, limit: int = 25) -> dict[str, Any]:
        capped_days = max(1, min(days, 365))
        final_day = datetime.now(LISBON_TZ).date()
        first_day = final_day - timedelta(days=capped_days - 1)
        start, end = (
            datetime.combine(first_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.combine(final_day, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        lines, products_from_sales, brand_field, template_brands, brand_aliases = self._sales_product_rows(start, end)
        fields = ["id", "default_code", "name", "qty_available", "virtual_available", "list_price", "standard_price", "categ_id", "product_tmpl_id"]
        if brand_field:
            fields.append(brand_field)
        stock_products = self.client.search_read(
            "product.product",
            domain=[["sale_ok", "=", True], ["active", "=", True], ["qty_available", ">", 0]],
            fields=fields,
            limit=10000,
        )
        products = {int(product["id"]): product for product in stock_products}
        products.update(products_from_sales)
        missing_template_ids = [
            product["product_tmpl_id"][0]
            for product in products.values()
            if brand_field and isinstance(product.get("product_tmpl_id"), list) and not product.get(brand_field)
        ]
        template_brands.update(self._template_brands(brand_field, missing_template_ids))
        sold_by_product: dict[int, dict[str, float]] = defaultdict(lambda: {"sold_qty": 0.0, "revenue": 0.0})
        for line in lines:
            product_id = int(line["product_id"])
            sold_by_product[product_id]["sold_qty"] += float(line["quantity"])
            sold_by_product[product_id]["revenue"] += float(line["revenue"])

        rows: list[dict[str, Any]] = []
        by_category: dict[str, dict[str, float]] = defaultdict(lambda: {"stock_value": 0.0, "available": 0.0, "sold_qty": 0.0})
        by_brand: dict[str, dict[str, float]] = defaultdict(lambda: {"stock_value": 0.0, "available": 0.0, "sold_qty": 0.0})
        for product_id, product in products.items():
            available = float(product.get("qty_available") or 0)
            if available <= 0 and product_id not in sold_by_product:
                continue
            sold_qty = sold_by_product[product_id]["sold_qty"]
            daily_velocity = sold_qty / capped_days
            days_of_cover = available / daily_velocity if daily_velocity else None
            cost = float(product.get("standard_price") or 0)
            stock_value_estimate = available * cost
            category = _many2one_name(product.get("categ_id"), "Uncategorized")
            template_ref = product.get("product_tmpl_id")
            template_id = template_ref[0] if isinstance(template_ref, list) else None
            brand = self._product_brand_name(
                product,
                brand_field,
                template_brands.get(int(template_id)) if template_id else None,
                brand_aliases,
            )
            if sold_qty > 0 and available <= 2:
                risk = "stockout_risk"
                action = "Replenish or check incoming stock."
            elif sold_qty > 0 and days_of_cover is not None and days_of_cover < 30:
                risk = "low_cover"
                action = "Consider a controlled buy."
            elif sold_qty == 0 and available > 0:
                risk = "no_recent_sales"
                action = "Do not buy more; review merchandising or discount."
            elif days_of_cover is not None and days_of_cover > 180:
                risk = "overstock"
                action = "Hold purchases and consider promotion."
            else:
                risk = "healthy"
                action = "Monitor."
            row = {
                "sku": product.get("default_code") or "no-sku",
                "product": product.get("name"),
                "category": category,
                "brand": brand,
                "available_qty": round(available, 2),
                "forecast_qty": round(float(product.get("virtual_available") or 0), 2),
                "sold_qty": round(sold_qty, 2),
                "revenue": round(sold_by_product[product_id]["revenue"], 2),
                "daily_velocity": round(daily_velocity, 3),
                "estimated_days_of_cover": round(days_of_cover, 1) if days_of_cover is not None else None,
                "stock_value_estimate": round(stock_value_estimate, 2),
                "risk": risk,
                "recommended_action": action,
            }
            rows.append(row)
            by_category[category]["stock_value"] += stock_value_estimate
            by_category[category]["available"] += available
            by_category[category]["sold_qty"] += sold_qty
            by_brand[brand]["stock_value"] += stock_value_estimate
            by_brand[brand]["available"] += available
            by_brand[brand]["sold_qty"] += sold_qty

        risk_order = {"stockout_risk": 0, "low_cover": 1, "overstock": 2, "no_recent_sales": 3, "healthy": 4}
        rows.sort(key=lambda item: (risk_order.get(item["risk"], 9), -float(item["stock_value_estimate"])))

        def grouped(source: dict[str, dict[str, float]], label_key: str) -> list[dict[str, Any]]:
            result = [
                {
                    label_key: key,
                    "stock_value_estimate": round(value["stock_value"], 2),
                    "available_qty": round(value["available"], 2),
                    "sold_qty": round(value["sold_qty"], 2),
                }
                for key, value in source.items()
            ]
            result.sort(key=lambda item: item["stock_value_estimate"], reverse=True)
            return result[:12]

        return {
            "period_days": capped_days,
            "start_date": first_day.isoformat(),
            "end_date": final_day.isoformat(),
            "products": rows[:limit],
            "by_category": grouped(by_category, "category"),
            "by_brand": grouped(by_brand, "brand"),
            "risk_counts": {
                key: sum(1 for row in rows if row["risk"] == key)
                for key in ["stockout_risk", "low_cover", "overstock", "no_recent_sales", "healthy"]
            },
            "caveat": "Stock cover uses recent sales velocity and current on-hand quantity.",
        }

    def dead_and_aged_stock(self, days: int = 120, limit: int = 20) -> dict[str, Any]:
        cover = self.stock_cover_and_velocity(days=days, limit=500)
        dead_stock = [
            row
            for row in cover["products"]
            if row["risk"] in {"no_recent_sales", "overstock"} and float(row["available_qty"] or 0) > 0
        ]
        dead_stock.sort(key=lambda item: float(item.get("stock_value_estimate") or 0), reverse=True)
        return {
            "period_days": cover["period_days"],
            "dead_or_overstocked_products": dead_stock[:limit],
            "stock_age": self.stock_analytics(limit=limit).get("by_age", []),
            "recommended_action": "Avoid replenishing these products until sales velocity improves; review pricing, display, or promotion.",
        }

    def purchase_vs_sales_analysis(self, days: int = 30, limit: int = 12) -> dict[str, Any]:
        capped_days = max(1, min(days, 365))
        final_day = datetime.now(LISBON_TZ).date()
        first_day = final_day - timedelta(days=capped_days - 1)
        start, end = (
            datetime.combine(first_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.combine(final_day, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        sales = self.sales_summary(start, end)
        sales_breakdown = self.sales_analytics_breakdowns(start_day=first_day, end_day=final_day, limit=limit)
        purchase_orders = self.client.search_read(
            "purchase.order",
            domain=[["date_order", ">=", start], ["date_order", "<", end], ["state", "in", ["purchase", "done"]]],
            fields=["id", "name", "date_order", "amount_total", "partner_id"],
            limit=30000,
        )
        order_ids = [row["id"] for row in purchase_orders]
        purchase_lines = (
            self.client.search_read(
                "purchase.order.line",
                domain=[["order_id", "in", order_ids]],
                fields=["order_id", "product_id", "product_qty", "price_subtotal"],
                limit=80000,
            )
            if order_ids
            else []
        )
        product_ids = sorted(
            {
                line["product_id"][0]
                for line in purchase_lines
                if isinstance(line.get("product_id"), list)
            }
        )
        products, brand_field, template_brands, brand_aliases = self._product_map(product_ids)
        purchase_by_category: dict[str, dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "quantity": 0.0, "lines": 0.0})
        purchase_by_brand: dict[str, dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "quantity": 0.0, "lines": 0.0})
        for line in purchase_lines:
            product_ref = line.get("product_id")
            product_id = product_ref[0] if isinstance(product_ref, list) else None
            product = products.get(int(product_id), {}) if product_id else {}
            category = _many2one_name(product.get("categ_id"), "Uncategorized")
            template_ref = product.get("product_tmpl_id")
            template_id = template_ref[0] if isinstance(template_ref, list) else None
            brand = self._product_brand_name(
                product,
                brand_field,
                template_brands.get(int(template_id)) if template_id else None,
                brand_aliases,
            )
            amount = float(line.get("price_subtotal") or 0)
            qty = float(line.get("product_qty") or 0)
            for bucket in (purchase_by_category[category], purchase_by_brand[brand]):
                bucket["amount"] += amount
                bucket["quantity"] += qty
                bucket["lines"] += 1

        def ranked(source: dict[str, dict[str, float]], label_key: str) -> list[dict[str, Any]]:
            rows = [
                {
                    label_key: key,
                    "purchase_amount": round(value["amount"], 2),
                    "purchase_qty": round(value["quantity"], 2),
                    "lines": int(value["lines"]),
                }
                for key, value in source.items()
            ]
            rows.sort(key=lambda item: item["purchase_amount"], reverse=True)
            return rows[:limit]

        purchase_total = round(sum(float(row.get("amount_total") or 0) for row in purchase_orders), 2)
        sales_total = float(sales["total_amount"])
        ratio = (purchase_total / sales_total) if sales_total else None
        return {
            "period_days": capped_days,
            "start_date": first_day.isoformat(),
            "end_date": final_day.isoformat(),
            "sales_total": round(sales_total, 2),
            "purchase_total": purchase_total,
            "purchase_to_sales_ratio": round(ratio, 2) if ratio is not None else None,
            "decision_signal": self._purchase_sales_signal(purchase_total, sales_total),
            "sales_by_category": sales_breakdown["sales_by_category"],
            "sales_by_brand": sales_breakdown["sales_by_brand"],
            "purchases_by_category": ranked(purchase_by_category, "category"),
            "purchases_by_brand": ranked(purchase_by_brand, "brand"),
            "recent_purchase_orders": [
                {
                    "reference": order.get("name"),
                    "date": order.get("date_order"),
                    "supplier": _many2one_name(order.get("partner_id"), "Unknown supplier"),
                    "amount": round(float(order.get("amount_total") or 0), 2),
                }
                for order in purchase_orders[:8]
            ],
        }

    def supplier_purchase_history(self, days: int = 120, limit: int = 12) -> dict[str, Any]:
        capped_days = max(1, min(days, 730))
        final_day = datetime.now(LISBON_TZ).date()
        first_day = final_day - timedelta(days=capped_days - 1)
        start, end = (
            datetime.combine(first_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S"),
            (datetime.combine(final_day, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        orders = self.client.search_read(
            "purchase.order",
            domain=[["date_order", ">=", start], ["date_order", "<", end], ["state", "in", ["purchase", "done"]]],
            fields=["id", "name", "date_order", "amount_total", "partner_id"],
            limit=30000,
            order="date_order desc",
        )
        by_supplier: dict[str, dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "orders": 0.0})
        for order in orders:
            supplier = _many2one_name(order.get("partner_id"), "Unknown supplier")
            by_supplier[supplier]["amount"] += float(order.get("amount_total") or 0)
            by_supplier[supplier]["orders"] += 1
        suppliers = [
            {"supplier": key, "amount": round(value["amount"], 2), "orders": int(value["orders"])}
            for key, value in by_supplier.items()
        ]
        suppliers.sort(key=lambda item: item["amount"], reverse=True)
        return {
            "period_days": capped_days,
            "start_date": first_day.isoformat(),
            "end_date": final_day.isoformat(),
            "total_purchase_amount": round(sum(item["amount"] for item in suppliers), 2),
            "suppliers": suppliers[:limit],
            "recent_orders": [
                {
                    "reference": order.get("name"),
                    "date": order.get("date_order"),
                    "supplier": _many2one_name(order.get("partner_id"), "Unknown supplier"),
                    "amount": round(float(order.get("amount_total") or 0), 2),
                }
                for order in orders[:limit]
            ],
        }

    def working_capital_snapshot(self) -> dict[str, Any]:
        financials = self.key_financials()
        stock = financials["stock"]
        outstanding = financials["outstanding"]
        purchases = financials["ytd_purchases"]
        month_sales = float(financials["month_sales"]["total_amount"])
        stock_value = float(stock["value"])
        receivable = float(outstanding["receivable"])
        payable = float(outstanding["payable"])
        exposure = stock_value + receivable - payable
        return {
            "generated_at": datetime.now(LISBON_TZ).isoformat(),
            "stock_value": round(stock_value, 2),
            "available_stock_units": stock["available"],
            "open_receivable": round(receivable, 2),
            "open_payable": round(payable, 2),
            "ytd_purchase_amount": purchases["amount"],
            "month_sales_amount": round(month_sales, 2),
            "working_capital_exposure": round(exposure, 2),
            "signals": [
                self._signal("receivable_collection", receivable > month_sales * 0.5, "Receivables are high relative to this month's sales."),
                self._signal("payable_pressure", payable > month_sales * 0.5, "Supplier payables are high relative to this month's sales."),
                self._signal("stock_cash_tied", stock_value > month_sales * 2 if month_sales else stock_value > 0, "A lot of cash is tied in stock."),
            ],
        }

    def financial_risk_alerts(self, limit: int = 10) -> dict[str, Any]:
        open_bills = self.open_bills(limit=limit)
        open_invoices = self.open_customer_invoices(limit=limit)
        price_exceptions = self.price_cost_exceptions(limit=limit)
        stock_cover = self.stock_cover_and_velocity(days=90, limit=limit)
        purchase_sales = self.purchase_vs_sales_analysis(days=30, limit=limit)
        alerts: list[dict[str, Any]] = []
        if open_invoices["total_open_receivable"] > 0:
            alerts.append(
                {
                    "type": "receivables",
                    "severity": "medium",
                    "message": f"Open customer receivables total EUR {open_invoices['total_open_receivable']:,.2f}.",
                    "recommended_action": "Review and chase overdue customer invoices.",
                }
            )
        if open_bills["total_open_payable"] > 0:
            alerts.append(
                {
                    "type": "payables",
                    "severity": "medium",
                    "message": f"Open supplier bills total EUR {open_bills['total_open_payable']:,.2f}.",
                    "recommended_action": "Check upcoming supplier payments before placing large buys.",
                }
            )
        if purchase_sales["decision_signal"] != "normal":
            alerts.append(
                {
                    "type": "purchase_vs_sales",
                    "severity": "high" if purchase_sales["decision_signal"] == "purchases_above_sales" else "medium",
                    "message": "Purchases are high compared with sales in the latest period.",
                    "recommended_action": "Pause non-critical buying and inspect category/brand mismatch.",
                }
            )
        if price_exceptions["exceptions"]:
            alerts.append(
                {
                    "type": "price_cost_data",
                    "severity": "medium",
                    "message": f"{len(price_exceptions['exceptions'])} sampled products have price/cost issues.",
                    "recommended_action": "Fix missing costs and products priced below cost before trusting margin.",
                }
            )
        risk_counts = stock_cover["risk_counts"]
        if risk_counts.get("stockout_risk") or risk_counts.get("low_cover"):
            alerts.append(
                {
                    "type": "stock_cover",
                    "severity": "high",
                    "message": "Some selling products have low cover or stockout risk.",
                    "recommended_action": "Prioritize controlled replenishment for items with recent sales.",
                }
            )
        return {
            "generated_at": datetime.now(LISBON_TZ).isoformat(),
            "alerts": alerts[:limit],
            "supporting_data": {
                "open_bills": open_bills,
                "open_customer_invoices": open_invoices,
                "price_cost_exceptions": price_exceptions,
                "stock_risk_counts": risk_counts,
                "purchase_vs_sales": purchase_sales,
            },
        }

    def daily_owner_briefing(self) -> dict[str, Any]:
        financials = self.key_financials()
        sales = self.sales_performance_breakdown(days=7, limit=6)
        stock = self.stock_cover_and_velocity(days=90, limit=8)
        working_capital = self.working_capital_snapshot()
        alerts = self.financial_risk_alerts(limit=6)
        priorities: list[str] = []
        if stock["risk_counts"].get("stockout_risk") or stock["risk_counts"].get("low_cover"):
            priorities.append("Review low-cover products with recent sales before they stock out.")
        if stock["risk_counts"].get("no_recent_sales") or stock["risk_counts"].get("overstock"):
            priorities.append("Avoid buying more slow stock; consider promotion or display changes.")
        if alerts["alerts"]:
            priorities.append(alerts["alerts"][0]["recommended_action"])
        if not priorities:
            priorities.append("Monitor sales and keep buying controlled until a clear stock gap appears.")
        return {
            "generated_at": datetime.now(LISBON_TZ).isoformat(),
            "today_sales": financials["today_sales"],
            "month_sales": financials["month_sales"],
            "sales_trend_7_days": sales["trend"],
            "stock_risk_counts": stock["risk_counts"],
            "working_capital": working_capital,
            "alerts": alerts["alerts"],
            "priorities": priorities[:4],
            "recommendation": priorities[0],
        }

    def recommendation_for_question(self, query: str, days: int = 90) -> dict[str, Any]:
        normalized = query.lower()
        if any(term in normalized for term in ["buy", "replenish", "reorder"]):
            data = self.product_replenishment_insight(query=query, days=days)
            return {
                "intent": "replenishment",
                "decision": data["decision"],
                "recommendation": data["recommendation"],
                "confidence": "medium" if data["matched_products"] else "low",
                "evidence": data,
            }
        if any(term in normalized for term in ["margin", "profit", "price", "cost"]):
            data = self.margin_by_product_category_brand(days=days)
            exceptions = self.price_cost_exceptions(limit=10)
            return {
                "intent": "margin",
                "decision": "review_margin_and_data_quality",
                "recommendation": "Review low-margin categories and fix products with missing cost or bad price data before making margin decisions.",
                "confidence": "medium",
                "evidence": {"margin": data, "price_cost_exceptions": exceptions},
            }
        if any(term in normalized for term in ["purchase", "supplier", "bought", "buying"]):
            data = self.purchase_vs_sales_analysis(days=min(days, 365))
            return {
                "intent": "purchase_control",
                "decision": data["decision_signal"],
                "recommendation": self._purchase_sales_recommendation(data["decision_signal"]),
                "confidence": "medium",
                "evidence": data,
            }
        if any(term in normalized for term in ["stock", "inventory", "category", "brand"]):
            data = self.stock_cover_and_velocity(days=days)
            return {
                "intent": "stock_risk",
                "decision": "review_stock_cover",
                "recommendation": "Focus first on low-cover products with sales, then reduce buying for no-sales or overstock products.",
                "confidence": "medium",
                "evidence": data,
            }
        briefing = self.daily_owner_briefing()
        return {
            "intent": "owner_briefing",
            "decision": "daily_priorities",
            "recommendation": briefing["recommendation"],
            "confidence": "medium",
            "evidence": briefing,
        }

    def _sales_product_rows(
        self,
        start: str,
        end: str,
    ) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], str | None, dict[int, Any], dict[str, str]]:
        pos_orders = self.client.search_read(
            "pos.order",
            domain=[["date_order", ">=", start], ["date_order", "<", end]],
            fields=["id"],
            limit=30000,
        )
        sale_orders = self.client.search_read(
            "sale.order",
            domain=[["date_order", ">=", start], ["date_order", "<", end]],
            fields=["id"],
            limit=30000,
        )
        pos_order_ids = [row["id"] for row in pos_orders]
        sale_order_ids = [row["id"] for row in sale_orders]
        pos_lines = (
            self.client.search_read(
                "pos.order.line",
                domain=[["order_id", "in", pos_order_ids]],
                fields=["product_id", "qty", "price_subtotal_incl"],
                limit=80000,
            )
            if pos_order_ids
            else []
        )
        sale_lines = (
            self.client.search_read(
                "sale.order.line",
                domain=[["order_id", "in", sale_order_ids]],
                fields=["product_id", "product_uom_qty", "price_subtotal"],
                limit=80000,
            )
            if sale_order_ids
            else []
        )
        rows: list[dict[str, Any]] = []
        product_ids: set[int] = set()
        for line in pos_lines:
            product_ref = line.get("product_id")
            if not isinstance(product_ref, list):
                continue
            product_id = int(product_ref[0])
            product_ids.add(product_id)
            rows.append(
                {
                    "source": "pos",
                    "product_id": product_id,
                    "product_name": str(product_ref[1]) if len(product_ref) > 1 else "Unknown product",
                    "quantity": float(line.get("qty") or 0),
                    "revenue": float(line.get("price_subtotal_incl") or 0),
                }
            )
        for line in sale_lines:
            product_ref = line.get("product_id")
            if not isinstance(product_ref, list):
                continue
            product_id = int(product_ref[0])
            product_ids.add(product_id)
            rows.append(
                {
                    "source": "sale_order",
                    "product_id": product_id,
                    "product_name": str(product_ref[1]) if len(product_ref) > 1 else "Unknown product",
                    "quantity": float(line.get("product_uom_qty") or 0),
                    "revenue": float(line.get("price_subtotal") or 0),
                }
            )
        products, brand_field, template_brands, brand_aliases = self._product_map(sorted(product_ids))
        return rows, products, brand_field, template_brands, brand_aliases

    def _product_map(
        self,
        product_ids: list[int],
    ) -> tuple[dict[int, dict[str, Any]], str | None, dict[int, Any], dict[str, str]]:
        brand_field = self._available_product_brand_field()
        brand_aliases = self._brand_aliases()
        product_fields = [
            "id",
            "name",
            "default_code",
            "categ_id",
            "standard_price",
            "list_price",
            "qty_available",
            "virtual_available",
            "product_tmpl_id",
        ]
        if brand_field:
            product_fields.append(brand_field)
        products: dict[int, dict[str, Any]] = {}
        for offset in range(0, len(product_ids), 200):
            batch = product_ids[offset : offset + 200]
            if not batch:
                continue
            for product in self.client.search_read(
                "product.product",
                domain=[["id", "in", batch]],
                fields=product_fields,
                limit=200,
            ):
                products[int(product["id"])] = product
        template_ids = [
            product["product_tmpl_id"][0]
            for product in products.values()
            if brand_field and isinstance(product.get("product_tmpl_id"), list) and not product.get(brand_field)
        ]
        return products, brand_field, self._template_brands(brand_field, template_ids), brand_aliases

    def _template_brands(self, brand_field: str | None, template_ids: list[int]) -> dict[int, Any]:
        if not brand_field or not template_ids:
            return {}
        template_brands: dict[int, Any] = {}
        for offset in range(0, len(template_ids), 200):
            batch = list(dict.fromkeys(template_ids[offset : offset + 200]))
            for template in self.client.search_read(
                "product.template",
                domain=[["id", "in", batch]],
                fields=["id", brand_field],
                limit=200,
            ):
                template_brands[int(template["id"])] = template.get(brand_field)
        return template_brands

    def _purchase_sales_signal(self, purchase_total: float, sales_total: float) -> str:
        if purchase_total <= 0:
            return "no_recent_purchases"
        if sales_total <= 0:
            return "purchases_without_sales"
        ratio = purchase_total / sales_total
        if ratio >= 1:
            return "purchases_above_sales"
        if ratio >= 0.6:
            return "purchases_high_vs_sales"
        return "normal"

    def _purchase_sales_recommendation(self, signal: str) -> str:
        if signal in {"purchases_above_sales", "purchases_without_sales"}:
            return "Pause non-critical purchases and compare buys against category sales before ordering more."
        if signal == "purchases_high_vs_sales":
            return "Keep buying controlled and prioritize products with proven recent sales velocity."
        if signal == "no_recent_purchases":
            return "No recent purchase pressure appears in Odoo for the selected period."
        return "Purchases look controlled compared with sales; keep monitoring by category and brand."

    def _signal(self, name: str, active: bool, message: str) -> dict[str, Any]:
        return {"name": name, "active": active, "message": message if active else ""}

    def purchase_summary(self, year: int | None = None, month: int | None = None) -> dict[str, Any]:
        now = datetime.now(LISBON_TZ)
        target_year = year or now.year
        if month:
            start, end = _month_range(target_year, month)
            period = f"{target_year}-{month:02d}"
        else:
            start, end = _year_range(target_year)
            period = f"{target_year} YTD"

        domain = [
            ["date_order", ">=", start],
            ["date_order", "<", end],
            ["state", "in", ["purchase", "done"]],
        ]
        amount = _sum_group(self.client, "purchase.order", domain, "amount_total")
        orders = self.client.search_read(
            "purchase.order",
            domain=domain,
            fields=["name", "date_order", "amount_total", "state"],
            limit=8,
            order="date_order desc",
        )

        return {
            "period": period,
            "start": start,
            "end": end,
            "amount": round(amount, 2),
            "count": self.client.search_count("purchase.order", domain),
            "recent_orders": [
                {
                    "reference": order.get("name"),
                    "date": order.get("date_order"),
                    "amount": round(float(order.get("amount_total") or 0), 2),
                    "state": order.get("state"),
                }
                for order in orders
            ],
        }

    def open_bills(self, limit: int = 12) -> dict[str, Any]:
        domain = [
            ["state", "=", "posted"],
            ["move_type", "in", ["in_invoice", "in_refund"]],
            ["payment_state", "in", ["not_paid", "partial"]],
        ]
        bills = self.client.search_read(
            "account.move",
            domain=domain,
            fields=[
                "id",
                "name",
                "partner_id",
                "invoice_date",
                "invoice_date_due",
                "amount_total_signed",
                "amount_residual_signed",
                "payment_state",
                "invoice_line_ids",
            ],
            limit=limit,
            order="invoice_date desc",
        )
        bill_line_ids = [
            int(line_id)
            for bill in bills
            for line_id in (bill.get("invoice_line_ids") or [])
            if isinstance(line_id, int)
        ]
        lines_by_bill: dict[int, list[dict[str, Any]]] = defaultdict(list)
        if bill_line_ids:
            bill_lines = self.client.search_read(
                "account.move.line",
                domain=[["id", "in", bill_line_ids]],
                fields=[
                    "move_id",
                    "product_id",
                    "name",
                    "quantity",
                    "price_unit",
                    "price_subtotal",
                    "price_total",
                ],
                limit=len(bill_line_ids),
            )
            for line in bill_lines:
                bill_id = line.get("move_id", [None])[0] if isinstance(line.get("move_id"), list) else None
                if not isinstance(bill_id, int):
                    continue
                lines_by_bill[bill_id].append(
                    {
                        "product": _many2one_name(line.get("product_id"), str(line.get("name") or "Bill line")),
                        "description": line.get("name"),
                        "quantity": round(float(line.get("quantity") or 0), 2),
                        "unit_price": abs(round(float(line.get("price_unit") or 0), 2)),
                        "subtotal": abs(round(float(line.get("price_subtotal") or 0), 2)),
                        "total": abs(round(float(line.get("price_total") or 0), 2)),
                    }
                )
        all_bills = self.client.search_read(
            "account.move",
            domain=domain,
            fields=["partner_id", "amount_residual_signed"],
            limit=10000,
        )
        by_supplier: dict[str, dict[str, float]] = defaultdict(lambda: {"open_amount": 0.0, "count": 0.0})
        for row in all_bills:
            supplier = _many2one_name(row.get("partner_id"), "Unknown supplier")
            by_supplier[supplier]["open_amount"] += abs(float(row.get("amount_residual_signed") or 0))
            by_supplier[supplier]["count"] += 1
        suppliers = [
            {"supplier": key, "open_amount": round(item["open_amount"], 2), "count": int(item["count"])}
            for key, item in by_supplier.items()
        ]
        suppliers.sort(key=lambda item: item["open_amount"], reverse=True)
        total_residual = abs(sum(float(row.get("amount_residual_signed") or 0) for row in all_bills))
        return {
            "total_open_payable": round(total_residual, 2),
            "count": self.client.search_count("account.move", domain),
            "by_supplier": suppliers[:12],
            "bills": [
                {
                    "id": row.get("id"),
                    "reference": row.get("name"),
                    "supplier": _many2one_name(row.get("partner_id"), "Unknown supplier"),
                    "date": row.get("invoice_date"),
                    "due_date": row.get("invoice_date_due"),
                    "amount": abs(round(float(row.get("amount_total_signed") or 0), 2)),
                    "open_amount": abs(round(float(row.get("amount_residual_signed") or 0), 2)),
                    "payment_state": row.get("payment_state"),
                    "lines": lines_by_bill.get(int(row["id"]), []) if isinstance(row.get("id"), int) else [],
                }
                for row in bills
            ],
        }

    def open_customer_invoices(self, limit: int = 12) -> dict[str, Any]:
        domain = [
            ["state", "=", "posted"],
            ["move_type", "in", ["out_invoice", "out_refund"]],
            ["payment_state", "in", ["not_paid", "partial"]],
        ]
        invoices = self.client.search_read(
            "account.move",
            domain=domain,
            fields=["name", "invoice_date", "amount_total_signed", "amount_residual_signed", "payment_state"],
            limit=limit,
            order="invoice_date desc",
        )
        total_residual = sum(float(row.get("amount_residual_signed") or 0) for row in invoices)
        return {
            "total_open_receivable": round(total_residual, 2),
            "count": self.client.search_count("account.move", domain),
            "invoices": [
                {
                    "reference": row.get("name"),
                    "date": row.get("invoice_date"),
                    "amount": round(float(row.get("amount_total_signed") or 0), 2),
                    "open_amount": round(float(row.get("amount_residual_signed") or 0), 2),
                    "payment_state": row.get("payment_state"),
                }
                for row in invoices
            ],
        }

    def recent_orders(self, limit: int = 10) -> dict[str, Any]:
        pos_orders = self.client.search_read(
            "pos.order",
            fields=["name", "date_order", "amount_total", "state"],
            limit=limit,
            order="date_order desc",
        )
        sale_orders = self.client.search_read(
            "sale.order",
            fields=["name", "date_order", "amount_total", "state"],
            limit=limit,
            order="date_order desc",
        )
        orders = [
            {
                "source": "pos",
                "reference": row.get("name"),
                "date": row.get("date_order"),
                "amount": round(float(row.get("amount_total") or 0), 2),
                "state": row.get("state"),
            }
            for row in pos_orders
        ] + [
            {
                "source": "sale_order",
                "reference": row.get("name"),
                "date": row.get("date_order"),
                "amount": round(float(row.get("amount_total") or 0), 2),
                "state": row.get("state"),
            }
            for row in sale_orders
        ]
        orders.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
        return {"orders": orders[:limit]}

    def profitability_snapshot(self, year: int | None = None, month: int | None = None) -> dict[str, Any]:
        now = datetime.now(LISBON_TZ)
        target_year = year or now.year
        if month:
            start, end = _month_range(target_year, month)
            sales = self.month_sales(target_year, month)
            period = f"{target_year}-{month:02d}"
        else:
            start, end = _year_range(target_year)
            sales = self.sales_summary(start, end)
            period = f"{target_year} YTD"

        purchases = self.purchase_summary(target_year, month)
        stock = self.stock_value()
        financials = self.key_financials()
        margin = self._estimated_sales_margin(start, end)

        return {
            "period": period,
            "sales": sales,
            "purchases": purchases,
            "stock": {
                "value": stock["value"],
                "available_units": stock["available"],
            },
            "working_capital": {
                "open_receivable": financials["outstanding"]["receivable"],
                "open_payable": financials["outstanding"]["payable"],
            },
            "estimated_margin": margin,
            "notes": [
                "Profitability is estimated from Odoo sales and product standard costs when those costs are available.",
                "Use accounting reports for final statutory profit.",
            ],
        }

    def business_snapshot(self) -> dict[str, Any]:
        now = datetime.now(LISBON_TZ)
        return {
            "generated_at": now.isoformat(),
            "financials": self.key_financials(),
            "purchases": self.purchase_summary(now.year),
            "profitability": self.profitability_snapshot(now.year),
            "top_stock_categories": self.stock_value_by_category(limit=6),
            "today_categories": self.sales_by_category(now.date(), limit=6),
            "low_stock": self.low_stock(limit=8),
            "recent_orders": self.recent_orders(limit=8),
        }

    def _estimated_sales_margin(self, start: str, end: str) -> dict[str, Any]:
        try:
            pos_orders = self.client.search_read(
                "pos.order",
                domain=[["date_order", ">=", start], ["date_order", "<", end]],
                fields=["id"],
                limit=20000,
            )
            sale_orders = self.client.search_read(
                "sale.order",
                domain=[["date_order", ">=", start], ["date_order", "<", end]],
                fields=["id"],
                limit=20000,
            )
            pos_order_ids = [row["id"] for row in pos_orders]
            sale_order_ids = [row["id"] for row in sale_orders]

            pos_lines = (
                self.client.search_read(
                    "pos.order.line",
                    domain=[["order_id", "in", pos_order_ids]],
                    fields=["product_id", "qty", "price_subtotal_incl"],
                    limit=40000,
                )
                if pos_order_ids
                else []
            )
            sale_lines = (
                self.client.search_read(
                    "sale.order.line",
                    domain=[["order_id", "in", sale_order_ids]],
                    fields=["product_id", "product_uom_qty", "price_subtotal"],
                    limit=40000,
                )
                if sale_order_ids
                else []
            )

            product_ids = sorted(
                {
                    line["product_id"][0]
                    for line in [*pos_lines, *sale_lines]
                    if isinstance(line.get("product_id"), list)
                }
            )
            costs: dict[int, float] = {}
            for offset in range(0, len(product_ids), 200):
                batch = product_ids[offset : offset + 200]
                for product in self.client.search_read(
                    "product.product",
                    domain=[["id", "in", batch]],
                    fields=["id", "standard_price"],
                    limit=200,
                ):
                    costs[int(product["id"])] = float(product.get("standard_price") or 0)

            revenue = 0.0
            estimated_cost = 0.0
            costed_lines = 0
            for line in pos_lines:
                product_ref = line.get("product_id")
                product_id = product_ref[0] if isinstance(product_ref, list) else None
                qty = float(line.get("qty") or 0)
                revenue += float(line.get("price_subtotal_incl") or 0)
                if product_id in costs:
                    estimated_cost += costs[product_id] * qty
                    costed_lines += 1

            for line in sale_lines:
                product_ref = line.get("product_id")
                product_id = product_ref[0] if isinstance(product_ref, list) else None
                qty = float(line.get("product_uom_qty") or 0)
                revenue += float(line.get("price_subtotal") or 0)
                if product_id in costs:
                    estimated_cost += costs[product_id] * qty
                    costed_lines += 1

            gross_profit = revenue - estimated_cost
            margin_pct = (gross_profit / revenue * 100) if revenue else 0.0
            return {
                "available": True,
                "revenue": round(revenue, 2),
                "estimated_cost": round(estimated_cost, 2),
                "estimated_gross_profit": round(gross_profit, 2),
                "estimated_gross_margin_pct": round(margin_pct, 1),
                "lines_used": costed_lines,
            }
        except Exception as exc:
            return {
                "available": False,
                "reason": f"Unable to estimate margin from available Odoo fields: {exc}",
            }

    def key_financials(self) -> dict[str, Any]:
        now = datetime.now(LISBON_TZ)
        ytd_start, next_year = _year_range(now.year)
        today = self.today_sales(now.date())
        month = self.month_sales(now.year, now.month)
        ytd = self.sales_summary(ytd_start, next_year)
        stock = self.stock_value()

        purchase_domain = [
            ["date_order", ">=", ytd_start],
            ["date_order", "<", next_year],
            ["state", "in", ["purchase", "done"]],
        ]
        purchases = _sum_group(self.client, "purchase.order", purchase_domain, "amount_total")
        purchase_count = self.client.search_count("purchase.order", purchase_domain)

        receivables = self.client.search_read(
            "account.move",
            domain=[
                ["state", "=", "posted"],
                ["move_type", "in", ["out_invoice", "out_refund"]],
                ["payment_state", "in", ["not_paid", "partial"]],
            ],
            fields=["amount_residual_signed"],
            limit=10000,
        )
        payables = self.client.search_read(
            "account.move",
            domain=[
                ["state", "=", "posted"],
                ["move_type", "in", ["in_invoice", "in_refund"]],
                ["payment_state", "in", ["not_paid", "partial"]],
            ],
            fields=["amount_residual_signed"],
            limit=10000,
        )

        return {
            "today_sales": today,
            "month_sales": month,
            "ytd_sales": ytd,
            "stock": stock,
            "ytd_purchases": {
                "amount": round(purchases, 2),
                "count": purchase_count,
            },
            "outstanding": {
                "receivable": round(sum(float(row.get("amount_residual_signed") or 0) for row in receivables), 2),
                "payable": abs(round(sum(float(row.get("amount_residual_signed") or 0) for row in payables), 2)),
                "receivable_count": len(receivables),
                "payable_count": len(payables),
            },
        }

    def dashboard(self) -> dict[str, Any]:
        now = datetime.now(LISBON_TZ)
        ytd_start = date(now.year, 1, 1)
        return {
            "generated_at": now.isoformat(),
            "financials": self.key_financials(),
            "monthly_sales": self.monthly_sales(now.year),
            "stock_categories": self.stock_value_by_category(),
            "stock_analytics": self.stock_analytics(),
            "purchases": self.purchase_summary(now.year),
            "open_bills": self.open_bills(),
            "open_customer_invoices": self.open_customer_invoices(),
            "today_sales_by_category": self.sales_by_category(now.date()),
            "sales_analytics": {
                "7": self.sales_analytics_breakdowns(days=7, end_day=now.date()),
                "30": self.sales_analytics_breakdowns(days=30, end_day=now.date()),
                "90": self.sales_analytics_breakdowns(days=90, end_day=now.date()),
                "365": self.sales_analytics_breakdowns(start_day=ytd_start, end_day=now.date()),
            },
            "low_stock": self.low_stock(),
        }
