# Retail Agent POC

Small end-to-end POC that connects to Jhonny Surf's Odoo data and exposes:

- a FastAPI backend
- a Next.js web dashboard
- an LLM-powered business question-answering agent
- a WhatsApp webhook scaffold connected to the same agent
- demo and pilot sales materials

## Current Status

The app is being developed and tested locally first.

| Service | URL | Status |
|---|---|---|
| Next.js web app | `http://127.0.0.1:3000` | Local dev server |
| FastAPI backend | `http://127.0.0.1:8000` | Local API |
| Health check | `http://127.0.0.1:8000/health` | Returns `{"status":"ok"}` |

Cloud hosting is intentionally deferred until the app is demo-ready and Azure or AWS access is available. The current recommendation is Azure Container Apps first, unless AWS access or client preference arrives first.

## Credentials

Runtime credentials are loaded from `.env`:

```env
ODOO_URL=https://jhonny-surf.odoo.com
ODOO_DB=jhonny-surf-master-26611951
ODOO_USERNAME=loja@jhonnysurfstore.pt
ODOO_API_KEY=replace-with-api-key
APP_HOST=127.0.0.1
APP_PORT=8000
APP_AUTH_TOKEN=replace-with-demo-token
WHATSAPP_ALLOWED_NUMBERS=351900000000
OPENAI_API_KEY=replace-with-openai-api-key
OPENAI_MODEL=gpt-4o-mini
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

`.env` is ignored by git. Keep API keys out of commits and rotate keys before production use.

## Smoke Test

```powershell
py scripts/test_connection.py
```

The script authenticates with Odoo and reads:

- company details from `res.company`
- sample sellable products from `product.product`
- installed modules from `ir.module.module`

For a broader business-data check:

```powershell
py scripts/inspect_business_data.py
```

With the backend running, verify the local API:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

Expected:

```json
{
  "status": "ok"
}
```

## Install Backend Dependencies

```powershell
py -m pip install -r requirements.txt
```

## Run The Backend

```powershell
py scripts/run_app.py
```

Backend API:

```text
http://127.0.0.1:8000
```

If `APP_AUTH_TOKEN` is set, protected routes require `X-App-Token`.

## Run The Next.js App

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

Use the local demo token from `.env` when the browser prompts for access. Protected API calls send this as `X-App-Token`.

## Ask The Agent From CLI

```powershell
py scripts/ask_agent.py "How much did we sell today?"
py scripts/ask_agent.py "What is our stock value?"
py scripts/ask_agent.py "What categories sold today?"
```

## API Endpoints

```text
GET /health
GET /dashboard
POST /chat
POST /tools/{tool_name}
POST /webhooks/whatsapp
```

Example:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/chat `
  -Method POST `
  -Headers @{ "X-App-Token" = "retail-demo" } `
  -ContentType "application/json" `
  -Body '{"question":"What is our stock value?","channel":"app"}'
```

## Project Handoffs

- Tiago app handoff: `docs/app_handoff.md`
- Rodrigo WhatsApp handoff: `docs/whatsapp_handoff.md`
- 5-minute sales demo: `docs/demo_script.md`
- Paid pilot offer: `docs/pilot_offer.md`
- Local-first deployment notes: `docs/deployment.md`

## LLM Agent

When OpenAI environment variables are configured, the agent uses OpenAI to:

1. choose the right curated business tool
2. execute that tool against Odoo
3. write a grounded answer from the tool result

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in `.env`. Without OpenAI credentials, the app falls back to deterministic routing so the demo remains usable locally. Databricks Model Serving remains an optional future fallback if those environment variables are configured.

## Useful Odoo Models

- `product.product`: product variants and stock quantities
- `product.template`: product catalog
- `sale.order`: sales orders
- `pos.order`: point-of-sale orders
- `stock.quant`: on-hand stock by location
- `stock.location`: warehouses and store locations
- `res.partner`: customers, suppliers, and contacts
