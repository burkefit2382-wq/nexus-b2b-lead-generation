# NEXUS API Reference

Base URL: `https://<your-host>` &nbsp;·&nbsp; All routes are prefixed with `/api`.

Authentication uses JWT Bearer tokens. After login, send the access token on every
protected request:

```http
Authorization: Bearer <access_token>
```

Programmatic/server-to-server access can alternatively use a generated API key
(see **API Keys** below).

---

## Conventions

| Aspect | Value |
| --- | --- |
| Content type | `application/json` |
| Auth header | `Authorization: Bearer <token>` |
| Timestamps | ISO 8601, UTC |
| Errors | `{ "detail": "<message>" }` with appropriate HTTP status |
| Roles | `admin`, `user` (RBAC enforced on admin routes) |

---

## Health

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/health` | – | Liveness probe. Returns service status. |

---

## Authentication

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | – | Create a new account. |
| POST | `/api/auth/login` | – | Authenticate and receive access/refresh tokens. |
| POST | `/api/auth/logout` | Bearer | Invalidate the current session. |
| POST | `/api/auth/refresh` | Bearer | Exchange a refresh token for a new access token. |
| GET | `/api/auth/me` | Bearer | Return the current user profile and credit balance. |

**Login request**
```json
{ "email": "admin@nexus.io", "password": "********" }
```
**Login response**
```json
{ "access_token": "ey...", "refresh_token": "ey...", "token_type": "bearer" }
```

---

## API Keys

Generate keys for headless/server access. The full secret is shown **once** on creation.

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/keys` | Bearer | Create a new API key. Returns the raw key once. |
| GET | `/api/keys` | Bearer | List your API keys (prefix + metadata only). |
| DELETE | `/api/keys/{key_id}` | Bearer | Revoke an API key. |

---

## Admin (RBAC: `admin`)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/admin/users` | Admin | List all users. |
| PATCH | `/api/admin/users/{user_id}/role` | Admin | Change a user's role. |

---

## Leads

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/leads` | Bearer | List leads (filterable by source, score, tags). |
| GET | `/api/leads/stats` | Bearer | Aggregate lead metrics. |
| POST | `/api/leads` | Bearer | Create a lead manually. |
| POST | `/api/leads/{lead_id}/unlock` | Bearer | Unlock a lead using credits. |
| POST | `/api/leads/{lead_id}/buy` | Bearer | Pay-per-lead purchase (price tiered by score). |
| PATCH | `/api/leads/{lead_id}/sell` | Bearer | Mark a lead as sold. |
| DELETE | `/api/leads/{lead_id}` | Bearer | Delete a lead. |
| GET | `/api/leads/export/csv` | Bearer | Export leads as CSV. |

---

## AI Enrichment (Hugging Face)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/enrichment/enrich` | Bearer | Enrich a record with AI-generated attributes. |
| GET | `/api/enrichment/model-status` | Bearer | Inference model availability. |
| POST | `/api/enrichment/chat` | Bearer | Conversational enrichment endpoint. |
| GET | `/api/enrich/pricing` | Bearer | Credit pricing per enrichment type. |
| POST | `/api/enrich/business` | Bearer | Enrich a business entity. |
| POST | `/api/enrich/person` | Bearer | Enrich a person entity. |
| POST | `/api/enrich/property` | Bearer | Enrich a property entity. |
| POST | `/api/enrich/osint` | Bearer | Run an OSINT-driven enrichment. |
| POST | `/api/enrich/lead` | Bearer | Enrich a full lead record. |
| GET | `/api/enrich/history` | Bearer | Enrichment history. |

---

## OSINT

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/osint/ip` | Bearer | IP intelligence lookup. |
| POST | `/api/osint/dns` | Bearer | DNS records (A, NS, MX, SOA, DNSSEC). |
| POST | `/api/osint/whois` | Bearer | WHOIS / registration data. |
| POST | `/api/osint/phone` | Bearer | Phone number intelligence. |
| POST | `/api/osint/social` | Bearer | Social profile discovery. |
| POST | `/api/osint/geolocate` | Bearer | Geolocation lookup. |
| POST | `/api/osint/breach` | Bearer | Data breach check. |
| POST | `/api/osint/subdomains` | Bearer | Subdomain enumeration. |
| POST | `/api/osint/portscan` | Bearer | Port scan. |
| POST | `/api/osint/metadata` | Bearer | File/URL metadata extraction. |
| POST | `/api/osint/shodan` | Bearer | Shodan host lookup (open ports/CVEs). |
| POST | `/api/osint/dork` | Bearer | Search-engine dorking helper. |
| GET | `/api/osint/reports` | Bearer | List saved OSINT reports. |

---

## Scrapers & Intel Sources

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/scraper/status` | Bearer | Current scraper run status. |
| GET | `/api/scraper/config` | Bearer | Read scraper configuration. |
| PUT | `/api/scraper/config` | Bearer | Update scraper config (sources, budget). |
| POST | `/api/scraper/trigger` | Bearer | Manually trigger a scrape run. |
| GET | `/api/scraper/feed` | Bearer | Latest scraped items feed. |
| GET | `/api/intel/sources` | Bearer | Aggregate health of OSM, Reddit, Shodan, DNS, Email. |

---

## People Intel

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/people-intel/scan` | Bearer | Scan a person across sources. |
| GET | `/api/people-intel/history` | Bearer | Past people-intel scans. |

---

## Threat Intel & Outreach

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/threat/scan` | Bearer | Scan a domain (DNS/DNSSEC/SSL/Shodan) and score risk. |
| GET | `/api/threat/reports` | Bearer | List threat reports. |
| GET | `/api/threat/outreach-profile` | Bearer | Read the outreach sender profile. |
| PUT | `/api/threat/outreach-profile` | Bearer | Update the outreach sender profile. |
| POST | `/api/threat/reports/{report_id}/send-email` | Bearer | Send the AI-drafted pitch via Resend. |

---

## Payments (Stripe)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/payments/packages` | – | List available credit packages. |
| POST | `/api/payments/checkout` | Bearer | Create a Stripe Checkout session (credits or pay-per-lead). |
| GET | `/api/payments/status/{session_id}` | Bearer | Poll a checkout session's payment status. |
| POST | `/api/webhook/stripe` | Stripe sig | Stripe webhook receiver (server-to-server). |

> The webhook endpoint verifies the Stripe signature; do not call it directly.

---

## Error Responses

| Status | Meaning |
| --- | --- |
| 400 | Validation / bad request |
| 401 | Missing or invalid token |
| 402 | Insufficient credits |
| 403 | Forbidden (role/permission) |
| 404 | Resource not found |
| 429 | Rate / budget limit reached |
| 500 | Internal server error |

All errors return:
```json
{ "detail": "Human-readable message" }
```
