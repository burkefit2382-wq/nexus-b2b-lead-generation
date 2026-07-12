# Observability — Sentry Error Tracking

This document explains the Sentry integration added to the NEXUS B2B Lead Generation platform, covering backend (FastAPI / launch server) and frontend (Vite + TypeScript).

## Overview

Sentry is **fully optional**.  The application starts and runs normally in local development and CI when `SENTRY_DSN` is not set — no configuration required, no errors thrown.  Sentry only activates when a valid DSN is supplied.

---

## 1. Getting a Sentry DSN

1. Sign in to [sentry.io](https://sentry.io) (or create a free account).
2. Create a **New Project** — choose **Python** for the backend and **JavaScript** (Browser) for the frontend; or use a single project with multiple platforms if you prefer.
3. Go to **Project Settings → Client Keys (DSN)**.
4. Copy the DSN — it looks like `https://<key>@o<org>.ingest.sentry.io/<project-id>`.

---

## 2. Environment Variables

### Backend

| Variable | Required | Default | Description |
|---|---|---|---|
| `SENTRY_DSN` | No | *(empty)* | Sentry DSN — Sentry is disabled when absent |
| `SENTRY_ENVIRONMENT` | No | `production` | Environment tag (`development`, `staging`, `production`) |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Performance trace sample rate (0.0 – 1.0) |
| `SENTRY_PROFILES_SAMPLE_RATE` | No | `0.0` | CPU profiling sample rate (requires SDK ≥ 1.18) |
| `SENTRY_RELEASE` | No | *(empty)* | Release/version string (e.g. git SHA or semver tag) |

Add these to `backend/.env` locally, or set them in the Render dashboard (they are already declared in `backend/render.yaml` as `sync: false`).

### Frontend

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_SENTRY_DSN` | No | *(empty)* | Sentry DSN for the browser client |
| `VITE_SENTRY_ENVIRONMENT` | No | `production` | Environment tag |
| `VITE_SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Performance trace sample rate |

Add these to `frontend/.env` locally, or to your Cloudflare Pages / Render static site environment variables.

---

## 3. What Is Captured

### Backend — automatic (via FastAPI/Starlette integration)
- Unhandled exceptions in any FastAPI route.
- Slow endpoint performance traces (when `traces_sample_rate > 0`).

### Backend — explicit capture points
| Location | Integration tag | Trigger |
|---|---|---|
| `backend/app/api/membership.py` | `stripe` | Stripe Checkout session creation failure |
| `backend/app/api/membership.py` | `stripe` | Stripe webhook signature verification failure |
| `backend/app/main.py` | `hubspot` | HubSpot contact upsert failure |
| `backend/server.py` | `resend` | Waitlist notification email send failure |
| `backend/server.py` | `resend` | Lead package notification email send failure |

Each explicit capture includes an `integration` tag so you can filter in Sentry by `integration:stripe`, `integration:hubspot`, or `integration:resend`.

### Frontend — automatic
- Unhandled JavaScript errors (window-level).
- Unhandled promise rejections.
- Network request spans (when `tracesSampleRate > 0`).

---

## 4. What Is Scrubbed (Never Sent)

The `before_send` hook in `backend/app/core/sentry.py` redacts any event field whose **key** contains one of:

```
secret, password, token, api_key, apikey, stripe, hubspot, resend, jwt,
authorization, cookie, card, cvv, ssn, r2_access, r2_secret, database_url
```

Additionally:
- Raw HTTP request bodies are **always** replaced with `[Filtered]` (prevents card/PII data leakage).
- `send_default_pii=False` is set globally — Sentry does not automatically collect IP addresses or user-agent strings.

---

## 5. Testing That Error Capture Works

### Safe backend test event

With the server running and `SENTRY_DSN` set, open a Python shell and run:

```python
import sentry_sdk
sentry_sdk.capture_message("Nexus Sentry test event", level="info")
```

Then check the Sentry dashboard — the event should appear within a few seconds.

Alternatively, trigger a deliberate 500 by hitting a route that will raise (e.g., passing a malformed body to `/api/event`):

```bash
curl -X POST https://<your-api-host>/api/event \
  -H "Content-Type: application/json" \
  -d '{"event_name": "INVALID_EVENT_THAT_DOES_NOT_EXIST"}'
```

The 400 validation error is caught and returned to the client normally — Sentry will not capture it (expected: only truly unhandled 500s are captured automatically).  Use the Python snippet above to force a test capture.

### Frontend test event

Open the browser console on your deployed frontend and run:

```js
import('@sentry/browser').then(Sentry => Sentry.captureMessage('Frontend Sentry test'))
```

Or simply trigger an unhandled rejection:

```js
Promise.reject(new Error('Sentry frontend test error'))
```

---

## 6. Alerting & Notification Setup

In the Sentry dashboard:

1. Go to **Alerts → Create Alert Rule**.
2. Recommended rules for this project:
   - **New issue** detected → notify via email and/or Slack.
   - **Regression** (resolved issue re-appears) → Slack notification.
   - **High volume** (> 10 events in 5 minutes for the same issue) → PagerDuty or Slack.

### Slack integration

1. Go to **Settings → Integrations → Slack** and connect your workspace.
2. In your Alert Rule, add a **Slack** action and select the `#alerts` channel (or whichever channel you use for ops).

### Email alerts

Sentry sends email digests to all project members by default.  Adjust frequency under **User Settings → Notifications**.

---

## 7. Local Development

No Sentry configuration is needed locally.  Leave `SENTRY_DSN` unset (or empty) and the SDK is never initialised — zero performance overhead, zero external calls.

If you want to test Sentry locally, set `SENTRY_DSN` and `SENTRY_ENVIRONMENT=development` in `backend/.env` (or `frontend/.env`) before starting the server.

---

## 8. References

- [Sentry Python SDK docs](https://docs.sentry.io/platforms/python/)
- [Sentry FastAPI integration](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- [Sentry Browser SDK docs](https://docs.sentry.io/platforms/javascript/)
- Source: `backend/app/core/sentry.py` — init, scrubbing hook, integration helper
