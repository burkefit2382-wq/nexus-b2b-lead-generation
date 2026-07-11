#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/nexuscloud}"
COMPOSE_PROFILES="${COMPOSE_PROFILES:-}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  echo "Missing $APP_DIR/.env. Copy .env.example to .env and fill production values." >&2
  exit 1
fi

git pull --ff-only

if [ -n "$COMPOSE_PROFILES" ]; then
  docker compose --profile "$COMPOSE_PROFILES" up -d --build --remove-orphans
else
  docker compose up -d --build --remove-orphans
fi

echo "Waiting for backend health..."
for attempt in {1..30}; do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    echo "Backend healthy."
    break
  fi

  if [ "$attempt" -eq 30 ]; then
    echo "Backend did not become healthy." >&2
    docker compose ps
    docker compose logs --tail=100 backend
    exit 1
  fi

  sleep 2
done

sudo nginx -t
sudo systemctl reload nginx

docker image prune -f
docker compose ps
