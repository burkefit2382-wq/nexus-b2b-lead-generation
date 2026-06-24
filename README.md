<p align="center">
  <img src="YOUR_LOGO_FILE.png" width="180" alt="NEXUS Logo">
</p>

<h1 align="center">NEXUS Intelligence Platform</h1>
<h3 align="center">Data Intelligence • Autonomous OSINT • AI‑Driven Lead Generation</h3>

<p align="center">
  <img src="https://img.shields.io/badge/status-active-brightgreen">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img src="https://img.shields.io/badge/FastAPI-teal">
  <img src="https://img.shields.io/badge/AI-LLaMA-orange">
  <img src="https://img.shields.io/badge/OSINT-Automated-purple">
</p>

## Overview

NEXUS is a full-stack B2B lead generation platform. It exposes a **FastAPI** backend that enriches company data with OSINT signals and scores leads, paired with a **React / TypeScript** dashboard for searching and reviewing results.

```
nexus-b2b-lead-generation/
├── backend/          FastAPI service
│   ├── app/
│   │   ├── main.py   API routes
│   │   ├── models.py Pydantic schemas
│   │   └── osint.py  Lead enrichment logic
│   ├── tests/
│   ├── requirements.txt
│   └── startup.py
└── frontend/         React + Vite + TypeScript dashboard
    ├── src/
    │   ├── App.tsx
    │   └── App.css
    └── index.html
```

## Local Development

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend

```bash
# point the dev server at your local API
echo "VITE_API_URL=http://localhost:8000" > frontend/.env.local

npm --prefix frontend install
npm --prefix frontend run dev
# Dashboard available at http://localhost:5173
```

## Build

```bash
npm --prefix frontend run build        # outputs to frontend/dist/
PYTHONPATH=. python -m pytest backend/tests   # run backend tests
```

## Deployment (Azure Web Apps)

The repository ships a ready-to-use GitHub Actions workflow at
`.github/workflows/azure-webapps-node.yml` that:

1. **Builds** the React frontend and runs the Python test suite on every push to `main`.
2. **Deploys** the frontend static bundle and the FastAPI backend to two separate Azure Web Apps.

### One-time setup

| Step | Action |
|------|--------|
| 1 | Create two Azure Web Apps – one for the React frontend (Node runtime or static), one for the FastAPI backend (Python runtime). |
| 2 | Download the **Publish Profile** for each app from the Azure Portal (Overview → Get publish profile). |
| 3 | Add two repository secrets in GitHub → Settings → Secrets and variables → Actions: `AZURE_WEBAPP_PUBLISH_PROFILE` (frontend) and `AZURE_BACKEND_PUBLISH_PROFILE` (backend). |
| 4 | Add two repository variables: `AZURE_FRONTEND_APP_NAME` and `AZURE_BACKEND_APP_NAME` matching your Azure app names. |
| 5 | Set `VITE_API_URL` in the frontend build environment (or Azure App Settings) to point to your backend URL. |

Push to `main` and the workflow will take care of the rest.

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/leads/search` | Search leads (JSON body) |
| `GET` | `/api/leads/search?company_name=…` | Search leads (query params) |

Interactive docs: `http://<backend-url>/docs`

## License

Apache 2.0 – see [LICENSE](LICENSE).
