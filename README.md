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
- `/.github/workflows/azure-webapps-node.yml` — CI build/test + Azure deployment workflow
- `/.env.example` — shared local/cloud environment template

## Key technologies

- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pytest
- **Frontend:** TypeScript, Vite
- **CI/CD:** GitHub Actions, Azure Web Apps deploy action

## Local launch (testing)

### 1) Backend

```bash
cd /home/runner/work/nexus-b2b-lead-generation/nexus-b2b-lead-generation
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

In a new terminal:

```bash
cd /home/runner/work/nexus-b2b-lead-generation/nexus-b2b-lead-generation/frontend
npm install
npm run dev
```

Open the Vite URL (default `http://localhost:5173`) and verify backend health + sample leads render.

## Local validation

```bash
cd /home/runner/work/nexus-b2b-lead-generation/nexus-b2b-lead-generation
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

## Environment variables

Copy `.env.example` and set values for your environment:

- `VITE_API_BASE_URL`
- `API_PORT`
- `CORS_ORIGINS`
