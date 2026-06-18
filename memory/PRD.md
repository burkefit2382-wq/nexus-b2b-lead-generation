# NEXUS — Product Requirements Document

## Original Problem Statement
User uploaded `NEXUS.zip` — a locally-built (Windows) FastAPI OSINT + AI lead-generation
app — and asked to "launch and deploy my SaaS". Ported to the Emergent cloud stack
(FastAPI on 8001 + React on 3000 + MongoDB) and made cloud-deployable.

## User Choices
- AI: user-provided Hugging Face token → DeepSeek via HF router (local Qwen not feasible in cloud).
- OSINT: keep only cloud-native tools (no holehe/maigret/theHarvester/Scrapy).
- Auth: JWT email/password, multi-user + role-based access control + API-key generation.
- Design: modern redesign (tactical "OSINT command center", lime/cyan on near-black).

## Architecture
- Backend `/app/backend/server.py`: FastAPI, motor/MongoDB, JWT (httpOnly cookies) + RBAC
  (`require_admin`) + API-key auth (`X-API-Key`, sha256-hashed). DeepSeek via HF router.
- Frontend `/app/frontend/src`: React (CRA/craco), AuthContext, Login + Dashboard with
  Overview / Lead Engine / OSINT Tools (12) / NEXUS AI / Reports / API Keys / Admin tabs.
- Seed: admin@nexus.io + 4 sample leads on startup (idempotent).

## Implemented (2026-06-18)
- JWT auth (register/login/logout/me/refresh), bcrypt, RBAC (user/admin), API keys (X-API-Key).
- Lead engine: list/filter/search/stats/create/sell/delete + CSV export.
- AI: DeepSeek + Qwen via HF router (model-selectable in chat & scraper); graceful fallback.
- 12 cloud OSINT tools + reports log.
- **24/7 Lead Scraper engine** (APScheduler, AsyncIOScheduler): multi-provider
  (Hacker News + GitHub working from cloud; Reddit via OAuth when creds set), OSINT intent
  pre-filter + AI/heuristic HQ scoring, dedup, contact extraction, configurable sources/
  interval/min-score, manual trigger, live feed. Self-healing source_site backfill on startup.
- Frontend: Lead Scrapers control panel, AI model selector, all dashboards.
- Tested: backend 26/26 pytest, frontend e2e — all green. Deployment check PASS.

## Known Constraints
- HF token needs the **"Inference Providers" permission** (currently 403) → AI returns graceful
  error / scraped leads tagged `ai_pending` until fixed. Heuristic scoring works meanwhile.
- Reddit/Craigslist block datacenter IPs → Reddit needs OAuth creds (REDDIT_CLIENT_ID/SECRET/
  USERNAME/PASSWORD). HN + GitHub work without auth.
- Local Qwen 3.6-27B not runnable in-container (no GPU) → Qwen served via HF router instead.

## Backlog / Next
- P0: HF token "Inference Providers" permission → enable DeepSeek/Qwen scoring.
- P1: Reddit OAuth creds for home-remodeling/cleaning niche leads.
- P1: More providers (StackExchange, RSS, Reddit) + per-source error reporting.
- P2: Stripe billing (sell leads / seats / API access); usage analytics; scraper rate-limit.
