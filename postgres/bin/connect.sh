#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check if the container is running
if ! docker compose ps --status running --format json postgres > /dev/null 2>&1; then
    echo "Error: PostgreSQL container is not running. Start it first with ./bin/start.sh"
    exit 1
fi

echo "Connecting to PostgreSQL..."
docker compose exec -it postgres psql -U postgres
