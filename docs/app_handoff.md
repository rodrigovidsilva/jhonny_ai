# App Handoff

Owner: Tiago

## Goal

Give the retailer a simple web app with dashboards and an agent chat surface. The first version should support the sales demo, not try to become a full BI tool.

Jhonny is the first client. He owns a family-style surf retail business, uses Odoo, and needs a browser-accessible app where he can ask questions about sales, bills, stock, purchases, and other daily owner topics. The app should also include predefined analytics dashboards that refresh from Odoo.

Rodrigo owns the WhatsApp prompting feature. The browser app remains the primary delivery surface for Jhonny while WhatsApp uses the same backend agent path.

## Current App

The app is local-first for now and has three top-level surfaces: Home, Analytics, and Assisted Agent. Run the backend:

```powershell
py scripts/run_app.py
```

Then run the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the app:

```text
http://127.0.0.1:3000
```

Backend health:

```text
http://127.0.0.1:8000/health
```

The backend, dashboard, and chat endpoints have been validated locally against live Odoo data. The current backend client retries transient Odoo XML-RPC transport failures so dashboard refreshes are more reliable during demos.

The app currently includes:

- Branded Jhonny Surf home page with store pulse metrics
- Header demo-token control that sends `X-App-Token`
- Analytics dashboards for Sales, Stock, Purchases, and Financials
- Period selector for Week, Month, 3 month, and YTD analysis
- Sales trend, weekday revenue, hourly sales, category ranking, and brand ranking
- Stock value by brand/category, stock antiquity, and low-stock watchlist
- Purchase pressure, supplier bill exposure, recent purchase orders, and bill-line preview
- Receivables, payables, working capital, and estimated profitability view
- Assisted Agent chat with suggested prompts
- Conversation history in the browser session
- Assistant metadata showing intent, tool, LLM provider, evidence trace, and request ID

## Current User Flow

| Step | User Action | Expected Result |
|---|---|---|
| 1 | Open `http://127.0.0.1:3000` | Branded Home surface loads |
| 2 | Confirm demo token | Token is stored in local storage and sent as `X-App-Token` |
| 3 | Refresh dashboard | Live Odoo dashboard data loads |
| 4 | Open Analytics | User can switch Sales, Stock, Purchases, and Financials views |
| 5 | Open Assisted Agent | User asks a plain-language business question |
| 6 | Expand metadata | Reviewer can see tool, provider, evidence, and request ID |

## Visual Standard

Use the layout, menu behavior, color system, typography, rounded cards, header/footer structure, and light EY-Parthenon-style visual language from:

```text
C:\Users\CC942ZE\OneDrive - EY\Desktop\LAKE\cursor_code\use_case_tracker
```

The Jhonny app has been adapted to that standard with a sticky top menu, branded client shell, white card surfaces, blue accent color, soft gradients, and a client-facing footer.

Current frontend implementation uses:

| File | Purpose |
|---|---|
| `frontend/app/page.tsx` | Main Jhonny app experience |
| `frontend/components/app-shell/*` | Header, app shell, profile menu, theme provider, and section cards |
| `frontend/components/ui/*` | Minimal UI primitives |
| `frontend/tailwind.config.ts` | Tailwind tokens and theme setup |
| `frontend/app/globals.css` | App-wide CSS variables and base styles |

## API Endpoints

```text
GET /health
GET /dashboard
POST /chat
POST /tools/{tool_name}
POST /webhooks/whatsapp
```

Agent request:

```json
{
  "question": "How much did we sell today?",
  "channel": "app"
}
```

Agent response includes the answer plus metadata such as `tool`, `data`, `evidence`, `tool_trace`, `visualization`, `llm_provider`, `intent`, and `request_id`.

## Optional Demo Auth

Set this in `.env`:

```env
APP_AUTH_TOKEN=retail-demo
```

When set, dashboard and agent API requests require `X-App-Token`. The browser app exposes a token input in the header and stores the value in local storage. The local frontend default is `retail-demo`.

## Suggested Demo Prompts

| Group | Prompts |
|---|---|
| Daily briefing | `Hi, how are you?`, `What should Jhonny focus on today?`, `What should I pay attention to this week?` |
| Sales | `How much did we sell today?`, `Which brands are selling best?`, `What products are growing or declining?` |
| Stock | `Should we buy more kids wetsuits?`, `Which products are at risk of stockout?`, `Which categories have too much stock?` |
| Purchases and margin | `Are purchases too high compared with sales?`, `Where are we losing margin by brand or category?`, `Which products have bad cost or price data?` |

## Tiago Tasks

1. Keep the current FastAPI contract stable for Rodrigo's WhatsApp work.
2. Rehearse the review demo end to end from Home to Analytics to Assisted Agent.
3. Validate that the top dashboard figures match Odoo UI before external review.
4. Keep improving mobile layout, loading states, empty states, and chart readability.
5. Add login only after the first review/demo loop confirms the product direction.
6. Keep the app focused on first buyer questions: sales, stock, purchases, margin, bills, receivables, and daily priorities.
7. Defer provider-specific Azure or AWS deployment work until cloud access is available and the local demo is approved.
