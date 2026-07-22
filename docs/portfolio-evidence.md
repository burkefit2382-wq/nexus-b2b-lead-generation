# NEXUS Portfolio Evidence

Last updated: July 16, 2026

This page keeps portfolio-facing proof in one place so the repository can show more than source code. Keep each result current, timestamped, and tied to a reproducible command, deployment run, screenshot, or demo recording.

## Demo Assets

| Asset | Status | Location |
|---|---|---|
| Production storefront | Live | <https://nexuscloud.sh/> |
| Command center dashboard | Live | <https://nexuscloud.sh/dashboard> |
| Interactive workflow demo | Live | <https://nexuscloud.sh/workflow-demo> |
| Dashboard screenshot | Added | `backend/assets/dashboard-preview.png` |
| Product walkthrough video | Needed | Record a 60-90 second walkthrough and attach it to the release/README |

## Suggested Walkthrough Script

1. Open the storefront and explain the lead product being sold.
2. Show the command center dashboard and the operational metrics it tracks.
3. Walk through the workflow demo: lead capture, enrichment, scoring, and fulfillment.
4. Show the backend health endpoint and GitHub Actions deployment history.
5. Close with the validation snapshot: tests, coverage, build time, and bundle size.

## Validation Snapshot

Commands run locally on July 16, 2026:

```bash
PYTHONPATH=. python -m pytest backend/tests
PYTHONPATH=. python -m coverage run --source=backend/app,backend/workers -m pytest backend/tests
python -m coverage report -m
npm --prefix frontend install
npm --prefix frontend run build
```

Results:

| Check | Result |
|---|---|
| Backend tests | 27 passed, 1 warning in 7.23s |
| Focused app/worker coverage | 55% |
| Whole backend coverage | 41% baseline including legacy `backend/server.py` |
| Frontend dependency audit | 0 vulnerabilities |
| Frontend build | Vite build completed in 812ms |
| Frontend bundle | `index.html` 0.41 kB, CSS 1.19 kB, JS 3.60 kB before gzip |

## Coverage Follow-Up

The current coverage baseline is useful but not yet portfolio-grade. The next coverage milestone should prioritize:

- `backend/app/api/membership.py`
- `backend/app/services/stripe_service.py`
- `backend/app/services/hubspot.py`
- `backend/workers/tampa_bay_lead_worker.py`
- migration of legacy `backend/server.py` behavior into tested service modules

## Release Evidence Checklist

Before the next public release, attach:

- Demo video link
- Dashboard screenshot
- Checkout screenshot or GIF
- GitHub Actions run link
- Test and coverage report
- Frontend build/bundle-size output
- Known limitations and next milestone
