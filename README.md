# NEXUS B2B Lead Generation (MVP Skeleton)

This repository now includes a runnable MVP structure for local testing and CI validation.

## Codebase structure

- `/backend/app/main.py` — FastAPI app with:
  - `GET /health` health check
  - `GET /api/leads/mock` mock lead generator endpoint
- `/backend/tests/test_main.py` — API tests with `pytest`
- `/backend/requirements.txt` — runtime Python dependencies
- `/backend/requirements-dev.txt` — development/test dependencies
- `/frontend` — Vite + TypeScript frontend that calls backend endpoints
- `/infra/main.bicep` — Bicep subscription-level orchestration template
- `/infra/resources.bicep` — App Service + Static Web App resource definitions
- `/azure.yaml` — Azure Developer CLI service definitions
- `/.github/workflows/azure-dev.yml` — primary Azure Developer CLI provision + deploy workflow
- `/.github/workflows/deploy-backend.yml` — manual Render fallback deploy workflow
- `/.github/workflows/deploy-worker.yml` — manual Cloudflare Worker fallback deploy workflow
- `/.env.example` — shared local/cloud environment template

## Key technologies

- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pytest
- **Frontend:** TypeScript, Vite
- **Primary CI/CD:** GitHub Actions + Azure Developer CLI (`azd`)
- **Fallback/edge deploys:** Render API deploys and Cloudflare Workers through manual workflows
- **Infrastructure as Code:** Bicep

## Local launch (testing)

### 1) Backend

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL (default `http://localhost:5173`) and verify backend health + sample leads render.

## Local validation

```bash
npm --prefix frontend run build
PYTHONPATH=. python -m pytest backend/tests
```

## Primary deploy: Azure Developer CLI (`azd`)

`azd` provisions all Azure infrastructure **and** deploys both services in one command.

### Prerequisites

- [Install azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd) **v1.11.0 or later** (CI uses `1.11.0`)
- An Azure subscription with contributor access

To check your installed version:

```bash
azd version
```

To install or upgrade on Windows:

```powershell
winget install microsoft.azd
```

On macOS/Linux:

```bash
curl -fsSL https://aka.ms/install-azd.sh | bash
```

### First-time setup

```bash
# 1. Authenticate
azd auth login

# 2. Initialise the environment (pick a short name, e.g. "nexus-dev")
azd init

# 3. Provision resources + deploy in one step
azd up
```

`azd up` creates a resource group, an App Service (Python 3.11) for the backend, and an Azure Static Web App for the Vite frontend, then deploys both services.

### Subsequent deploys

```bash
azd deploy          # re-deploy code changes only
azd provision       # re-apply infrastructure changes only
```

### CI/CD with GitHub Actions

Set the following repository **variables** (not secrets) in GitHub → Settings → Secrets and variables → Actions:

| Variable | Description |
|---|---|
| `AZURE_CLIENT_ID` | Service principal / managed identity client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription ID |
| `AZURE_ENV_NAME` | `azd` environment name (e.g. `nexus-dev`) |
| `AZURE_LOCATION` | Azure region (e.g. `eastus`) |

Set the following repository **secrets** in GitHub → Settings → Secrets and variables → Actions:

| Secret | Description |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe live or test secret key for Azure App Service runtime |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `PRICE_ID` | Default Stripe price used by the membership checkout endpoint |
| `DATABASE_URL` | Production Postgres connection string for memberships and tracking |
| `RESEND_API_KEY` | Resend email API key |
| `RESEND_FROM` | Verified sender, for example `NEXUS <no-reply@mail.nexuscloud.sh>` |
| `WAITLIST_NOTIFY_TO` | Internal fulfillment/lead notification inbox |
| `HUBSPOT_ACCESS_TOKEN` | HubSpot private app token or service key |
| `HUBSPOT_PORTAL_ID` | HubSpot portal ID, for example `246668830` |

Then run `azd pipeline config` to wire up federated credentials automatically, or push to `main` to trigger `.github/workflows/azure-dev.yml`.

### What Azure receives

The Bicep infrastructure sets App Service runtime settings from the GitHub secrets above:

- `LAUNCH_HOST=0.0.0.0`
- `PUBLIC_BASE_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `PRICE_ID`
- `DATABASE_URL`
- `RESEND_API_KEY`
- `RESEND_FROM`
- `WAITLIST_NOTIFY_TO`
- `HUBSPOT_ACCESS_TOKEN`
- `HUBSPOT_PORTAL_ID`
- `ENVIRONMENT=production`

## Environment variables

Copy `.env.example` and set values for your environment:

- `VITE_API_BASE_URL`
- `DATABASE_URL`
- `API_PORT`
- `CORS_ORIGINS`

## Fallback deploys

Render and Cloudflare are no longer the primary automatic production path. They are kept as manual fallback/edge workflows:

```text
.github/workflows/deploy-backend.yml
.github/workflows/deploy-worker.yml
```

Use these only when intentionally deploying the Render backend fallback or Cloudflare Worker fallback.

For the Render fallback workflow, store `RENDER_API_KEY` as a GitHub Actions secret. The workflow defaults to service ID `srv-d91akdb7uimc73a2b8g0`, and you can override it at manual run time or by setting repository variable `RENDER_SERVICE_ID`.

## Cloudflare Workers deployment

`wrangler` is installed as a local devDependency. Use `npm run` scripts or `npx` — do **not** call `wrangler` directly on the command line.

```bash
# Authenticate with Cloudflare (run once)
npm run wrangler:login
# or: npx wrangler login

# Deploy the Worker
npm run cf:deploy
# or: npx wrangler deploy
```

### Custom domain (optional)

`wrangler.toml` includes a commented custom-domain template. To activate it:

1. Uncomment the `[[custom_domains]]` and `hostname` lines.
2. Set `hostname` to your domain (for example `app.example.com`).
3. Ensure the domain's zone is already in your Cloudflare account.
4. Run `npm run cf:deploy` — Wrangler will create the DNS record automatically.

Without this step the Worker is reachable on its default `raspy-hat-15da.<your-subdomain>.workers.dev` URL.

### Cloudflare 1033 quick fix

If you see **Error 1033**, the hostname is usually pointing to a missing/invalid Cloudflare tunnel target.

1. Test your Worker on the default `workers.dev` URL first (`npm run cf:deploy` output).
2. If `workers.dev` works but your custom hostname fails, remove stale tunnel/DNS records for that hostname in Cloudflare.
3. Re-deploy after setting `[[custom_domains]]` only for a hostname in a zone you own in this account.
