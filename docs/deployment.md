# Local-First Deployment Notes

## Current Decision

Keep the app local until the review demo is stable and cloud access is confirmed.

| Service | Local URL | Command |
|---|---|---|
| Backend API | `http://127.0.0.1:8000` | `py scripts/run_app.py` |
| Frontend app | `http://127.0.0.1:3000` | `cd frontend && npm run dev` |
| Health check | `http://127.0.0.1:8000/health` | `Invoke-RestMethod -Uri http://127.0.0.1:8000/health` |

Do not add provider-specific Azure or AWS automation until an account, subscription, resource group, or client hosting preference is confirmed.

## Hosting Shape

When hosting is needed, deploy two services:

| Service | Artifact | Runtime Notes |
|---|---|---|
| Backend API | Root `Dockerfile` | FastAPI, Odoo XML-RPC, LLM calls, WhatsApp webhook |
| Web app | `frontend/Dockerfile` | Next.js app, public backend URL, demo token UI |

`render.yaml` is included as a two-service Render blueprint. The same split also works on Railway, Fly.io, Azure Container Apps, AWS App Runner, or ECS Fargate.

Preferred target once cloud access exists:

| Option | Recommendation | Why |
|---|---|---|
| Azure Container Apps | Default first enterprise path | Fits the existing two-container split, managed secrets, HTTPS, logs, and likely Microsoft/EY alignment |
| Render | Fast review environment | Existing blueprint is already present and maps directly to the current services |
| AWS App Runner or ECS Fargate | Use if AWS access comes first | Equivalent container hosting path with Secrets Manager and CloudWatch |

## Backend Environment

Set these as managed secrets in the hosting provider:

```env
ODOO_URL=https://jhonny-surf.odoo.com
ODOO_DB=jhonny-surf-master-26611951
ODOO_USERNAME=loja@jhonnysurfstore.pt
ODOO_API_KEY=<rotated-odoo-api-key>
APP_AUTH_TOKEN=<demo-access-token>
APP_CORS_ORIGINS=https://<frontend-app-url>
WHATSAPP_ALLOWED_NUMBERS=351900000000
WHATSAPP_RATE_LIMIT_PER_MINUTE=20
PUBLIC_WHATSAPP_WEBHOOK_URL=https://<backend-api-url>/webhooks/whatsapp
TWILIO_AUTH_TOKEN=<twilio-auth-token-if-using-twilio>
WHATSAPP_APP_SECRET=<meta-app-secret-if-using-meta-cloud-api>
OPENAI_API_KEY=<openai-api-key>
OPENAI_MODEL=gpt-4o-mini
DATABRICKS_HOST=<optional-databricks-workspace-url>
DATABRICKS_TOKEN=<optional-databricks-token>
DATABRICKS_MODEL_ENDPOINT=<optional-serving-endpoint>
```

Rotate the Odoo key before deploying because development credentials should not be reused in hosted review or paid-pilot environments.

For local development, keep these values in `.env` only. For hosted environments, move them into managed secrets and never bake them into Docker images.

## Frontend Environment

```env
NEXT_PUBLIC_API_BASE_URL=https://<backend-api-url>
```

The frontend stores the demo token in browser local storage and sends it as `X-App-Token` to protected backend routes.

## Auth And CORS

The backend protects app endpoints with `APP_AUTH_TOKEN`.

Clients should send:

```text
X-App-Token: <demo-access-token>
```

Set `APP_CORS_ORIGINS` to the exact hosted frontend URL. For local development, keep:

```env
APP_CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000
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

## Validation Checklist

Run these before a stakeholder or client demo:

| Check | Command | Expected |
|---|---|---|
| Backend dependencies | `py -m pip install -r requirements.txt` | Install completes |
| Odoo authentication | `py scripts/test_connection.py` | Authenticates and reads sample data |
| Agent regression | `py scripts/evaluate_agent.py` | Deterministic routing checks pass |
| API security | `py scripts/evaluate_api_security.py` | Allowlist, rate-limit, and signature checks pass |
| Backend health | `Invoke-RestMethod -Uri http://127.0.0.1:8000/health` | Returns `{"status":"ok"}` |
| OpenAI path | `py scripts/smoke_openai_chat.py "How much did we sell today?"` | Returns provider `openai` when configured |
| Frontend build | `cd frontend && npm run build` | Production build succeeds |

## LLM Routing

The backend tries providers in this order:

1. OpenAI when `OPENAI_API_KEY` is set.
2. Databricks Model Serving when `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, and `DATABRICKS_MODEL_ENDPOINT` are set.
3. Deterministic routing when no LLM provider is configured.

Use `scripts/smoke_openai_chat.py` before demos that need proof the real OpenAI path is active.

## Logging

The FastAPI service writes structured JSON logs for:

- app chat questions
- WhatsApp messages
- selected tool and intent
- LLM provider
- tool trace summary
- latency
- success or failure
- request ID for `/chat`

For a paid pilot, connect these logs to the host's log viewer first. Add persistent analytics only after customer usage justifies it.

## WhatsApp URL

For local testing, expose the backend with a tunnel if a WhatsApp provider needs inbound internet access. After backend deployment, configure the provider webhook to:

```text
https://<backend-api-url>/webhooks/whatsapp
```

Use approved phone numbers only for the pilot.

If using Twilio, set `TWILIO_AUTH_TOKEN` and `PUBLIC_WHATSAPP_WEBHOOK_URL` so inbound requests are signature-checked against the exact public URL. If using Meta WhatsApp Cloud API, set `WHATSAPP_APP_SECRET` so `X-Hub-Signature-256` is verified. Keep `WHATSAPP_RATE_LIMIT_PER_MINUTE` enabled for pilot traffic.
