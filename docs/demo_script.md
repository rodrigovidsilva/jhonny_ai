# 5-Minute Demo Script

## Audience

Small retail owner or operator with sales, stock, purchasing, and customer data spread across Odoo, POS, e-commerce, or spreadsheets.

## Core Message

Retail Agent turns operational data into daily decisions. The owner can open a dashboard or ask the business directly through chat or WhatsApp.

## Local Demo Setup

Before the call, confirm:

| Check | Expected |
|---|---|
| Web app | `http://127.0.0.1:3000` opens |
| Backend health | `http://127.0.0.1:8000/health` returns `{"status":"ok"}` |
| Demo token | Browser has the local `APP_AUTH_TOKEN` from `.env` |
| Dashboard | Refresh data returns live Odoo numbers |
| Agent chat | A stock or sales question returns an answer |

## Script

### 0:00-0:30 - Problem

"Most small retailers have the data, but not the time to read it. Sales, stock, purchase orders, invoices, and category performance live in the system, but the owner still asks the same questions manually every day."

### 0:30-1:30 - Dashboard

Open `http://127.0.0.1:3000` and show:

- Today's sales
- Month-to-date sales
- Year-to-date sales
- Current stock value
- Monthly sales trend
- Stock value by category
- Low-stock products

Say: "This is live from Odoo. No spreadsheet export."

### 1:30-2:30 - Agent Chat

Ask:

```text
How much did we sell today?
```

Then ask:

```text
What is our stock value?
```

Then ask:

```text
What categories sold today?
```

Position it as "the business owner asking the shop questions in plain language."

### 2:30-3:30 - WhatsApp

If WhatsApp is connected, show the same interaction through WhatsApp:

```text
What is my stock value?
```

Explain that this is the owner channel: no dashboard, just fast answers from trusted company data. If WhatsApp is not connected yet, position it as the next channel using the same backend agent.

### 3:30-4:30 - Business Value

Connect the demo to money:

- Less time spent asking staff for reports
- Better stock decisions
- Faster reorder decisions
- Better visibility across stores
- Daily owner briefing without manual work

### 4:30-5:00 - Offer

"We can connect your system, build your first dashboard, and give you a WhatsApp business agent in a paid pilot. The first version focuses on sales, stock, and purchasing decisions."

## Questions The Demo Should Answer

- How much did we sell today?
- What is the current stock value?
- Which categories are selling?
- What is low in stock?
- What did we sell this month?
- Are we buying more inventory than we are selling?
