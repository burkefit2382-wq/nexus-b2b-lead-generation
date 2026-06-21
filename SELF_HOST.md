# NEXUS — Self-Host on Your Own VPS

This is the **correct** deployment for the real NEXUS stack:
**React + FastAPI (`server:app`, port 8001) + MongoDB + APScheduler worker**.
(Do NOT use generic Celery/Redis/Postgres templates — NEXUS does not use them.)

Stack (see `docker-compose.yml`):
- `mongo`   — database (internal only)
- `api`     — FastAPI, `RUN_SCHEDULER=false` (no in-process scheduler)
- `worker`  — runs `worker.py`, `RUN_SCHEDULER=true` (owns the 24/7 scrape + Reddit jobs)
- `web`     — NGINX: serves the React build, proxies `/api` → `api:8001`, terminates TLS

## 1. One-time server setup (Ubuntu)
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin certbot nginx
git clone https://github.com/YOU/nexus.git /root/nexus
cd /root/nexus
cp backend/.env.production.example backend/.env.production
# edit backend/.env.production — fill JWT_SECRET, HF_TOKEN, STRIPE_API_KEY,
# APIFY_TOKEN, SHODAN_API_KEY, RESEND_API_KEY, ADMIN_* etc.
```

## 2. DNS (Cloudflare)
Point an A record for `nexuscloud.io` (and `www`) to your server's public IP.
For the SSL issuance below, set those A records to **DNS only (grey cloud)** during issuance.

## 3. TLS certificate (Let's Encrypt)
```bash
sudo certbot certonly --standalone -d nexuscloud.io -d www.nexuscloud.io
# certs land in /etc/letsencrypt/live/nexuscloud.io/ (mounted read-only into the web container)
```

## 4. Launch
```bash
cd /root/nexus
docker compose up -d --build
docker compose logs -f api worker   # verify boot
```
App: https://nexuscloud.io  ·  API: https://nexuscloud.io/api/...

## 5. Auto-start on reboot (systemd)
```bash
sudo cp deploy/nexus.service /etc/systemd/system/nexus.service
sudo systemctl daemon-reload
sudo systemctl enable --now nexus
```

## 6. CI/CD (optional, GitHub Actions — `.github/workflows/deploy.yml`)
Add repo secrets: `SERVER_IP`, `SERVER_USER` (e.g. root), `SERVER_SSH_KEY`.
Every push to `main` SSHes in, `git pull`, rebuilds, and restarts the stack.

## Notes
- Keep the `api` container at **1 uvicorn worker** (the scheduler lives in the separate `worker` container; scale `api` horizontally if needed, never via more uvicorn workers).
- Cert renewal: `certbot renew` on a cron, then `docker compose restart web`.
- `REACT_APP_BACKEND_URL` is baked into the frontend at build time (compose build arg = `https://nexuscloud.io`). Change it there if your domain differs.
