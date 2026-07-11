# nexuscloud.ai Production Deploy Pack

This folder contains deploy templates for a FastAPI backend behind host-level NGINX on Ubuntu 22.04.

## Files

- `Dockerfile`: production Python/FastAPI image.
- `docker-compose.yml`: backend service plus optional worker profile.
- `.env.example`: production environment variable template.
- `requirements.txt`: minimal FastAPI runtime dependencies. Replace or merge with the app's real locked requirements.
- `nginx/nexuscloud.ai.bootstrap.conf`: temporary HTTP config used before certificates exist.
- `nginx/nexuscloud.ai.conf`: final host NGINX config for `nexuscloud.ai`, `www.nexuscloud.ai`, and `api.nexuscloud.ai`.
- `scripts/deploy.sh`: pull, build, restart, health-check, and reload NGINX.

## Server Setup

```bash
sudo mkdir -p /opt/nexuscloud
sudo chown -R "$USER:$USER" /opt/nexuscloud
git clone <YOUR_REPO_URL> /opt/nexuscloud
cd /opt/nexuscloud
cp .env.example .env
chmod 600 .env
chmod +x scripts/deploy.sh
```

Edit `.env` before starting containers.

## NGINX And SSL Setup

```bash
sudo cp nginx/nexuscloud.ai.bootstrap.conf /etc/nginx/sites-available/nexuscloud.ai
sudo ln -sf /etc/nginx/sites-available/nexuscloud.ai /etc/nginx/sites-enabled/nexuscloud.ai
sudo nginx -t
sudo systemctl reload nginx
```

Issue certificates after DNS points to the server:

```bash
sudo certbot --nginx -d nexuscloud.ai -d www.nexuscloud.ai -d api.nexuscloud.ai
sudo certbot renew --dry-run
```

Then install the final HTTPS config:

```bash
sudo cp nginx/nexuscloud.ai.conf /etc/nginx/sites-available/nexuscloud.ai
sudo nginx -t
sudo systemctl reload nginx
```

## Deploy

Backend only:

```bash
APP_DIR=/opt/nexuscloud ./scripts/deploy.sh
```

Backend plus worker:

```bash
APP_DIR=/opt/nexuscloud COMPOSE_PROFILES=worker ./scripts/deploy.sh
```

## Validation

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS https://api.nexuscloud.ai/health
docker compose logs -f backend
docker compose --profile worker logs -f worker
```

## Notes

- The real backend source is not currently present in this workspace. Set `APP_MODULE` in `.env` to the actual ASGI app path, for example `src.main:app`.
- The frontend root in NGINX is `/var/www/nexuscloud.ai`. Copy a built frontend or the static `launch_site/` contents there.
- `docker compose down` is intentionally not used by the deploy script because it causes avoidable downtime.
