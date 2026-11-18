#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Starting Forgejo and PostgreSQL containers..."
docker compose up -d

echo "Waiting for services to be ready..."
sleep 5

if docker compose exec -T forgejo healthcheck > /dev/null 2>&1; then
    echo "Forgejo is ready at http://localhost:3000"
else
    echo "Forgejo is starting. Try accessing http://localhost:3000 in a few seconds."
fi
