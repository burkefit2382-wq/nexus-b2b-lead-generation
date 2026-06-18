# NEXUS — Self-Hosted Deployment (DigitalOcean + Docker + NGINX/TLS)

This deploys the **real** NEXUS app: FastAPI backend (`backend/server.py`) + MongoDB + the
React frontend (served as static files by NGINX, with `/api` reverse-proxied to the backend).

> Easiest alternative: the **Deploy** button inside Emergent gives you a managed URL with
> zero server admin. Use this guide only if you want to self-host on your own domain.

## Architecture
```
Internet ──443──> nexus_web (NGINX: React static + TLS + proxy /api)
                       │ /api/*  ──> nexus_api (uvicorn server:app, 1 worker, scheduler)
                                          └──> nexus_mongo (MongoDB, internal only)
```

## Files
- `Dockerfile.backend` — backend image (installs `emergentintegrations` from its custom index)
- `frontend/Dockerfile` — multi-stage: `yarn build` → NGINX serving static + `/api` proxy
- `frontend/nginx.conf` — TLS + SPA fallback + `/api` proxy (keeps the `/api` prefix!)
- `docker-compose.yml` — mongo + api + web
- `backend/.env.production.example` — copy to `backend/.env.production` and fill in

## ⚠️ Critical notes
1. **One backend worker only.** The 24/7 scraper uses an in-process scheduler; running
   multiple workers would scrape/charge multiple times. To scale the API later, move the
   scheduler into a dedicated worker container with `SCRAPER_ENABLED=false` on the API.
2. **Same-origin frontend.** `REACT_APP_BACKEND_URL=https://nexuscloud.ai` (no separate api
   subdomain) so the JWT httpOnly cookies work without cross-site issues. `/api` is proxied.
3. **`emergentintegrations`** (Stripe) needs the extra pip index — already wired in the
   backend Dockerfile. If you prefer no custom index, swap the Stripe calls for the official
   `stripe` SDK.
4. For stricter cookie security in prod, set the auth cookies to `Secure` (HTTPS only).

## Steps (Ubuntu 22.04 droplet, 2GB+ RAM)

```bash
# 1) Install Docker + compose + certbot
sudo apt update
sudo apt install -y docker.io docker-compose certbot
sudo mkdir -p /var/www/certbot

# 2) Get the code
cd /opt && sudo git clone <your-repo-url> nexus && cd nexus

# 3) Configure secrets
cp backend/.env.production.example backend/.env.production
nano backend/.env.production        # set JWT_SECRET, ADMIN_*, HF_TOKEN, STRIPE_API_KEY ...

# 4) DNS:  A  nexuscloud.ai -> <droplet IP>,   A  www -> <droplet IP>

# 5) Issue TLS cert (standalone; nginx not running yet)
sudo certbot certonly --standalone -d nexuscloud.ai -d www.nexuscloud.ai

# 6) Launch
sudo docker-compose up -d --build
```

Your SaaS is live at **https://nexuscloud.ai** (admin = the ADMIN_EMAIL/PASSWORD you set).

## Update later
```bash
./redeploy.sh
```

## Cert auto-renew (cron)
```bash
# renew + reload nginx container monthly
0 3 1 * * certbot renew --quiet && docker exec nexus_web nginx -s reload
```

## Health checks
```bash
curl -s https://nexuscloud.ai/api/health         # {"status":"online",...}
docker-compose logs -f api                        # backend logs (scheduler, seeds)
```

## Backups (MongoDB volume)
```bash
docker exec nexus_mongo mongodump --archive=/data/db/backup.gz --gzip
docker cp nexus_mongo:/data/db/backup.gz ./nexus-backup-$(date +%F).gz
```
