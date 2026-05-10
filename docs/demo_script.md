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
| Demo token | Header token field contains the local `APP_AUTH_TOKEN`, usually `retail-demo` |
| Dashboard | Refresh returns live Odoo numbers |
| Agent chat | A stock, sales, purchase, or margin question returns an answer with evidence |
| OpenAI path | `py scripts/smoke_openai_chat.py "How much did we sell today?"` passes when OpenAI is required for the demo |

## Script

### 0:00-0:30 - Problem

"Most small retailers have the data, but not the time to read it. Sales, stock, purchase orders, invoices, and category performance live in the system, but the owner still asks the same questions manually every day."

### 0:30-1:00 - Home

Open `http://127.0.0.1:3000` and show the branded Jhonny Surf home page:

- Today's sales
- Daily profit estimate
- Last week sales estimate
- Profit margin
- Year-to-date sales
- Current stock value
- Supplier bill exposure

Say: "This is live from Odoo. No spreadsheet export."

### 1:00-2:10 - Analytics

Open the Analytics tab and quickly move through:

| Dashboard | Show |
|---|---|
| Sales | Period sales, daily trend, category and brand ranking |
| Stock | Stock value by brand/category, stock antiquity, low-stock watchlist |
| Purchases | Supplier bills, purchase activity, bill-line preview |
| Financials | Receivables, payables, working capital, profit margin estimate |

Position it as "not a full BI project, just the owner views needed for daily decisions."

### 2:10-3:20 - Assisted Agent

Ask:

```text
What should Jhonny focus on today?
```

Then ask:

```text
Are purchases too high compared with sales?
```

Then ask:

```text
Where are we losing margin by brand or category?
```

Expand the assistant metadata once and show the tool, LLM provider, evidence trace, and request ID. Position it as "the business owner asking the shop questions in plain language, with evidence from Odoo behind each answer."

### 3:20-4:00 - WhatsApp

If WhatsApp is connected, show the same interaction through WhatsApp:

```text
What should I focus on today?
```

Explain that this is the owner channel: no dashboard, just fast answers from trusted company data. If WhatsApp is not connected yet, position it as the next channel using the same backend agent.

### 4:00-4:40 - Business Value

Connect the demo to money:

- Less time spent asking staff for reports
- Better stock decisions
- Faster reorder decisions
- Better visibility across stores
- Daily owner briefing without manual work
- Earlier warning on bills, receivables, bad cost data, and overbuying

### 4:40-5:00 - Offer

"We can connect your system, build your first dashboard, and give you a WhatsApp business agent in a paid pilot. The first version focuses on sales, stock, and purchasing decisions."

## Questions The Demo Should Answer

- How much did we sell today?
- What is the current stock value?
- Which categories are selling?
- What is low in stock?
- What did we sell this month?
- Are we buying more inventory than we are selling?
- What should the owner focus on today?
- Where are we losing margin?
- Which products have bad price or cost data?
