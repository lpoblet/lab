# PostgreSQL Storage Migration Guide

## Overview

This document guides the migration of PostgreSQL persistent storage from a Docker named volume to a bind mount (configurable via `PG_DATA_DIR`, defaulting to `./data`), along with a container image upgrade from `postgres:15` to `postgres:16`.

This is a **major version upgrade** (15 → 16). The dump/restore method is used, which is the safest approach for cross-major-version migrations.

## Current State

- **Storage**: Docker named volume `postgres-data` mounted at `/var/lib/postgresql/data` inside the container
- **Image**: `postgres:15`
- **Container name**: `postgres-practice`
- **Port**: `5432`
- **Scripts**: `bin/start.sh`, `bin/stop.sh`, `bin/connect.sh`, `bin/backup.sh`

## Target State

- **Storage**: Bind mount `${PG_DATA_DIR:-./data}` on the host → `/var/lib/postgresql/data` in the container
- **Image**: `postgres:16`
- **Container name**: `postgres-practice` (unchanged)
- **Port**: `5432` (unchanged)
- **Data**: All existing databases and roles migrated intact

## Prerequisites

- Docker and Docker Compose installed and running
- Write access to the target data directory (default: `./data` within the project)
- The target partition must have enough free space for the PostgreSQL data directory
- `shellcheck` installed (for script validation)

## Migration Procedure

### Step 1: Verify Current State

Before starting, check what data exists:

```bash
# Check container is running
cd postgres
docker compose ps

# List databases
docker compose exec -T postgres psql -U postgres -c "\l"

# List roles
docker compose exec -T postgres psql -U postgres -c "\du"
```

Note down the databases and roles for verification after migration.

### Step 2: Pre-migration Backup

Create a backup of all databases as a safety net:

```bash
cd postgres

# Backup each database
./bin/backup.sh postgres
# Repeat for any other databases found in Step 1
```

Backups are stored in `postgres/backups/`.

### Step 3: Stop the Container

```bash
./bin/stop.sh
```

This runs `docker compose down` which stops and removes the container but preserves the named volume.

### Step 4: Export All Data

Export all roles and databases using `pg_dumpall`. Start a temporary container to access the existing volume:

```bash
# Start a temporary container with the old volume to export data
docker run --rm \
  --volume postgres-data:/var/lib/postgresql/data:ro \
  --network host \
  postgres:15 \
  pg_dumpall -U postgres > postgres/backups/pg_dumpall_pre_migration.sql

# Verify the export
wc -l postgres/backups/pg_dumpall_pre_migration.sql
```

This captures all roles, databases, and data in a single SQL file.

### Step 5: Reconfigure docker-compose.yml

Update `postgres/docker-compose.yml`:

1. Change the image from `postgres:15` to `postgres:16`
2. Replace the named volume with a bind mount to `${PG_DATA_DIR:-./data}`
3. Remove the top-level `volumes:` declaration (no longer needed)

### Step 6: Create Host Directory

```bash
# Create the target directory (default: ./data, or set PG_DATA_DIR for a custom path)
mkdir -p ./data

# Set correct ownership (PostgreSQL runs as UID 70 in the container)
sudo chown 70:70 ./data

# Set correct permissions
sudo chmod 700 ./data
```

### Step 7: Start the New Container

```bash
cd postgres

# Pull the new image
docker compose pull

# Start the container
./bin/start.sh
```

The container will initialize a fresh PostgreSQL 16 data directory at the configured data path (default: `./data`).

### Step 8: Import Data

Restore from the `pg_dumpall` export:

```bash
# Import the dump into the new container
cat postgres/backups/pg_dumpall_pre_migration.sql | \
  docker compose exec -T postgres psql -U postgres
```

### Step 9: Verify Migration

```bash
# Check databases match the pre-migration list
docker compose exec -T postgres psql -U postgres -c "\l"

# Check roles match the pre-migration list
docker compose exec -T postgres psql -U postgres -c "\du"

# Verify data integrity with sample queries
docker compose exec -T postgres psql -U postgres -c "SELECT count(*) FROM information_schema.tables;"
```

Compare the output with the notes from Step 1.

## Rollback Procedure

If migration fails or data is corrupted:

### Option A: Revert Configuration

1. Restore `docker-compose.yml` to use the named volume `postgres-data`
2. Run `docker compose down && docker compose up -d`
3. The old data is still in the named volume

### Option B: Restore from Backup

1. Stop the container: `./bin/stop.sh`
2. Start a temporary container with the named volume:
   ```bash
   docker run --rm \
     --volume postgres-data:/var/lib/postgresql/data \
     --network host \
     postgres:15
   ```
3. Restore from `bin/backup.sh` backups:
   ```bash
   cat postgres/backups/postgres_*.sql | \
     docker compose exec -T postgres psql -U postgres
   ```

## Verification Checklist

- [ ] `shellcheck` passes for all scripts in `bin/`
- [ ] `docker compose config` validates the new configuration without errors
- [ ] All pre-migration databases exist in the new container
- [ ] All pre-migration roles exist in the new container
- [ ] Data integrity verified with sample queries
- [ ] Container starts and stops correctly with `bin/start.sh` and `bin/stop.sh`
- [ ] `bin/connect.sh` works with the new configuration
- [ ] `bin/backup.sh` works with the new configuration

## DevOps Learning Notes

### Why Bind Mounts?

- **Portability**: Bind mounts tie data to a specific host path, making it easy to locate and manage backups
- **Performance**: Direct filesystem access can be faster than Docker volumes on some setups
- **Control**: You control the directory permissions and location directly

### Why Dump/Restore for Major Upgrades?

- PostgreSQL major versions (15 → 16) may have internal format changes
- `pg_upgrade` is faster but more complex and requires both versions installed
- Dump/restore is the safest method and works across any major version gap
- For training purposes, dump/restore teaches the most transferable skills

### Key Commands Reference

| Command | Purpose |
|---|---|
| `pg_dumpall` | Dump all databases and roles to SQL |
| `pg_dump` | Dump a single database |
| `psql -f file.sql` | Restore from SQL file |
| `docker volume ls` | List Docker volumes |
| `docker volume inspect` | Inspect a volume's mount point |
| `docker compose config` | Validate compose file syntax |
