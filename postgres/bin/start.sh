#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
echo "$PROJECT_DIR"

echo "Starting PostgreSQL container..."
docker compose up -d

echo "Waiting for PostgreSQL to be ready..."
sleep 3
if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "PostgreSQL is ready and accepting connections on port 5432."
else
    echo "PostgreSQL is starting. Try connecting in a few seconds."
fi
