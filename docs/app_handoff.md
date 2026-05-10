# App Handoff

Owner: Tiago

## Goal

Give the retailer a simple web app with dashboards and an agent chat surface. The first version should support the sales demo, not try to become a full BI tool.

Jhonny is the first client. He owns a family-style surf retail business, uses Odoo, and needs a browser-accessible app where he can ask questions about sales, bills, stock, purchases, and other daily owner topics. The app should also include predefined analytics dashboards that refresh from Odoo.

Rodrigo owns the WhatsApp prompting feature. The browser app remains the primary delivery surface for Jhonny while WhatsApp uses the same backend agent path.

## Current App

The app is local-first for now. Run the backend:

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

- Dashboard cards for today, month, YTD sales, and stock value
- Monthly sales bars
- Today category mix
- Stock value by category bars
- Low-stock table
- Agent chat input
- Suggested prompt buttons
- Conversation history in the browser session

## Visual Standard

Use the layout, menu behavior, color system, typography, rounded cards, header/footer structure, and light EY-Parthenon-style visual language from:

```text
C:\Users\CC942ZE\OneDrive - EY\Desktop\LAKE\cursor_code\use_case_tracker
```

The Jhonny app has been adapted to that standard with a sticky top menu, branded client shell, white card surfaces, blue accent color, soft gradients, and a client-facing footer.

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
  "question": "How much did we sell today?"
}
```

## Optional Demo Auth

Set this in `.env`:

```env
APP_AUTH_TOKEN=replace-with-demo-token
```

When set, dashboard and agent API requests require `X-App-Token`. The browser app prompts for it and stores it in local storage.

## Tiago Tasks

1. Keep the current FastAPI contract stable for Rodrigo's WhatsApp work.
2. Polish the current Next.js experience for a sales call:
   - Company logo and client name
   - Cleaner charts
   - Mobile layout
   - Loading states
3. Add login only after the first end-to-end demo is working.
4. Keep the app focused on the first buyer questions:
   - Sales today
   - Month-to-date sales
   - Stock value
   - Top categories
   - Low stock
   - Purchases vs sales
5. Defer Azure or AWS deployment work until cloud access is available and the local demo is stable.
