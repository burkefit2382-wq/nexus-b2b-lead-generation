# Nexus LeadGen Command Center

Nexus LeadGen Command Center is a hybrid SaaS launch workspace for lead generation, 24/7 scraper operations, AI enrichment, lead scoring, storefront-safe lead sale listings, onsite tools, Pi Suite edge-node planning, and Nexus Llama 3 command assistance.

## Current Deployments

- Local command center: http://127.0.0.1:4173/
- Health check: http://127.0.0.1:4173/healthz
- Devvit app page: https://developers.reddit.com/apps/nexus-saas
- Devvit playtest subreddit: https://www.reddit.com/r/nexus_saas_dev

See `DEPLOYMENT_STATUS.md` for the latest verified state.

## Main Components

| Path | Purpose |
| --- | --- |
| `launch_site/` | Python-backed launch/waitlist/command-center site |
| `nexus-saas/` | Reddit Devvit app |
| `product/` | Product specs for scrapers, enrichment, storefront listings, Pi Suite, and Nexus AI |
| `policies/` | Draft security/compliance policies |
| `trackers/` | Risk, evidence, defect, policy, and go/no-go trackers |
| `deploy_artifacts/` | Generated zip packages for deployment handoff |

## Local Run

```powershell
cd launch_site
python -m pip install -r requirements.txt
python server.py
```

Open:

```text
http://127.0.0.1:4173/
```

## Devvit App

```powershell
cd nexus-saas
npm ci
npm run type-check
npm run build
npm run deploy
```

## Production Notes

- Keep `RESEND_API_KEY`, `RESEND_FROM`, `WAITLIST_NOTIFY_TO`, `LLAMA_CHAT_ENDPOINT`, and any storefront/API secrets in hosting secrets only.
- Do not commit local waitlist data from `data/`.
- Public launch requires reviewed terms, privacy policy, security evidence, and buyer workflow approval.

