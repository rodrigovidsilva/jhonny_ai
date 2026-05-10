# Retail Agent POC

Local-first retail intelligence POC for Jhonny Surf Store. It connects to live Odoo data and exposes:

- a FastAPI backend
- a Next.js web app with Home, Analytics, and Assisted Agent surfaces
- a curated Odoo business-agent layer
- OpenAI primary LLM routing with optional Databricks fallback
- a WhatsApp webhook scaffold connected to the same agent
- demo, handoff, deployment, and paid-pilot materials

## Current Status

The app is being developed and reviewed locally first.

| Service | URL | Status |
|---|---|---|
| Next.js web app | `http://127.0.0.1:3000` | Local demo app |
| FastAPI backend | `http://127.0.0.1:8000` | Local API |
| Health check | `http://127.0.0.1:8000/health` | Returns `{"status":"ok"}` |

Cloud hosting is intentionally deferred until the demo flow is approved and hosting access is confirmed. The preferred enterprise path is Azure Container Apps. A Render blueprint is also included for a quick two-service deployment reference.

## App Surface

| Area | What It Shows |
|---|---|
| Home | Branded landing page, store pulse, daily sales, daily profit, last week sales estimate, profit margin, YTD profit, YTD sales, stock value, supplier bill exposure |
| Analytics | Sales, Stock, Purchases, and Financials dashboards with period selection |
| Assisted Agent | Chat UI, suggested prompts, session history, answer metadata, tool evidence, request IDs |

The app uses a demo token stored in browser local storage. Protected API calls send it as `X-App-Token`.

## Credentials

Runtime credentials are loaded from `.env`. Use `.env.example` as the template:

```env
ODOO_URL=https://jhonny-surf.odoo.com
ODOO_DB=jhonny-surf-master-26611951
ODOO_USERNAME=loja@jhonnysurfstore.pt
ODOO_API_KEY=replace-with-api-key
APP_HOST=127.0.0.1
APP_PORT=8000
APP_AUTH_TOKEN=retail-demo
APP_CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
WHATSAPP_ALLOWED_NUMBERS=351900000000
WHATSAPP_RATE_LIMIT_PER_MINUTE=20
PUBLIC_WHATSAPP_WEBHOOK_URL=https://replace-with-public-url/webhooks/whatsapp
TWILIO_AUTH_TOKEN=replace-with-twilio-auth-token
WHATSAPP_APP_SECRET=replace-with-meta-app-secret
OPENAI_API_KEY=replace-with-openai-api-key
OPENAI_MODEL=gpt-4o-mini
DATABRICKS_HOST=https://replace-with-workspace-url
DATABRICKS_TOKEN=replace-with-databricks-token
DATABRICKS_MODEL_ENDPOINT=replace-with-serving-endpoint
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

`.env` is ignored by git. Keep API keys out of commits and rotate development keys before production or paid-pilot hosting.

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

Use the local demo token from `.env` in the header token control. The default local demo token used by the frontend is `retail-demo`.

## Smoke Tests

Authenticate with Odoo and read core data:

```powershell
py scripts/test_connection.py
```

Inspect broader business data:

```powershell
py scripts/inspect_business_data.py
```

Run local regression checks that do not require live OpenAI:

```powershell
py scripts/evaluate_agent.py
py scripts/evaluate_api_security.py
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

Before a client or stakeholder demo, verify the OpenAI path if credentials are configured:

```powershell
py scripts/smoke_openai_chat.py "How much did we sell today?"
```

Expected result includes:

```json
{
  "status": "ok",
  "provider": "openai"
}
```

## Ask The Agent From CLI

```powershell
py scripts/ask_agent.py "How much did we sell today?"
py scripts/ask_agent.py "What is our stock value?"
py scripts/ask_agent.py "Are purchases too high compared with sales?"
py scripts/ask_agent.py "Where are we losing margin by brand or category?"
```

## API Endpoints

```text
GET /health
GET /dashboard
POST /chat
POST /tools/{tool_name}
POST /webhooks/whatsapp
```

Example chat request:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/chat `
  -Method POST `
  -Headers @{ "X-App-Token" = "retail-demo" } `
  -ContentType "application/json" `
  -Body '{"question":"What is our stock value?","channel":"app"}'
```

The `/chat` response can include `answer`, `tool`, `data`, `evidence`, `tool_trace`, `visualization`, `llm_provider`, `intent`, and `request_id`.

## Agent Tool Coverage

The LLM agent only selects from curated read-only Odoo tools for:

- sales totals, daily series, categories, brands, top/bottom products, and recent orders
- stock value, category value, brand value, stock age, low stock, stock cover, and overstock risk
- purchases, suppliers, purchase-versus-sales signals, and product replenishment recommendations
- open bills, customer receivables, working capital, price/cost exceptions, and estimated margin
- daily owner briefing and recommendation summaries

When OpenAI is configured, the agent uses it for tool selection and grounded answer writing. If OpenAI is not configured, it tries Databricks Model Serving if configured. If no LLM provider is available, deterministic routing keeps the local demo usable.

## Project Documents

- Review-ready POC plan: `docs/jhonny-retail-agent-poc-plan.md`
- Rendered POC plan PDF: `docs/jhonny-retail-agent-poc-plan.pdf`
- Tiago app handoff: `docs/app_handoff.md`
- Rodrigo WhatsApp handoff: `docs/whatsapp_handoff.md`
- 5-minute sales demo: `docs/demo_script.md`
- Paid pilot offer: `docs/pilot_offer.md`
- First outreach copy: `docs/outreach_message.md`
- Local-first deployment notes: `docs/deployment.md`
- EW app style guide: `docs/ew-app-style-guide.md`

## Useful Odoo Models

- `product.product`: product variants, price/cost fields, and stock quantities
- `product.template`: product catalog and fallback product metadata
- `sale.order` and `sale.order.line`: sale order revenue and quantities
- `pos.order` and `pos.order.line`: point-of-sale revenue and quantities
- `stock.quant`: on-hand stock, availability, valuation, location, and stock age signals
- `purchase.order` and `purchase.order.line`: purchasing activity and supplier spend
- `account.move` and `account.move.line`: supplier bills, receivables, payables, and bill lines
