from __future__ import annotations

import os
import time
import http.client
import xmlrpc.client
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_env(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class OdooConfig:
    url: str
    db: str
    username: str
    api_key: str

    @classmethod
    def from_env(cls) -> "OdooConfig":
        missing = [
            name
            for name in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_API_KEY")
            if not os.getenv(name)
        ]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            url=os.environ["ODOO_URL"].rstrip("/"),
            db=os.environ["ODOO_DB"],
            username=os.environ["ODOO_USERNAME"],
            api_key=os.environ["ODOO_API_KEY"],
        )


class OdooClient:
    def __init__(self, config: OdooConfig) -> None:
        self.config = config
        self._connect()
        self.uid: int | None = None

    def _connect(self) -> None:
        self.common = xmlrpc.client.ServerProxy(f"{self.config.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.config.url}/xmlrpc/2/object")

    def authenticate(self) -> int:
        uid = self.common.authenticate(
            self.config.db,
            self.config.username,
            self.config.api_key,
            {},
        )
        if not uid:
            raise RuntimeError(
                "Odoo authentication failed. Check ODOO_DB, ODOO_USERNAME, API key, and user permissions."
            )

        self.uid = int(uid)
        return self.uid

    def execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        if self.uid is None:
            self.authenticate()

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                models = xmlrpc.client.ServerProxy(f"{self.config.url}/xmlrpc/2/object")
                return models.execute_kw(
                    self.config.db,
                    self.uid,
                    self.config.api_key,
                    model,
                    method,
                    args or [],
                    kwargs or {},
                )
            except (OSError, http.client.HTTPException, xmlrpc.client.ProtocolError) as exc:
                last_error = exc
                if attempt == 2:
                    break
                self._connect()
                time.sleep(0.25 * (attempt + 1))

        raise last_error or RuntimeError("Odoo request failed")

    def search_read(
        self,
        model: str,
        domain: list[Any] | None = None,
        fields: list[str] | None = None,
        limit: int = 10,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"limit": limit}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order

        return self.execute_kw(model, "search_read", [domain or []], kwargs)

    def search_count(self, model: str, domain: list[Any] | None = None) -> int:
        return int(self.execute_kw(model, "search_count", [domain or []]))
