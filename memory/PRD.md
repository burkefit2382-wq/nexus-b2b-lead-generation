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
- JWT auth (register/login/logout/me/refresh), bcrypt, brute-force-safe login.
- RBAC: admin-only `/api/admin/users` + role update; user/admin roles.
- API keys: generate (shown once) / list / revoke; machine auth via `X-API-Key`.
- Lead engine: list/filter/search/stats/create/sell/delete + CSV export.
- AI: DeepSeek enrichment + chat (graceful error when token invalid).
- 12 cloud OSINT tools: dns, whois, ip, geolocate, phone, social, breach, subdomains,
  portscan, metadata, dork, shodan + reports log.
- Tested: backend 19/19 pytest, frontend Playwright e2e — all green.
- Deployment check: PASS (deployable); query limits added.

## Known Constraints
- Hugging Face token provided (`hf_KPweOeKQkePU`) is INVALID/truncated → AI returns a graceful
  error until a valid full `hf_...` token is set in `/app/backend/.env` (HF_TOKEN).
- Local Qwen 3.6-27B not runnable in this container (no GPU).

## Backlog / Next
- P1: Add valid HF token → enable AI enrichment/chat.
- P1: Real lead scrapers (replace Scrapy spiders with cloud-safe ingestion / CSV import).
- P2: API-key scopes/rate-limits; usage dashboard.
- P2: Billing (Stripe) to monetize lead exports / seats.
- P2: Frontend live-search debounce; pagination on leads & users.
