#!/bin/bash
# One-command redeploy for the NEXUS droplet.
set -e
git pull
docker-compose build
docker-compose up -d
docker image prune -f
echo "✅ NEXUS redeployed."
