<div align="center">

# 🛰️ NEXUS

**Autonomous lead-generation & corporate threat-intelligence SaaS for the Tampa Bay market.**

NEXUS continuously discovers local independent-service businesses, enriches them with AI,
passively scans their infrastructure for security exposures, and auto-drafts high-ticket
sales pitches — turning open-source intelligence into a self-running revenue funnel.

![Stack](https://img.shields.io/badge/stack-React%20%2B%20FastAPI%20%2B%20MongoDB-0b7285)
![AI](https://img.shields.io/badge/AI-HuggingFace%20(DeepSeek%2FQwen)-orange)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## ✨ Features

- **🔐 Auth & Monetization** — JWT (HTTP-only) auth, role-based access control, API keys, and Stripe
  for both credit packs and **pay-per-lead** checkout (score-tiered pricing).
- **🤖 24/7 Lead Scraper** — background worker discovers Tampa Bay (Hillsborough + Pinellas)
  independent-service businesses via OpenStreetMap, plus **Reddit** service-intent posts through
  Apify (hourly, hard **$5/day budget guard**).
- **🧠 AI Enrichment** — metered enrichment APIs (business / person / property / OSINT / composite lead
  scoring) powered by HuggingFace inference (DeepSeek V3.1 / Qwen2.5).
- **🛡️ Threat Intelligence** — passive domain scan: DNS + DNSSEC, SSL/TLS cert checks, security headers,
  sensitive subdomains, breach signals, and **Shodan** (open ports / services / known CVEs) — scored
  0–10, with AI-drafted outreach for high-ticket prospects, sent via **Resend**.
- **🔗 Scan-to-Pipeline** — scraped business domains are automatically threat-scanned by the worker.
- **📊 Intel Sources dashboard** — live status of every sensor (OSM, Reddit, Shodan, DNS/SSL, Email)
  with today's Apify spend vs budget.

## 🏗️ Architecture

```
React SPA  ──HTTPS──►  NGINX  ──/api──►  FastAPI (server.py, :8001)  ──►  MongoDB
                                                  ▲
                          APScheduler worker (worker.py) ── 24/7 scrape + Reddit + scan-to-pipeline
```

| Layer | Tech |
|---|---|
| Frontend | React, shadcn/ui, axios (`REACT_APP_BACKEND_URL`) |
| Backend | FastAPI, Motor (async MongoDB), APScheduler |
| AI | HuggingFace router (DeepSeek / Qwen) |
| Integrations | Stripe · Apify (Reddit) · Shodan · Resend · HaveIBeenPwned |

## 🚀 Getting started (local)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.production.example .env   # fill MONGO_URL, DB_NAME, JWT_SECRET, HF_TOKEN, etc.
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend
cd frontend
yarn install
yarn start
```

## 🔑 Environment variables (`backend/.env`)

| Key | Purpose |
|---|---|
| `MONGO_URL`, `DB_NAME` | Database |
| `JWT_SECRET` | Auth token signing |
| `HF_TOKEN` | HuggingFace AI inference |
| `STRIPE_API_KEY` | Payments |
| `APIFY_TOKEN`, `APIFY_DAILY_BUDGET_USD`, `REDDIT_INTERVAL_MIN` | Reddit scraping (budget-guarded) |
| `SHODAN_API_KEY` | OSINT host/CVE intel |
| `RESEND_API_KEY`, `SENDER_EMAIL` | Outbound pitch email |
| `RUN_SCHEDULER` | `false` on API container, `true` on worker |

## 📦 Deployment

- **Managed (Emergent):** one-click Deploy button — no infra setup.
- **Self-host (VPS):** see [`SELF_HOST.md`](./SELF_HOST.md) — `docker compose up -d --build`
  (mongo + api + worker + nginx/TLS), systemd auto-start, and GitHub Actions CI/CD included.

## 🗂️ Project layout

```
backend/   server.py (API)  ·  worker.py (scheduler)  ·  tests/
frontend/  src/components (Dashboard, tabs, Leads, Scrapers)  ·  Dockerfile  ·  nginx.conf
deploy/    nexus.service (systemd)
.github/   workflows/deploy.yml (CI/CD)
docker-compose.yml · SELF_HOST.md · DEPLOY.md
```

## 📄 License

MIT — see [`LICENSE`](./LICENSE).
