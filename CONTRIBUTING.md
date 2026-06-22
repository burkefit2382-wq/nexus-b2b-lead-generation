# Contributing to NEXUS

Thanks for your interest in contributing! This guide covers local setup, coding
standards, and the pull-request workflow.

## Tech Stack

- **Backend:** FastAPI · MongoDB · APScheduler (background worker)
- **Frontend:** React (CRA) · Tailwind · shadcn/ui
- **Integrations:** Stripe, Resend, Shodan, Apify, Hugging Face

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+ and Yarn
- MongoDB (local or Docker)

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.production.example .env   # then fill in your values
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### Background Worker
```bash
cd backend
python worker.py
```

### Frontend
```bash
cd frontend
cp .env.example .env              # set REACT_APP_BACKEND_URL
yarn install
yarn start
```

The full stack can also be launched with Docker:
```bash
docker compose up --build
```

## Environment Variables

Backend secrets live in `backend/.env` (never commit real keys). See
`backend/.env.production.example`. Frontend config lives in `frontend/.env`
(see `frontend/.env.example`). The frontend must always call the API via
`REACT_APP_BACKEND_URL`.

## Coding Standards

- **Routes:** every backend API route is prefixed with `/api`.
- **Config:** read all URLs, ports, and credentials from environment variables —
  no hardcoded secrets or defaults that mask missing config.
- **Mongo:** never return raw `ObjectId`; serialize documents before responding.
- **Frontend:** keep components small and focused; add a `data-testid` to every
  interactive or user-facing element.
- **Commits:** use clear, present-tense messages (e.g. `add pay-per-lead checkout`).

## Pull Request Workflow

1. Fork and create a feature branch: `git checkout -b feat/my-feature`.
2. Make focused changes with descriptive commits.
3. Verify the app runs (backend health check + frontend loads) before pushing.
4. Open a PR describing **what** changed and **why**, linking any related issue.
5. Keep PRs scoped — one logical change per PR.

## Reporting Issues

Open an issue with reproduction steps, expected vs. actual behavior, and relevant
logs or screenshots. For security disclosures, please contact the maintainer
privately instead of filing a public issue.
