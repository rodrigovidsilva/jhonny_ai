from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.odoo_client import OdooClient, OdooConfig, load_env


def print_count(client: OdooClient, label: str, model: str, domain: list | None = None) -> None:
    try:
        count = client.search_count(model, domain or [])
        print(f"- {label}: {count}")
    except Exception as exc:
        print(f"- {label}: unavailable ({exc.__class__.__name__})")


def main() -> None:
    load_env(ROOT / ".env")
    client = OdooClient(OdooConfig.from_env())
    client.authenticate()

    print("Core record counts:")
    print_count(client, "Products", "product.product")
    print_count(client, "Sellable products", "product.product", [["sale_ok", "=", True]])
    print_count(client, "Customers and contacts", "res.partner")
    print_count(client, "Sales orders", "sale.order")
    print_count(client, "POS orders", "pos.order")
    print_count(client, "Stock quants", "stock.quant")
    print_count(client, "Stock locations", "stock.location")
    print_count(client, "Purchase orders", "purchase.order")

    locations = client.search_read(
        "stock.location",
        domain=[["usage", "=", "internal"]],
        fields=["complete_name", "usage", "active"],
        limit=25,
    )
    print("\nInternal stock locations:")
    for location in locations:
        print(f"- {location.get('complete_name')} | active={location.get('active')}")

    sale_orders = client.search_read(
        "sale.order",
        fields=["name", "date_order", "partner_id", "amount_total", "state"],
        limit=10,
    )
    print("\nRecent sales orders sample:")
    for order in sale_orders:
        partner = order.get("partner_id")
        partner_name = partner[1] if isinstance(partner, list) and len(partner) > 1 else "unknown"
        print(
            f"- {order.get('name')} | {order.get('date_order')} | "
            f"{partner_name} | {order.get('amount_total')} | {order.get('state')}"
        )

    pos_orders = client.search_read(
        "pos.order",
        fields=["name", "date_order", "partner_id", "amount_total", "state"],
        limit=10,
    )
    print("\nRecent POS orders sample:")
    for order in pos_orders:
        partner = order.get("partner_id")
        partner_name = partner[1] if isinstance(partner, list) and len(partner) > 1 else "no customer"
        print(
            f"- {order.get('name')} | {order.get('date_order')} | "
            f"{partner_name} | {order.get('amount_total')} | {order.get('state')}"
        )


if __name__ == "__main__":
    main()
