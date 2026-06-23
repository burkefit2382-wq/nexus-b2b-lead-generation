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
- **Corporate Threat Intel (owner-only)**: scan a company domain (SPF/DMARC, sensitive subdomains,
  risky open ports, missing security headers, breach) → AI-assisted 0-10 risk score (clamped).
  Risk > 5 → flagged HIGH-TICKET (admin-only) + auto-drafted professional AI sales pitch (uses
  editable outreach profile: sender/brand/services/CTA). Email SENDING pending provider choice
  (draft + copy works now). Endpoints: /api/threat/scan|reports|outreach-profile (all require_admin).
- Tested: backend 45+ pytest, frontend e2e (iterations 1-6) — all green.

## Implemented (2026-06-18 — pay-per-lead)
- **Stripe Pay-Per-Lead (pay-as-you-go)**: locked scraped leads expose a score-tiered price
  (score >=70 -> $15, >=40 -> $7, else $3) via `lead_price()`. `POST /api/leads/{id}/buy`
  creates a direct Stripe checkout for one lead (no pre-bought credits); on settlement
  (`_settle_payment`, kind="lead") the buyer is added to that lead's `unlocked_by`.
  `/payments/status` returns `kind`/`lead_id`; Billing poll shows "lead unlocked" message.
  Frontend: lime "$price" Buy button per locked lead in Lead Engine (`lead-buy-{id}`).
  Verified: 27 buy buttons render for normal user; live Stripe session created ($15 for score-95 lead).

## Implemented (2026-06-18 — Tampa Bay scraping, worker, pipeline, email)
- **Broadened scraping → Tampa Bay independent services** (Hillsborough + Pinellas): switched scraper
  to **OpenStreetMap/Nominatim** (free, no key, cloud-accessible) — Craigslist & Reddit block our
  datacenter IP (403). 16 service categories (plumbing, electrical, HVAC, landscaping, handyman,
  cleaning, painting, roofing, pest, remodeling, pressure washing, moving, pool, auto, tree, flooring)
  × 5 locales (Tampa, St Pete, Clearwater, Brandon, Largo), throttled 1.1s/req. New business-lead path
  (`_process_business`) scores by completeness (website/phone/city), geo-tags FL. `sources_version`
  migration. Verified: 20 real businesses with websites scraped in one cycle.
- **P0 Background Worker**: APScheduler extracted to `backend/worker.py` (standalone). API gates the
  in-process scheduler behind `RUN_SCHEDULER` (default true in preview so scraping still runs; set
  false in prod). docker-compose adds a `worker` container (RUN_SCHEDULER=true) + api RUN_SCHEDULER=false.
  Verified: worker boots, starts scheduler, runs cycle.
- **P1 Scan-to-pipeline**: qualifying scraped leads with a real company domain auto-trigger a Threat
  Intel scan (`_auto_threat_pipeline` → `_run_threat_scan`, source="scraper-auto", deduped). Verified:
  20 auto threat reports generated from scraped business websites (high-ticket flagged).
- **P1 Email (Gmail SMTP)**: `POST /api/threat/reports/{id}/send-email` sends the AI pitch via Gmail
  SMTP (smtplib SSL:465, GMAIL_USER/GMAIL_APP_PASSWORD). Frontend "Send via Gmail" button in Threat
  Intel. NOTE: BLOCKED — provided password is the account password, not a 16-char Gmail **App Password**
  (Gmail returns 535 Bad Credentials). Needs an App Password (2-Step Verification on) to send.

## Implemented (2026-06-19 — Reddit via Apify, budget-guarded hourly)
- **Reddit leads via Apify** (Reddit blocks our datacenter IP on all direct methods: json/old.reddit/oauth
  all 403). Uses Apify actor `trudax/reddit-scraper-lite` over HTTPS (`fetch_apify_reddit`, async
  start→poll→fetch pattern). Subreddits: tampa, StPetersburgFL, Clearwater, HillsboroughCounty,
  stpetersburg → service-intent posts → existing intent pipeline (AI scored).
- **Separate hourly schedule** (`run_reddit_cycle`, REDDIT_INTERVAL_MIN=60) distinct from the 30-min OSM
  `run_scrape_cycle` (which now skips apify sources). Scheduled by `reschedule()` + worker.py.
- **Hard $5/day budget guard**: `db.apify_usage` tracks daily results/spend; caps before each run
  (cost $0.0034/result). Env: APIFY_DAILY_BUDGET_USD, APIFY_COST_PER_RESULT. `/api/scraper/status` exposes
  reddit_spend_today_usd/budget/next run; `/api/scraper/trigger?source=reddit|all` for manual runs.
- Verified live: 30 posts fetched ($0.10 spend), 6 Tampa Bay service-intent leads created.
- NOTE: changes on PREVIEW; REDEPLOY to push to production + ensure APIFY_TOKEN is in production env.


## Known Constraints
- AI is LIVE: DeepSeek-V3.1 (`deepseek-ai/DeepSeek-V3.1:novita`) + Qwen (`Qwen/Qwen2.5-72B-Instruct`)
  via HF router with a working token (Inference Providers permission granted).
- Reddit scraping deferred (needs script-app client_id/secret — user skipped). HN + GitHub run 24/7.
- Local Qwen 27B not runnable (no GPU) → Qwen served via HF router.
- Stripe in TEST mode (sk_test_emergent); test card 4242 4242 4242 4242.

## Backlog / Next
- P0: HF "Inference Providers" permission; Reddit OAuth creds.
- P1: API-access subscription tier (recurring) on top of one-time credit packs.
- P1 (tech debt): split server.py (~2540 lines) into modules (auth/leads/enrichment/storefront/threat/osint/payments).
- P2: People-intel rate limiting; lead unlock receipts/exports; usage analytics dashboard.

## Changelog
- 2026-06-23 — **Intel Marketplace UI v2 (enterprise SOC) + RFP portal**: bundle catalog strip (sector
  aggregates: count/avg-confidence/from-price/strategic via Mongo aggregation in `GET /storefront/leads`);
  cards refined to "Llama 3 · Accuracy Vector" score, geometric tier badges (▲ Strategic / ▪ Tactical /
  ● Operational), Threat-Level pill (derived from risk_matrix), friendly verification node badges
  ([MX Match] [Registry Verified] [Footprint Consistent]…). New **Request Agency Scope / Submit RFP** modal
  (gov/municipal intake: agency, contact, email, regions, sectors, budget, timeline, classification, scope)
  → `POST /api/storefront/rfp` (+ admin `GET /api/storefront/rfp`). Verified via curl + UI (bundle filter,
  RFP submit success). Design blueprint: `/app/design_guidelines.json`. PREVIEW only — REDEPLOY to push.
- 2026-06-23 — **Intelligence Marketplace (per-lead storefront + gov-grade enrichment)**:
  Llama 3 (`meta-llama/Llama-3.3-70B-Instruct` via HF router, deepseek fallback) + OSINT verification
  produce an Intelligence Payload: `data_confidence_score` (0-100), `cross_verification`
  (Email_Syntax_Valid/Domain_MX_Match/Public_Registry_Verified/Social_Footprint_Consistent/
  Phone_Format_Valid/Geo_Located), `risk_matrix` ([{flag,severity}]), `operational_value_tier`
  (Strategic/Tactical/Operational). New lead fields: `price_per_lead` (credits 5/3/1), `purchase_status`
  (available/reserved/sold), `buyer_user_id`, `ready_to_sell` (legacy leads backfilled at startup).
  Endpoints: `POST /api/enrichment/process-leads` (admin), `GET /api/storefront/leads` (masked browse +
  facet filters), `POST /api/storefront/purchase-leads` (credit-based, atomic available->sold, returns
  full payload). Frontend: new **Intel Marketplace** tab (`Storefront.jsx`). testing_agent 14/14 backend +
  full frontend, 0 issues. PREVIEW only — REDEPLOY to push.
- 2026-06-23 — Recruiter-ready repo docs: `docs/API.md` (full endpoint reference), `CONTRIBUTING.md`,
  `frontend/.env.example`, README Documentation section.
- 2026-06-23 — Deployment readiness: removed `.env`/`.env.*`/`*.env` from `.gitignore` (platform needs
  env files); deployment_agent PASS.
- 2026-06-23 — **Prod crash-loop fix**: `AsyncIOMotorClient` was created at module-import time (before the
  event loop), causing silent connection failures / pod restarts under Atlas (mongodb+srv). Moved client
  creation into the `startup` event (server.py) and into `worker.py main()`; added graceful
  `scheduler.shutdown()` on app shutdown. Verified in preview (clean boot + login). REDEPLOY required.
- Resend custom domain: DNS for `mail.nexuscloud.sh`/`nexuscloud.sh` not yet verified in Resend dashboard;
  app sends from `onboarding@resend.dev` until verified.
