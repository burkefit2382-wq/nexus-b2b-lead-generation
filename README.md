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
- `/.github/workflows/azure-webapps-node.yml` — CI build/test + Azure Web Apps deploy workflow
- `/.github/workflows/azure-dev.yml` — Azure Developer CLI provision + deploy workflow
- `/.env.example` — shared local/cloud environment template

## Key technologies

- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pytest
- **Frontend:** TypeScript, Vite
- **CI/CD:** GitHub Actions, Azure Web Apps deploy action, Azure Developer CLI (`azd`)
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

## Deploy for Azure testing

1. Create your Azure Web App.
2. Set repository secret:
   - `AZURE_WEBAPP_PUBLISH_PROFILE`
3. Update workflow variable in `/.github/workflows/azure-webapps-node.yml`:
   - `AZURE_WEBAPP_NAME`
4. Push to `main` (or run workflow manually).
5. Open deployed app URL from workflow output and run smoke checks.

## Deploy with Azure Developer CLI (`azd`)

`azd` provisions all Azure infrastructure **and** deploys both services in one command.

### Prerequisites

- [Install azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- An Azure subscription with contributor access

### First-time setup

```bash
# 1. Authenticate
azd auth login

# 2. Initialise the environment (pick a short name, e.g. "nexus-dev")
azd init

# 3. Provision resources + deploy in one step
azd up
```

`azd up` creates a resource group, an App Service (Python 3.11) for the FastAPI backend, and an Azure Static Web App for the Vite frontend, then deploys both services.

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

Then run `azd pipeline config` to wire up federated credentials automatically, or push to `main` to trigger `.github/workflows/azure-dev.yml`.

## Environment variables

Copy `.env.example` and set values for your environment:

- `VITE_API_BASE_URL`
- `API_PORT`
- `CORS_ORIGINS`

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

The Worker ships with a `[[custom_domains]]` block in `wrangler.toml`. To activate it:

1. Open `wrangler.toml` and replace `YOUR_CUSTOM_DOMAIN` with your domain (e.g. `app.example.com`).
2. Ensure the domain's zone is already in your Cloudflare account.
3. Run `npm run cf:deploy` — Wrangler will create the DNS record automatically.

Without this step the Worker is reachable on its default `raspy-hat-15da.<your-subdomain>.workers.dev` URL.
