#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <database_name>"
    echo "Example: $0 postgres"
    exit 1
fi

DATABASE="$1"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/${DATABASE}_${TIMESTAMP}.sql"

# Check if the container is running
if ! docker compose ps --status running --format json postgres > /dev/null 2>&1; then
    echo "Error: PostgreSQL container is not running. Start it first with ./bin/start.sh"
    exit 1
fi

# Create backups directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Backing up database '$DATABASE'..."
docker compose exec -T postgres pg_dump -U postgres -F plain "$DATABASE" > "$BACKUP_FILE"

echo "Backup saved to: $BACKUP_FILE"
echo "File size: $(du -h "$BACKUP_FILE" | cut -f1)"
