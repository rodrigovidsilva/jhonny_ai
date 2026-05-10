# Local-First Deployment Notes

## Current Decision

Keep the app local until the demo flow is stable and cloud access is available.

| Service | Local URL | Command |
|---|---|---|
| Backend API | `http://127.0.0.1:8000` | `py scripts/run_app.py` |
| Frontend app | `http://127.0.0.1:3000` | `cd frontend && npm run dev` |
| Health check | `http://127.0.0.1:8000/health` | `Invoke-RestMethod -Uri http://127.0.0.1:8000/health` |

Do not add Azure or AWS deployment automation until an account, subscription, or resource group is confirmed.

## Services

When hosting is needed, deploy two services:

1. Backend API: FastAPI, Dockerfile at project root
2. Web app: Next.js, Dockerfile in `frontend/`

`render.yaml` is included as a Render blueprint, but the same split works on Railway, Fly.io, Azure Container Apps, AWS App Runner, or ECS Fargate.

Preferred target once cloud access exists:

| Option | Recommendation | Why |
|---|---|---|
| Azure Container Apps | Default first choice | Fits the existing two-container split, managed secrets, HTTPS, logs, and likely Microsoft/EY alignment |
| AWS App Runner or ECS Fargate | Use if AWS access comes first | Equivalent container hosting path with Secrets Manager and CloudWatch |

## Backend Environment

Set these as managed secrets in the hosting provider:

```env
ODOO_URL=https://jhonny-surf.odoo.com
ODOO_DB=jhonny-surf-master-26611951
ODOO_USERNAME=loja@jhonnysurfstore.pt
ODOO_API_KEY=<rotated-odoo-api-key>
APP_AUTH_TOKEN=<demo-access-token>
WHATSAPP_ALLOWED_NUMBERS=351900000000
OPENAI_API_KEY=<openai-api-key>
OPENAI_MODEL=gpt-4o-mini
```

Rotate the Odoo key before deploying because the development key was exposed during setup.

For local development, keep these values in `.env` only. For hosted environments, move them into managed secrets and never bake them into Docker images.

## Frontend Environment

```env
NEXT_PUBLIC_API_BASE_URL=https://<backend-api-url>
```

## Health Check

```text
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

Latest local validation:

| Check | Result |
|---|---|
| Odoo authentication | Passed |
| Backend `/health` | Passed |
| Backend `/dashboard` | Passed with live data |
| Backend `/chat` | Passed with `stock_value` tool |
| Frontend production build | Passed with `npm run build` |

## Demo Auth

The backend protects app endpoints with `APP_AUTH_TOKEN`.

Clients should send:

```text
X-App-Token: <demo-access-token>
```

The web app stores this token in browser local storage for the demo.

## Logging

The FastAPI service writes structured JSON logs for:

- app chat questions
- WhatsApp messages
- selected tool
- latency
- success/failure

For a paid pilot, connect these logs to the host's log viewer first. Add persistent analytics only after customer usage justifies it.

## WhatsApp URL

For local testing, expose the backend with a tunnel if a WhatsApp provider needs to reach it. After backend deployment, configure the WhatsApp provider webhook to:

```text
https://<backend-api-url>/webhooks/whatsapp
```

Use approved phone numbers only for the pilot.
