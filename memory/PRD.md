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
- **Enrichment Engine (Clearbit/Apollo-style)**: 5 AI-backed endpoints — `/api/enrich/business`
  (firmographics: industry/employees/tech_stack/quality_score), `/person` (footprint + AI profile),
  `/property` (AI estimate), `/osint` (identity + accounts), `/lead` (composite + weighted score/grade)
  + `/enrich/history` + `/enrich/pricing`. **Metered/paid API**: each call consumes credits
  (business/person/property/osint = 1, composite lead = 3) via atomic deduction; 402 when out of
  credits; works for dashboard users AND external `X-API-Key` developers. Frontend "Enrichment" tab
  shows per-call cost + balance.
- Refactored into modular components (Leads.jsx, Scrapers.jsx, Dashboard Sidebar/Topbar/hook, helpers.js).
- Tested: backend 36/36 pytest + 5 enrich endpoints, frontend e2e (iterations 1-5) — all green.

## Known Constraints
- AI is LIVE: DeepSeek-V3.1 (`deepseek-ai/DeepSeek-V3.1:novita`) + Qwen (`Qwen/Qwen2.5-72B-Instruct`)
  via HF router with a working token (Inference Providers permission granted).
- Reddit scraping deferred (needs script-app client_id/secret — user skipped). HN + GitHub run 24/7.
- Local Qwen 27B not runnable (no GPU) → Qwen served via HF router.
- Stripe in TEST mode (sk_test_emergent); test card 4242 4242 4242 4242.

## Backlog / Next
- P0: HF "Inference Providers" permission; Reddit OAuth creds.
- P1: API-access subscription tier (recurring) on top of one-time credit packs.
- P2: People-intel rate limiting; lead unlock receipts/exports; usage analytics dashboard.
