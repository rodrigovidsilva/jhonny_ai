from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.odoo_client import OdooClient, OdooConfig, load_env


def main() -> None:
    load_env(ROOT / ".env")
    client = OdooClient(OdooConfig.from_env())

    uid = client.authenticate()
    print(f"Authenticated with Odoo user id: {uid}")

    company = client.search_read(
        "res.company",
        fields=["name", "email", "phone", "website"],
        limit=5,
    )
    print("\nCompanies:")
    for item in company:
        print(f"- {item.get('name')}")

    products = client.search_read(
        "product.product",
        domain=[["sale_ok", "=", True]],
        fields=["default_code", "name", "qty_available", "virtual_available", "list_price"],
        limit=10,
    )
    print("\nSample sellable products:")
    for item in products:
        code = item.get("default_code") or "no-sku"
        print(
            f"- [{code}] {item.get('name')} | "
            f"qty={item.get('qty_available')} | forecast={item.get('virtual_available')} | "
            f"price={item.get('list_price')}"
        )

    modules = client.search_read(
        "ir.module.module",
        domain=[["state", "=", "installed"]],
        fields=["name", "shortdesc"],
        limit=20,
    )
    print("\nInstalled modules sample:")
    for item in modules:
        print(f"- {item.get('name')}: {item.get('shortdesc')}")


if __name__ == "__main__":
    main()
