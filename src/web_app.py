from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.app_factory import create_agent


ROOT = Path(__file__).resolve().parents[1]


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Retail Agent POC</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, Segoe UI, Arial, sans-serif; }
    body { margin: 0; background: #111; color: #f5f5f5; }
    main { max-width: 1180px; margin: 0 auto; padding: 32px; }
    header { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
    h1, h2 { margin: 0; }
    p { color: #bbb; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .card { border: 1px solid #333; background: #181818; border-radius: 12px; padding: 16px; }
    .value { font-size: 28px; font-weight: 700; margin-top: 8px; }
    .label { color: #aaa; font-size: 13px; }
    .layout { display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; margin-top: 18px; }
    .bar-row { display: grid; grid-template-columns: minmax(160px, 260px) 1fr 90px; gap: 12px; align-items: center; margin: 9px 0; }
    .bar-track { background: #2a2a2a; height: 12px; border-radius: 999px; overflow: hidden; }
    .bar { background: #7c3aed; height: 100%; }
    input { width: 100%; box-sizing: border-box; border: 1px solid #444; background: #101010; color: #fff; border-radius: 10px; padding: 12px; }
    button { border: 0; border-radius: 10px; padding: 12px 14px; background: #7c3aed; color: white; font-weight: 700; cursor: pointer; }
    .chat-row { display: flex; gap: 8px; }
    pre { white-space: pre-wrap; color: #ddd; background: #101010; border: 1px solid #333; border-radius: 10px; padding: 12px; min-height: 80px; }
    table { width: 100%; border-collapse: collapse; }
    td, th { border-bottom: 1px solid #333; padding: 8px; text-align: left; }
    td:last-child, th:last-child { text-align: right; }
    @media (max-width: 900px) { .grid, .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Retail Agent POC</h1>
        <p>Live dashboards and business agent powered by Odoo data.</p>
      </div>
      <button onclick="loadDashboard()">Refresh</button>
    </header>

    <section class="grid" id="stats"></section>

    <section class="layout">
      <div class="card">
        <h2>Monthly Sales</h2>
        <div id="monthly"></div>
      </div>
      <div class="card">
        <h2>Ask The Agent</h2>
        <p>Try: "How much did we sell today?" or "What is stock value?"</p>
        <div class="chat-row">
          <input id="question" value="How much did we sell today?" />
          <button onclick="askAgent()">Ask</button>
        </div>
        <pre id="answer"></pre>
      </div>
    </section>

    <section class="layout">
      <div class="card">
        <h2>Stock Value By Category</h2>
        <div id="stockCategories"></div>
      </div>
      <div class="card">
        <h2>Low Stock</h2>
        <table>
          <thead><tr><th>SKU</th><th>Qty</th></tr></thead>
          <tbody id="lowStock"></tbody>
        </table>
      </div>
    </section>
  </main>

  <script>
    const euro = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR" });
    const fmt = (value) => euro.format(value || 0);

    function barRows(items, labelKey, valueKey) {
      const max = Math.max(...items.map((item) => item[valueKey] || 0), 1);
      return items.map((item) => `
        <div class="bar-row">
          <div>${item[labelKey]}</div>
          <div class="bar-track"><div class="bar" style="width:${((item[valueKey] || 0) / max) * 100}%"></div></div>
          <div>${fmt(item[valueKey])}</div>
        </div>
      `).join("");
    }

    function authHeaders() {
      const token = localStorage.getItem("retailAgentToken") || "";
      return token ? { "X-App-Token": token } : {};
    }

    async function loadDashboard() {
      const response = await fetch("/api/dashboard", { headers: authHeaders() });
      if (response.status === 401) {
        const token = prompt("Enter demo access token");
        if (token) localStorage.setItem("retailAgentToken", token);
        return loadDashboard();
      }
      const data = await response.json();
      const financials = data.financials;
      document.getElementById("stats").innerHTML = `
        <div class="card"><div class="label">Today sales</div><div class="value">${fmt(financials.today_sales.total_amount)}</div></div>
        <div class="card"><div class="label">Month sales</div><div class="value">${fmt(financials.month_sales.total_amount)}</div></div>
        <div class="card"><div class="label">YTD sales</div><div class="value">${fmt(financials.ytd_sales.total_amount)}</div></div>
        <div class="card"><div class="label">Stock value</div><div class="value">${fmt(financials.stock.value)}</div></div>
      `;
      document.getElementById("monthly").innerHTML = barRows(data.monthly_sales, "month", "amount");
      document.getElementById("stockCategories").innerHTML = barRows(data.stock_categories, "category", "value");
      document.getElementById("lowStock").innerHTML = data.low_stock.slice(0, 10).map((item) => `
        <tr><td>${item.sku}<br><span class="label">${item.name}</span></td><td>${item.qty_available}</td></tr>
      `).join("");
    }

    async function askAgent() {
      const question = document.getElementById("question").value;
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ question })
      });
      const data = await response.json();
      document.getElementById("answer").textContent = data.answer || JSON.stringify(data, null, 2);
    }

    loadDashboard().catch((error) => {
      document.body.innerHTML = `<main><h1>Unable to load dashboard</h1><pre>${error}</pre></main>`;
    });
  </script>
</body>
</html>
"""


class RetailPocHandler(BaseHTTPRequestHandler):
    agent = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_text(HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/api/dashboard":
            if not self._is_authorized():
                self._send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            self._send_json(self._agent().tools.dashboard())
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))

        if parsed.path == "/api/agent":
            if not self._is_authorized():
                self._send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            payload = self._parse_json(body)
            question = str(payload.get("question", ""))
            self._send_json(self._agent().answer(question))
            return

        if parsed.path == "/webhooks/whatsapp":
            payload = self._parse_payload(body)
            sender = self._extract_sender(payload)
            if not self._is_allowed_sender(sender):
                self._send_json({"error": "sender is not authorized"}, HTTPStatus.FORBIDDEN)
                return
            question = self._extract_message(payload)
            answer = self._agent().answer(question)
            self._send_whatsapp_response(answer["answer"])
            return

        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    @classmethod
    def _agent(cls):
        if cls.agent is None:
            cls.agent = create_agent(ROOT)
        return cls.agent

    def _parse_json(self, body: bytes) -> dict[str, Any]:
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def _parse_payload(self, body: bytes) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return self._parse_json(body)
        parsed = parse_qs(body.decode("utf-8"))
        return {key: values[0] if values else "" for key, values in parsed.items()}

    def _extract_sender(self, payload: dict[str, Any]) -> str:
        if "From" in payload:
            return str(payload["From"]).replace("whatsapp:", "")
        try:
            return str(payload["entry"][0]["changes"][0]["value"]["messages"][0]["from"])
        except (KeyError, IndexError, TypeError):
            return ""

    def _extract_message(self, payload: dict[str, Any]) -> str:
        if "Body" in payload:
            return str(payload["Body"])
        try:
            return str(payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"])
        except (KeyError, IndexError, TypeError):
            return ""

    def _is_allowed_sender(self, sender: str) -> bool:
        allowed = {
            value.strip()
            for value in os.getenv("WHATSAPP_ALLOWED_NUMBERS", "").split(",")
            if value.strip()
        }
        return not allowed or sender in allowed

    def _is_authorized(self) -> bool:
        token = os.getenv("APP_AUTH_TOKEN", "").strip()
        if not token:
            return True
        parsed = urlparse(self.path)
        query_token = parse_qs(parsed.query).get("token", [""])[0]
        header_token = self.headers.get("X-App-Token", "")
        return token in {query_token, header_token}

    def _send_whatsapp_response(self, answer: str) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" in content_type:
            escaped = answer.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self._send_text(
                f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Message>{escaped}</Message></Response>",
                "application/xml; charset=utf-8",
            )
            return
        self._send_json({"answer": answer})

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_text(
        self,
        content: str,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), RetailPocHandler)
    print(f"Retail Agent POC running at http://{host}:{port}")
    server.serve_forever()
