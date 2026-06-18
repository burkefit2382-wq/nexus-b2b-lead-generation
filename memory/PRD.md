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
- JWT auth + RBAC (user/admin), API keys (X-API-Key), refresh tokens.
- Lead engine: list/filter/search/stats/create/sell/delete + CSV export.
- **Monetization (Stripe)**: credit packages (Starter $29/10cr, Pro $99/50cr, Agency $299/200cr);
  scraped/premium leads are locked (contact masked) until unlocked with 1 credit; secure
  checkout (server-side prices, origin allowlist, atomic idempotent credit grant, session
  ownership check) + /api/webhook/stripe. Billing tab with return-polling.
- **People Intelligence**: POST /api/people-intel/scan → identity resolution + live digital
  footprint (social presence checks) + public records (breach) + AI profile + risk scoring;
  history scoped per-user (admin sees all). People Intel tab UI.
- AI: DeepSeek + Qwen via HF router (selectable in chat, scraper, people-intel); graceful fallback.
- 12 cloud OSINT tools + reports log.
- 24/7 multi-provider scraper (Hacker News + GitHub live; Reddit via OAuth) with OSINT/AI HQ filter.
- Tested: backend 36/36 pytest, frontend e2e — all green. Deployment check PASS.

## Known Constraints
- HF token needs **"Inference Providers" permission** (currently 403) → AI graceful/heuristic
  fallback until fixed. Reddit needs OAuth creds (REDDIT_*). Local Qwen 27B not runnable (no GPU).
- Stripe in TEST mode (sk_test_emergent); test card 4242 4242 4242 4242.

## Backlog / Next
- P0: HF "Inference Providers" permission; Reddit OAuth creds.
- P1: API-access subscription tier (recurring) on top of one-time credit packs.
- P2: People-intel rate limiting; lead unlock receipts/exports; usage analytics dashboard.
