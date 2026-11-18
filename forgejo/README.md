# Forgejo Practice Environment

This directory contains a Docker-based [Forgejo](https://forgejo.org/) server (self-hosted Git platform) with a PostgreSQL backend for hands-on practice. It is designed to help you learn **multi-service container management**, **persistent storage**, and **Git workflows**.

## Quick Start

```bash
# Set up environment variables
cp .env.example .env
# Edit .env and change FORGEJO_DB_PASSWORD to a strong password

# Create the Forgejo database in your existing PostgreSQL practice container
cd ../postgres
docker compose exec -T postgres psql -U postgres -c "CREATE USER forgejo WITH PASSWORD 'YOUR_PASSWORD';"
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE forgejo OWNER forgejo;"

# Start the Forgejo container
cd ../forgejo
./bin/start.sh

# Open http://localhost:3000 in your browser to complete the first-run setup
```

## What is Forgejo?

Forgejo is a lightweight, community-driven Git platform — a fork of Gitea — that provides a self-hosted Git service with a web interface, issue tracking, pull requests, and more. It runs comfortably on modest hardware and is fully open-source.

## Project Structure

```
forgejo/
├── README.md            # This file
├── docker-compose.yml   # Forgejo container configuration
├── .env.example         # Environment variable template
└── bin/
    ├── start.sh         # Start the container
    ├── stop.sh          # Stop the container
    └── logs.sh          # Stream Forgejo logs
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and adjust the values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `FORGEJO_DB_PASSWORD` | PostgreSQL password for the Forgejo database | `changeme` |
| `FORGEJO_DB_HOST` | PostgreSQL host | `host.docker.internal` |
| `FORGEJO_DB_NAME` | Database name | `forgejo` |
| `FORGEJO_DB_USER` | Database user | `forgejo` |
| `FORGEJO_DATA_DIR` | Host path for persistent data | `./data` |

> **Security Warning:** The default password is for practice only. Replace it with a strong, unique password before any real use.

### Persistent Storage

Forgejo data is stored via a bind mount. By default, data is stored in a local `./data` directory. You can configure a custom host path via the `FORGEJO_DATA_DIR` environment variable:

| Mount | Contents |
|---|---|
| `${FORGEJO_DATA_DIR:-./data}:/data` | Repositories, configuration, avatars |

The PostgreSQL database is managed by the `postgres/` subproject.

## Container Management

```bash
# Start
./bin/start.sh

# Stop
./bin/stop.sh

# View logs
./bin/logs.sh

# Update to a newer version
docker compose pull
docker compose up -d
```

## First-Run Web Setup

1. Open `http://localhost:3000` in your browser
2. Configure the site title, application URL, and server settings
3. Create the first administrator account
4. Click "Install Forgejo"

## Git Operations

```bash
# Clone a repository via HTTP
git clone http://localhost:3000/your-username/your-repo.git

# Clone via SSH (after adding your SSH key in Forgejo settings)
git clone ssh://git@localhost:2223/your-username/your-repo.git
```

## Backup

```bash
# Stop container
./bin/stop.sh

# Backup Forgejo data (adjust path if using FORGEJO_DATA_DIR)
tar czf forgejo-backup-$(date +%Y%m%d).tar.gz ./data

# Backup PostgreSQL data
cd ../postgres
./bin/backup.sh forgejo

# Restart
./bin/start.sh
```

## Ports

| Port | Service |
|---|---|
| `3000` | Forgejo HTTP web interface |
| `2223` | Forgejo SSH Git operations |

## Full Guide

See [docs/forgejo-container-guide.md](../docs/forgejo-container-guide.md) for the complete DevOps training guide with troubleshooting, learning notes, and verification checklist.
