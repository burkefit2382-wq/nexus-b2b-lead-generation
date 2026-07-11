# Deployment Status

Last updated: 2026-07-04

## Nexus Devvit App

Status: Deployed to Devvit playtest on latest uploaded version.

Evidence from `npm run deploy` and `devvit publish --public`:

- App name: `nexus-saas`
- Build: passed
- Upload: passed
- WebView assets uploaded: 9
- Playtest subreddit created/used: https://www.reddit.com/r/nexus_saas_dev
- Playtest installed version: `0.0.4`
- Latest uploaded version: `0.0.4`
- Previous source upload info exists for `source/nexus-saas/0.0.3.zip`
- Developer app page: https://developers.reddit.com/apps/nexus-saas

Notes:

- `npm run launch` initially hit an interactive source-upload prompt in the non-interactive terminal.
- `devvit publish --public` was retried with the source-upload prompt answered, and the command exited successfully.
- Devvit CLI output confirms version `0.0.4` is uploaded and installed to the playtest subreddit.
- The Devvit dashboard should be checked for final public review/approval status.
- The local git repository shows the app files as untracked/new, so commit/push is still needed if source control handoff matters.

## Launch/Waitlist Site

Status: Running publicly through Cloudflare Tunnel and cloud-host-ready.

- Public URL: https://nexuscloud.sh/
- Public dashboard: https://nexuscloud.sh/dashboard
- Render URL: https://nexus-b2b-lead-generation.onrender.com/
- Render dashboard: https://nexus-b2b-lead-generation.onrender.com/dashboard
- Render service: `nexus-b2b-lead-generation`
- Render service ID: `srv-d91akdb7uimc73a2b8g0`
- Tracking API URL: https://nexus-tracking-api.onrender.com/
- Tracking API service: `nexus-tracking-api`
- Tracking API service ID: `srv-d957p7favr4c73a1rtt0`
- Local URL: http://127.0.0.1:4173/
- Last local/public verification: 2026-06-29
- Health check: http://127.0.0.1:4173/healthz
- Local waitlist API: http://127.0.0.1:4173/api/waitlist
- Local Nexus AI chat API: http://127.0.0.1:4173/api/chat
- Local enrichment/scoring API: http://127.0.0.1:4173/api/enrich-score
- Local lead sale listing API: http://127.0.0.1:4173/api/sale-listing
- Local checkout API: http://127.0.0.1:4173/api/checkout
- Local Stripe webhook API: http://127.0.0.1:4173/api/stripe-webhook
- Waitlist storage: `data/waitlist_requests.jsonl`
- Resend email: wired but skipped until `RESEND_API_KEY`, `RESEND_FROM`, and `WAITLIST_NOTIFY_TO` or `RESEND_TO` are configured.
- Nexus Llama 3 chat: safe fallback mode works; set `LLAMA_CHAT_ENDPOINT` and `LLAMA_CHAT_MODEL` for live Llama/Ollama-compatible chat.
- AI scoring/enrichment: local demo pipeline works and returns summary, score, confidence, reasons, next action, and storefront-safe fields.
- Lead sale page: visible default AI-enriched listing is present and `/api/sale-listing` can regenerate it from scraper output.
- Revenue storefront: HQ Florida lead packages are live with 137 available leads and pricing tiers of 10 for $49, 25 for $99, and 50 for $149.
- Pricing page: Starter, Pro, Elite, and DFY plans are visible at `/#pricing`.
- Marketplace page: lead bundles, OSINT reports, and AI intelligence reports are visible at `/#marketplace`.
- Stripe checkout: `/api/checkout` creates live Stripe Checkout sessions for SaaS plans, lead bundles, OSINT reports, and intelligence reports.
- DFY checkout includes both `price_dfy_setup_1500` and `price_dfy_997`.
- Stripe webhook: `/api/stripe-webhook` verifies Stripe signatures, processes `checkout.session.completed`, records fulfillment events, and sends buyer/admin Resend emails when Resend is configured.
- Fulfillment log: `data/fulfillment_events.jsonl`
- Fulfillment dashboard: `/dashboard#fulfillment` shows paid-order counts, masked buyer emails, logged revenue, and delivery status.
- Buyer package request API: `/api/lead-package-request`
- Static routing verified: `/`, `/styles.css`, `/app.js`, `/dashboard`, `/dashboard/`, unknown routes, `?page=dashboard`, and `#dashboard`.
- Render deploy verified: GitHub commit `68bbd17dba1535090b7b198c667a895b3ad9672c`; start command `python server.py`; health check `/healthz`.
- Latest smoke test: Render public page, `/lead-control-center`, `/static/lead-control-center.html`, `/api/health`, `/api/scraper-queue`, `/api/lead-stats`, `/api/event`, OSINT quality fields, control-center queue/ingestion metrics, revenue status, fulfillment status, pricing, marketplace markers, tracking FastAPI service definition, Stripe configuration status, and Resend configuration status were verified on 2026-07-05.
- Render config: `launch_site/render.yaml`
- Railway config: `launch_site/railway.json`

## Deploy Artifacts

- `deploy_artifacts/leadgen-virtual-hub-launch-site.zip`
- `deploy_artifacts/nexus-saas-devvit-build.zip`
- `deploy_artifacts/github-enterprise-repo.zip`

## Public Web Deployment Remaining

To put the launch/waitlist site on the public internet, choose one:

- Static/Python-capable host such as Render, Railway, Fly, or a VPS for `launch_site/server.py`.
- Static-only host such as Netlify/Vercel/Cloudflare Pages, plus a separate serverless `/api/waitlist` function.

Still required:

- Public hosting provider and credentials.
- Domain/subdomain.
- Resend verified sending domain.
- Backend secrets configured in the host.
- Resend secrets configured for lead package delivery: `RESEND_API_KEY`, `RESEND_FROM`, and `WAITLIST_NOTIFY_TO` or `RESEND_TO`.
- Render `STRIPE_SECRET_KEY` must be set with a real live Stripe key before checkout opens payment sessions.
- Production waitlist storage, CRM, database, or storefront sync.

Fastest next step:

- Upload `deploy_artifacts/leadgen-virtual-hub-launch-site.zip` to Render or Railway as a Python web service.
- Start command: `python server.py`
- Health check path: `/healthz`
- Set `LAUNCH_HOST=0.0.0.0`

## GitHub Enterprise Readiness

Status: Repository governance files created locally.

- CI workflows: `.github/workflows/ci.yml`
- Security workflows: `.github/workflows/security.yml`
- Artifact packaging workflow: `.github/workflows/package.yml`
- Manual production deploy workflow: `.github/workflows/deploy.yml`
- Dependabot: `.github/dependabot.yml`
- CODEOWNERS: `.github/CODEOWNERS`
- Security policy: `SECURITY.md`
- Contribution guide: `CONTRIBUTING.md`
- GitHub setup checklist: `GITHUB_ENTERPRISE_SETUP.md`
- Local verification: `python -m py_compile launch_site/server.py`, `npm run type-check`, and `npm run build` passed.

Remaining:

- Create or connect a GitHub/GitHub Enterprise remote.
- Push the repository.
- Enable branch protection, secret scanning, Dependabot alerts, and required checks.
- Set `RENDER_DEPLOY_HOOK` or equivalent host deploy credentials for public web deploys.
