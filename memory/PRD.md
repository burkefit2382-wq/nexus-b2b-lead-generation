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
- 2026-07-04 (2) — **Auto-attach Sample Pilot Pack PDF to outreach emails (verified).**
  `send_email()` now supports `attachments` (Resend `content` as List[int] + `content_type`; Gmail fallback via
  MIMEApplication). `_sample_pack_attachment()` builds the 5-lead PDF. Wired into all 3 send paths: sandbox test,
  live campaign (`OutreachSendReq.attach_sample_pack`), and auto-sweep (`AutoOutreachCfg.attach_sample_pack`).
  Frontend: "Attach this pack (PDF)…" checkbox in the Sample Pilot Pack card (attach-sample-checkbox), passed on
  sandbox send + persisted via Save. LIVE-VERIFIED: sandbox send w/ attachment → HTTP 200 (Resend accepted PDF)
  to burkefit2382@gmail.com. testing_agent iteration_16: 100% (toggle, checked send, config round-trip, regression).
  Also confirmed earlier: `mail.nexuscloud.sh` domain verified + inboxing (live test to user's Gmail landed).

- 2026-07-04 — **Sample Pilot Pack + A-Leads/Astro marketability chart (verified).**
  (1) One-click **Sample Pilot Pack** in the admin Outreach tab: 5 HQ (92+) cleaning-demand leads —
  3 residential home-cleaning + 2 commercial — across Pinellas/Hillsborough/Pasco (Palm Harbor, Wesley Chapel,
  Tampa, Clearwater, Brandon), scores 96/94/93/95/92. Backend `GET /api/outreach/sample-pack` (JSON),
  `.csv` (StreamingResponse), `.pdf` (fpdf2) — all admin-only, curl-verified. Frontend `OutreachPanel` card
  (`sample-pack-card`) with Preview/PDF/CSV buttons (blob download). Contacts masked; clearly a representative
  SAMPLE. Added `fpdf2==2.8.7` to requirements.txt.
  (2) **compare.html** reworked for marketability head-to-head: NEXUS vs **A-Leads** vs **Astro** cost-per-lead
  chart ($35/$60/$55, exact-scaled), attribute table, and a CSS **Marketability scorecard** (8 attributes ×3
  vendors, composite NEXUS ~94 / A-Leads ~55 / Astro ~56) — figures labeled editable estimates.
  testing_agent iteration_15: 100% (UI + endpoints); compare.html screenshot-verified.
  NOTE: only 2 real `cleaning` leads exist in DB (36 total 92+), so the pack is curated representative sample
  per user's chosen default (option a).

- 2026-06-30 (4) — **Complexity slice #2 (verified).** Decomposed the remaining high-complexity units:
  Frontend `Storefront()` (C24) → `StorefrontFilters` + `IntelGrid` + `CartBar`; `IntelCard()` (C17) →
  `VerificationNodes` + `RiskMatrix`; `OutreachPanel()` (C25) → extracted `OutreachHistoryTable`.
  Backend `fetch_osm()` (C23) → `_osm_record_to_lead`; `fetch_apify_reddit()` (C26) → `_apify_reddit_payload` +
  `_apify_run_reddit` + `_apify_reddit_item_to_lead`. All presentational/extract-method (behavior-preserving);
  backend helpers unit-verified via python; testing_agent iteration_14: 100% pass (Marketplace filters/cards/
  cart/RFP + Outreach history), 0 console/key warnings. All code-review complexity findings now addressed.

- 2026-06-30 (3) — **2nd code-review pass: hook-dep warnings fixed; false-positives triaged.**
  Legit fix: added `// eslint-disable-next-line react-hooks/exhaustive-deps` to 5 intentional mount/refresh
  effects (AdminPanels MonitorPanel/AuditPanel/OutreachPanel/PilotLeadsPanel + ThreatIntel loadReports) —
  build now compiles clean, 0 warnings (blindly adding the unmemoized `load` fns to deps would cause infinite
  loops, so suppression is the correct + review-endorsed fix). testing_agent iteration_13: 100% pass, no regressions.
  FALSE POSITIVES (no change — would be wrong to "fix"): (a) "3 undefined variables" — pyflakes clean across all
  files (3rd confirmation); (b) server.py:1794/1820 `ai is not None` — `is`/`is not` with None is PEP8-correct;
  (c) test `is True/False/None` comparisons — idiomatic; converting to `==` would introduce E712 lint errors.
  ALREADY DONE previously: AuthContext console statements wrapped in NODE_ENV; array-index keys fixed.
  STILL DEFERRED (P2): remaining complexity refactors (Storefront C24, OutreachPanel C25, fetch_osm, fetch_apify_reddit),
  Storefront:368 useMemo (trivial 2-elem op — over-engineering), and type-hint coverage.

- 2026-06-30 (2) — **Code-review complexity refactor (verified).**
  Addressed the two "most critical" complexity findings without regressions:
  (1) **Frontend module split** — the monolithic `components/tabs.jsx` (1078 lines) was split into a
  `components/tabs/` folder (one file per panel: Overview, PeopleIntel, Billing, ThreatIntel, Enrichment,
  Osint, AIChat, ApiKeys, Reports, Admin, AdminPanels); `tabs.jsx` is now a thin barrel re-export so
  `Dashboard.jsx` imports are unchanged. (2) **ThreatIntel (was C50)** decomposed into subcomponents
  (ThreatProfileEditor, ThreatReportCard, ThreatDnsPanel, ThreatEmailDraft, ThreatTargetsTable).
  (3) **Backend `_gather_threat_signals` (was C45, 116 lines)** decomposed into extracted collectors
  (`_resolve_ip_sync`, `_dns_records_sync`, `_dnssec_enabled_sync`, `_sensitive_subs_sync`, `_open_ports_sync`,
  `_dns_email_findings`, `_http_header_breach_findings`, `_ssl_findings`, `_shodan_findings`) — behavior
  preserved (curl: example.com → risk 5.7, 6 findings, full DNS/SSL, AI summary). testing_agent iteration_12:
  all 13 dashboard tabs + 6 Governance sub-tabs render, 0 console/key errors. Also earlier this session:
  fixed array-index React keys (chat msgs → uuid; storefront risk chips → r.flag), removed unused `os` import
  in worker.py, moved hardcoded test creds → os.getenv() in the 3 test files.
  STILL DEFERRED (P2, high-risk on working monolith): server.py FILE-level route split into /routes (the module
  uses a startup-populated global `db` + worker.py mutates `server.db`); Storefront (C24) / Leads (C17) component
  extraction; fetch_osm / fetch_apify_reddit complexity; type-hint coverage.

- 2026-06-30 — **Outreach Template Library + Sandbox Testing + competitor doc — VERIFIED.**
  Verified the previous (untested) feature batch via testing_agent (iteration_10, frontend, 6/6 PASS):
  (1) Outreach tab (Governance > gov-tab-outreach) renders OutreachPanel without breaking the React tree.
  (2) Template dropdown (`outreach-template`, GET /api/outreach/templates) loads 4 pilot options — RE 5/10-lead
  ($200/$350) + B2B 5/10-lead ($200/$350), all "92+" — and selecting one populates subject/body.
  (3) Sandbox Text Testing (`outreach-sandbox-email`/`-send` → POST /api/outreach/send test_to) sent live to
  admin@nexus.io (sample: Diendei, LLC) — Resend delivery worked in preview.
  (4) "Model & comparison doc" link (`outreach-compare-link` → /launch/compare.html) served 200 with graph markup.
  (5) Pilot Leads regression intact. No bugs. NOTE: tabs.jsx ~1078 lines — split candidate (P2 tech debt).

- 2026-06-29 (4) — **Email enrichment + auto-send engine + Outreach admin tab.**
  (1) **Email enrichment** (`POST /api/outreach/enrich-emails` + `/enrich-status/{job}`): background job that
  fetches each lead's website (home + /contact + /about), extracts a domain-matched email (junk-filtered),
  saves it (`email_source:"web_enriched"`) and re-runs OSINT/HQ scoring. Ran on the 18 HQ real-estate leads
  without emails → **found 8** (Diendei, Klein & Heuchan, Ragsdale Residential, Bayside Waters, etc.).
  (2) **Auto-send engine**: `db.outreach_auto` config (`GET/PUT /api/outreach/auto`), `_auto_outreach_sweep`
  emails every HQ lead matching category that hasn't been sent (deduped via db.outreach_sends), wired to run
  after every scrape cycle (`_auto_outreach_sweep("post-scrape")`) + manual `POST /api/outreach/auto/run`.
  Enabled for real_estate with the pilot template → auto-sent to the 8 newly-enriched leads (0 failed).
  **Total real-estate HQ leads emailed: 12** (4 manual + 8 auto). (3) **Outreach admin tab** (Governance →
  Outreach, tabs.jsx OutreachPanel, testid gov-outreach): toggle auto-send, edit subject/body template,
  Enrich emails, Send now, Refresh, and send history. Sender: robert@mail.nexuscloud.sh (verified). AUTO-SEND
  IS CURRENTLY ON for real_estate — toggle off in the Outreach tab if undesired. PRODUCTION: redeploy + ensure
  SENDER_EMAIL=robert@mail.nexuscloud.sh in the deployed env.


- 2026-06-29 (3) — **HQ outreach campaign engine + first real-estate pilot send.** Added admin-only
  endpoints: `POST /api/outreach/preview` (list HQ recipients by score range / category / FL, minus
  already-sent), `POST /api/outreach/send` (test_to single-send mode + confirm-gated bulk; personalizes
  `{{company}}/{{city}}/{{category}}/{{first_name}}` and `[First Name]`; per-lead status → db.outreach_sends;
  skips already-sent; audit-logged), `GET /api/outreach/history`. **Resend domain finding**: mail.nexus.sh /
  nexus.sh / nexuscloud.sh are NOT verified in Resend, but **`mail.nexuscloud.sh` IS verified** — set
  `SENDER_EMAIL="robert@mail.nexuscloud.sh"` in backend/.env (was onboarding@resend.dev test mode).
  **Sent the user's real-estate pilot template** (uploaded "Hi [First Name].txt", signed Robert) to all 4 HQ
  real_estate leads that have emails (South Tampa Agent, Sea Glass Florida Properties, Eagle Premier Realty,
  Ruben Buys Houses) — campaign 6df82ec0, 4 sent / 0 failed. NOTE: only 4 of 22 HQ real-estate leads have
  email addresses (rest are OSM records with none). PRODUCTION: ensure deployed env also sets
  SENDER_EMAIL=robert@mail.nexuscloud.sh. Not yet automated (manual trigger); auto-send-on-discovery is a
  proposed follow-up.


- 2026-06-29 (2) — **Live AI chat + Pilot Leads admin tab.** (1) The public launch site's AI Chat
  demo (`POST /api/chat`) now calls the REAL NEXUS AI (Gemini 3 Flash via Emergent key / `deepseek_chat`)
  with a launch-site system prompt, returns `mode:"live"`, and falls back to keyword safe-mode on any LLM
  error; the endpoint is public and rate-limited (`RL_CHAT_PER_MIN=8`/min per IP). Launch `app.js` updated
  to show "Connected to live Nexus AI." and label replies "Nexus AI". (2) New **Pilot Leads** sub-tab in the
  admin Governance Console (`tabs.jsx` PilotLeadsPanel, testids gov-tab-pilot/gov-pilot-leads/pilot-refresh/
  pilot-export-csv) reading `GET /api/waitlist` (admin-only) — shows email/company/source/captured with
  Refresh + CSV export. testing_agent iteration_9: all 6 frontend flows PASS (live chat, login, Pilot Leads,
  waitlist round-trip, no regressions). PREVIEW only — REDEPLOY to push.


- 2026-06-29 — **Public launch site integrated** ("LeadGen Virtual Hub"): the user's static
  marketing site (index.html/styles.css/app.js/assets, built in Google AI Studio) is now served
  verbatim from `frontend/public/launch/` and rendered at **`/`** inside a full-viewport iframe
  (perfect CSS/JS isolation — their `.topbar`/`.tool-card`/`.badge` no longer clash with the NEXUS
  app styles). The functional React NEXUS console moved to **`/dashboard`** (also reachable via
  `#app`/`#dashboard`/`#login`/`#console`). App.js now hash/path-routes between `<Landing/>` (public)
  and `<AuthProvider><Gate/></AuthProvider>` (app); AuthContext/Login/Dashboard untouched (auth verified
  unchanged: SameSite=Lax httpOnly cookie + /auth/me OK). Landing CTAs ("Console Login", "Open the live
  console →") break out to `/dashboard` via target="_top". Added public (no-auth) FastAPI endpoints
  backing the landing: `POST /api/waitlist` (pilot capture → db.waitlist, `GET /api/waitlist` admin-only),
  `POST /api/enrich-score`, `POST /api/sale-listing`, `POST /api/chat` (safe-mode, no LLM cost) — ported
  from the launch site's demo server.py. Verified: /launch/* served 200, waitlist persists to Mongo,
  demos return scored payloads, both routes render. NOTE: the launch site's `dashboard.html` mockup is
  intentionally NOT used — the real React dashboard is the console. PREVIEW only — REDEPLOY to push.


- 2026-06-28 — **OSINT-wired live scraper → HQ-only FL B2B marketplace**: the 24/7 scrape cycle now
  runs every harvested entity through the OSINT verifier inline (free, no LLM) and only surfaces
  high-quality leads. (1) **Source pivot**: continuous scraper switched from Nominatim home-services to
  **Overpass** area queries over 6 high-value B2B sectors (financial_services, legal, insurance,
  real_estate, healthcare, b2b_tech — FinServ & Legal prioritised) × 5 counties (Hillsborough, Pinellas,
  Manatee, Pasco, Hernando). One area query per sector+county (`fetch_overpass_county` → `_overpass_generate`),
  SOURCES_VERSION=5. (2) **OSINT HQ filter inline**: `_process_business`/`_process_candidate` now compute
  `_osint_verify_sync` + `_data_confidence` and build the full storefront payload (cross_verification,
  risk_matrix, operational_value_tier, price_per_lead, purchase_status) with `ready_to_sell` gated at
  **confidence ≥ 65 & ≥2 nodes** (`_osint_fields`, STOREFRONT_MIN_CONFIDENCE=65). (3) **Stronger OSINT**:
  `_osint_verify_sync` now also MX-checks the *website* domain (a resolving company domain that can receive
  mail is a strong legitimacy signal — lifts website-having firms to HQ). (4) **HQ-only + FL-only storefront**:
  `/storefront/leads` now filters `ready_to_sell:true, purchase_status≠sold` AND Florida residency
  (state ∈ FL/Florida/empty) on both the lead list and the bundle/facet base. (5) **Cost-controlled AI**:
  OSINT-only in the cycle; `_bg_ai_enrich` runs in the background on *HQ-qualified leads only*. (6) **Florida
  bbox fix**: ambiguous county names (e.g. "Hillsborough County" exists in FL *and* NH) were pulling
  out-of-state firms — `_overpass_generate` now constrains to a Florida bbox [24.3,-87.7,31.1,-79.8] and
  retries across 3 Overpass mirrors. (7) **Startup re-score** (`_bg_reosint_all`) re-OSINTs all non-sold
  leads to the live HQ bar on boot. Verified: live cycle harvested 605 FL firms (FinServ/Legal/Insurance/
  Healthcare/RealEstate), 34 HQ; testing_agent 9/10 backend pass (FL-leak edge case then fixed + cleaned up
  6 legacy non-FL leads). deployment_agent: **PASS** (fixed .gitignore re-blocking .env). Frontend Generate
  modal now uses a 5-county FL dropdown, default sector financial_services. PREVIEW only — REDEPLOY to push.
- 2026-06-28 — **Real-time lead-generation progress toast**: background AI enrichment after a harvest
  now reports live progress. Backend: `db.generate_jobs` job tracking (job_id/total/done/status,
  TTL-cleaned); `_bg_ai_enrich(lead_ids, job_id)` increments `done` per lead and marks `complete`;
  `POST /storefront/generate-leads` returns `job_id`+`enrich_total`; new `GET /storefront/generate-status/{job_id}`
  (admin) for polling. Frontend: mounted sonner `<Toaster>` (bottom-right, dark) in App.js; GenerateModal
  polls every 2s and drives a loading→success toast ("Enriching {sector} · done/total" → "Enrichment
  complete · N leads"), refreshing the marketplace on completion. Self-tested: curl job 0→8→complete +
  UI toast 0/6→2/6→complete (4/4 automotive). PREVIEW only — REDEPLOY to push.
- 2026-06-28 — **Gov-Ready application layer (multi-tenancy, RBAC, audit, security, monitoring)**:
  Translated the user's "Gov-Ready Azure Architecture (do it ur way)" guide into application-level code
  (the Emergent platform already provides the K8s/VNET/WAF/CI-CD/health-probe infra). New `backend/governance.py`:
  (1) **Granular RBAC** hierarchy user<analyst<tenant_admin<admin<owner (`require_min_role`); `require_admin`
  now accepts admin+owner. (2) **Multi-tenancy**: `tenant_id`/`tenant_name` on users; new registrations
  provision their own tenant (registrant = tenant_admin); seeded admin in `default` tenant; legacy users
  backfilled on startup. Row-level isolation (`tenant_scope`) on OSINT reports + people-intel history
  (platform admins bypass); storefront marketplace stays cross-tenant. (3) **Brute-force lockout** (Mongo
  login_attempts, 5/15min, TTL-cleaned, HTTP 429). (4) **Audit log** (db.audit_logs) on login/register/
  role-change/apikey/threat-scan/rfp/purchase/generate + admin viewer `GET /api/admin/audit`. (5) **Rate
  limiting** on generate-leads (5/min) + threat-scan (10/min). (6) **Health/monitoring**: `/api/ready`
  (DB readiness probe) + `/api/admin/monitoring` ops snapshot. New endpoints: /api/governance/me,
  /api/governance/tenant/members, /api/admin/tenants, /api/admin/audit, /api/admin/monitoring, /api/ready.
  Frontend: Admin tab → **Governance Console** (Operators w/ granular roles + tenant column / Tenants /
  Audit Trail / Monitoring auto-refresh). Sidebar shows role · tenant. deployment_agent: PASS (no blockers).
  Smoke-tested via curl + UI. server.py refactor into /routes still deferred (P1 tech debt).

- 2026-06-23 — **On-demand lead generator + full-catalog storefront**: (1) Storefront now lists EVERY
  non-sold lead (relaxed query/purchase from `ready_to_sell+available` to `purchase_status != sold`);
  total jumped to 160+ across all sector bundles. (2) New `POST /api/storefront/generate-leads` (admin) +
  `GET /api/storefront/sectors`: harvests real businesses for a sector+county from OSM (Overpass area
  query, 10 mapped sectors: real_estate, legal, healthcare, dental, construction, automotive, restaurant,
  financial, veterinary, fitness), OSINT-verifies, stores as available, and runs deep AI enrichment in a
  background task. Frontend: **Generate Leads** modal (sector/county/limit/ai_enrich) in Storefront header
  (admin-only). Verified: dental Pinellas harvested 38; purchase + double-sell guard intact.
- 2026-06-23 — **AI provider switch (Emergent Universal Key)**: HF Inference account hit 402 (out of
  credits), blocking all AI (enrichment, scraper scoring, NEXUS AI chat). Routed the central
  `deepseek_chat` helper through the Emergent Universal Key via `emergentintegrations` LlmChat
  (default `gemini/gemini-3-flash-preview`; env AI_PROVIDER/EMERGENT_AI_PROVIDER/EMERGENT_AI_MODEL),
  HF router as fallback. Restores AI app-wide. ⚠️ Production needs these env vars on redeploy.
- 2026-06-23 — **Pinellas real estate lead batch (real data)**: 52 real estate firms in Pinellas County
  from OpenStreetMap (Overpass + Nominatim, keyless), OSINT-verified + full Gemini 3 Flash analyst
  enrichment → 10 verified & live in Intel Marketplace (category `real_estate`). Generators:
  `backend/seed_realestate.py`, `backend/enrich_realestate.py`. OSM caps ~52 for Pinellas; reaching 200
  needs broader geography or a paid real-estate data API. Preview DB only.
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
