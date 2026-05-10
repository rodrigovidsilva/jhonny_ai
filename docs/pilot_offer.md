# Paid Pilot Offer

## Product Name

Retail Agent POC

## One-Liner

An AI business copilot for small retailers that connects to POS, stock, and accounting data, then answers owner questions through dashboards, chat, and WhatsApp.

## Target Customer

Small retailers with:

- 1-10 stores
- POS and stock software
- Owner-led operations
- Recurring questions about sales, inventory, buying, and cash tied in stock
- Limited time for manual reporting

Good first verticals:

- Surf and outdoor retail
- Fashion and footwear
- Specialty retail
- Sports equipment
- Lifestyle stores

## Buyer Pain

The buyer already has data, but the data does not create daily decisions without manual work. The owner wants to know:

- What did we sell today?
- What is selling by category?
- How much money is tied in stock?
- What products are low in stock?
- Are purchases ahead of sales?
- Which store needs attention?

## Pilot Scope

Duration: 2-4 weeks

Included:

- Connect to one operational system, starting with Odoo
- Build core dashboards
- Add business question answering in the web app
- Add WhatsApp questions for approved owners when provider access is available
- Weekly review call
- End-of-pilot recommendation report

Not included in the first pilot:

- Forecasting
- Custom ERP workflows
- Customer segmentation
- Deep accounting reconciliation
- Full multi-tenant SaaS admin

## Pricing

Recommended first offer:

- Setup fee: EUR 1,500-3,000
- Monthly pilot fee: EUR 300-900

Simple anchor:

```text
EUR 2,000 setup + EUR 500/month
```

Discount only in exchange for:

- Testimonial
- Permission to use anonymized metrics
- Introduction to 2-3 similar retailers

## Success Criteria

The pilot is successful if the owner uses the product weekly to answer business questions and can name at least one decision it improved.

Track:

- Number of dashboard sessions
- Number of agent questions
- Number of WhatsApp questions
- Time saved on manual reporting
- Stock or purchasing decisions influenced

## Delivery Approach

Start local-first for the Jhonny proof point:

1. Validate the local web app and backend against live Odoo data.
2. Run the owner demo from `http://127.0.0.1:3000`.
3. Add WhatsApp provider testing through a temporary tunnel if needed.
4. Move to hosted deployment only after the demo flow is stable and cloud access exists.

Preferred hosting path is Azure Container Apps because it fits the current backend/frontend container split and likely Microsoft/EY alignment. AWS App Runner or ECS Fargate remains a valid alternative if AWS access is available first.

## Sales Demo Flow

1. Show current sales and stock dashboards.
2. Ask a question in the app.
3. Show low-stock and category insights.
4. Ask the same question through WhatsApp if the provider is connected.
5. Offer a paid pilot connected to their system.

## Qualification Questions

- What system do you use for POS and stock?
- How many stores do you operate?
- Who checks sales and stock today?
- What reports do you look at every week?
- What questions do you ask your team repeatedly?
- Would WhatsApp answers be useful for the owner or manager?

## Near-Term Revenue View

This can make money soon if sold as an operational tool with fast setup and narrow scope. The first customers should pay for outcomes, not for AI novelty. Avoid building a broad platform before 3-5 paid pilots confirm the repeatable pain.
