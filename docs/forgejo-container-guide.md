# Forgejo Container Guide

## Overview

This guide walks through setting up a self-hosted [Forgejo](https://forgejo.org/) instance in a Docker container with persistent data volumes, using the PostgreSQL practice environment from this repository as the backend database. Forgejo is a lightweight, community-driven Git platform — a fork of Gitea — that provides a self-hosted Git service with a web interface, issue tracking, and pull requests.

This is a **DevOps training exercise** designed to help you practice multi-service container management, persistent storage, service discovery, and Git workflows against a self-hosted platform.

## Why Forgejo for DevOps Training?

Forgejo is an excellent choice for learning DevOps fundamentals because it:

- **Works with PostgreSQL** — practice connecting services across containers
- **Provides real Git operations** — clone, push, pull, branches, tags
- **Has a web UI** — practice managing repositories, users, and settings
- **Is lightweight** — runs comfortably on modest hardware
- **Is open-source** — study the configuration, learn from the setup

## Prerequisites

- **Docker** installed and running on your machine
- **Docker Compose** (v2, bundled with Docker Desktop or installed separately)
- **Basic Git knowledge** — cloning, pushing, branching
- **A terminal** — for running Docker and Git commands
- **PostgreSQL practice environment** running (see `postgres/README.md`)

To verify your setup:

```bash
docker --version
docker compose version
git --version

# Verify the PostgreSQL container is running
cd ../postgres
docker compose ps
```

## Quick Start

### Step 1: Start the PostgreSQL Backend

Make sure the PostgreSQL practice container is running. It provides the database Forgejo will connect to.

```bash
cd ../postgres
./bin/start.sh
```

The PostgreSQL container (`postgres-practice`) runs on port `5432` with the default credentials from `postgres/docker-compose.yml`.

### Step 2: Create the Data Directory

Create the persistent data directory on your backup partition:

```bash
# Set up environment variables
cp .env.example .env
# Edit .env and change FORGEJO_DB_PASSWORD to a strong password
```

### Step 3: Create the Forgejo Database

Create a dedicated database and user for Forgejo in your existing PostgreSQL practice container:

```bash
cd ../postgres

# Create the forgejo user and database (use the password from your .env file)
docker compose exec -T postgres psql -U postgres -c "CREATE USER forgejo WITH PASSWORD 'YOUR_PASSWORD';"
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE forgejo OWNER forgejo;"
docker compose exec -T postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE forgejo TO forgejo;"
```

> **Security Warning:** Replace `YOUR_PASSWORD` with a strong, unique password. Never use example passwords in production.

### Step 4: Create `docker-compose.yml`

Create a Docker Compose file for Forgejo that connects to your existing PostgreSQL practice container:

```yaml
services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:17
    container_name: forgejo
    restart: unless-stopped
    ports:
      - "3000:3000"   # HTTP web interface
      - "2223:22"     # SSH Git operations
    volumes:
      - ${FORGEJO_DATA_DIR:-./data}:/data
    environment:
      - DATABASE_TYPE=postgres
      - DB_HOST=host.docker.internal
      - DB_PORT=5432
      - DB_NAME=forgejo
      - DB_USER=forgejo
      - DB_PASSWD=${FORGEJO_DB_PASSWORD:-changeme}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

This single-service setup uses:
- **PostgreSQL 16** from the existing `postgres/` subproject as the backend database
- **Bind mount** `${FORGEJO_DATA_DIR:-./data}:/data` for persistent storage — all repositories, avatars, and configuration survive container recreation
- **`host.docker.internal`** to reach the PostgreSQL container running on the host network

### Step 5: Start the Container

```bash
docker compose up -d
```

This starts the Forgejo container. It connects to your already-running PostgreSQL practice container.

### Step 6: First-Run Web Setup

1. Open `http://localhost:3000` in your browser
2. You'll see the Forgejo installation page
3. Configure the site:
   - **Site Title**: Enter a name (e.g., "My Forgejo Lab")
   - **Application URL**: `http://localhost:3000`
   - **Root Path**: `/`
   - **Server Domain**: `localhost`
   - **HTTP Port**: `3000`
   - **SSH Port**: `2223`
   - **Enable SSH**: Checked
4. Create the first administrator account:
   - **Username**: Choose an admin username
   - **Password**: Set a strong password
   - **Email**: Your email address
5. Click "Install Forgejo"

After installation, you'll be redirected to the dashboard.

## Persistent Storage

### How It Works

The `${FORGEJO_DATA_DIR:-./data}:/data` bind mount maps a directory on your host machine to the `/data` directory inside the container. This is where Forgejo stores:

| Path | Contents |
|---|---|
| `/data/gitea/conf/` | Configuration files (app.ini) |
| `/data/gitea/data/` | Sessions, indexes, attachments |
| `/data/gitea/repos/` | All Git repositories |
| `/data/gitea/public/` | Avatars, assets |

The PostgreSQL database stores its data separately (managed by the `postgres/` subproject).

### Why Persistence Matters

Without persistent storage, all your repositories and configuration would be lost when the container is removed. The bind mount ensures:

- **Repositories survive** container restarts and recreations
- **Configuration persists** across updates
- **Data is accessible** on the host for backup purposes

### Verifying Persistence

```bash
# Check the bind mount
docker inspect forgejo --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{end}}'

# Stop and recreate the container
docker compose down
docker compose up -d

# Your data is still there — visit http://localhost:3000
```

## Git Operations

### Clone a Repository

Once you've created a repository in the Forgejo web UI, you can interact with it via Git:

```bash
# HTTP clone
git clone http://localhost:3000/your-username/your-repo.git

# SSH clone
git clone ssh://git@localhost:2223/your-username/your-repo.git
```

### Push Changes

```bash
cd your-repo

# Make a change
echo "Hello Forgejo" > README.md
git add README.md
git commit -m "Initial commit"
git push origin main
```

### Create Repositories

You can create repositories in three ways:

1. **Web UI** — Click the "+" icon in the top-right corner
2. **Git push** — Push a new repository (if enabled by admin)
3. **CLI** — Use the Forgejo API (advanced)

### SSH vs HTTP

| Feature | HTTP | SSH |
|---|---|---|
| Authentication | Username + password or token | SSH key |
| Port | 3000 | 2223 |
| Setup | Immediate after web setup | Requires adding SSH key in profile |
| Recommended for | Quick testing | Regular development |

To set up SSH access:

1. Generate an SSH key if you don't have one: `ssh-keygen -t ed25519`
2. Copy the public key: `cat ~/.ssh/id_ed25519.pub`
3. In Forgejo, go to User Settings → SSH Keys → Add Key
4. Paste your public key

## Container Management

### Start, Stop, Restart

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f
```

### Update to a Newer Version

```bash
# Pull the latest image
docker compose pull

# Recreate the container with the new image
docker compose up -d
```

Forgejo handles database migrations automatically on startup.

### Backup Data

Since all data is stored in bind-mounted directories, backing up is straightforward:

```bash
# Stop the container to ensure data consistency
docker compose down

# Backup Forgejo data (repos, config, avatars)
tar czf forgejo-backup-$(date +%Y%m%d).tar.gz ./data

# Backup PostgreSQL data (use the postgres/ scripts)
cd ../postgres
./bin/backup.sh forgejo

# Restart the container
cd ../forgejo
docker compose up -d
```

### Restore from Backup

```bash
# Stop the container
docker compose down

# Restore Forgejo data
rm -rf ./data/*
tar xzf forgejo-backup-20241118.tar.gz -C ./data

# Restore PostgreSQL data (if needed)
cd ../postgres
cat backups/forgejo_*.sql | docker compose exec -T postgres psql -U postgres

# Start the container
cd ../forgejo
docker compose up -d
```

## Troubleshooting

### Port Already in Use

If you see an error like `bind: address already in use`:

```bash
# Check what's using port 3000
sudo lsof -i :3000

# Either stop the conflicting service or change the port in docker-compose.yml
# Change "3000:3000" to "8080:3000" to access via http://localhost:8080
```

### Container Won't Start

```bash
# Check logs for errors
docker compose logs

# Common issue: permission denied on data directory
# Fix by ensuring the directory exists and is writable
mkdir -p ./data
chown 1000:1000 ./data
```

### First-Run Setup Page Doesn't Appear

If you see a "Database is already initialized" error on a fresh install:

```bash
# Remove the data directory to start fresh
docker compose down
rm -rf ./data/*
mkdir -p ./data
chown 1000:1000 ./data
docker compose up -d
```

### SSH Connection Refused

```bash
# Verify the SSH port mapping
docker port forgejo

# Check if SSH is enabled in Forgejo settings
# Go to Admin → Configuration → SERVER → SSH_DOMAIN
```

### Git Clone Fails with Authentication Error

- For HTTP: Ensure you're using the correct username and password, or generate a personal access token in User Settings → Applications
- For SSH: Verify your SSH key is added to your Forgejo profile

### PostgreSQL Connection Error

If Forgejo can't connect to the database:

```bash
# Check the PostgreSQL practice container is running
cd ../postgres
docker compose ps

# Check PostgreSQL is accepting connections
docker compose exec -T postgres psql -U postgres -c "SELECT 1;"

# Verify the database environment variables match your PostgreSQL setup
# DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWD must be correct
```

If you see `FATAL: password authentication failed`, verify the `DB_PASSWD` environment variable matches the password you set for the `forgejo` database user.

## DevOps Learning Notes

### Cross-Container Service Communication

Forgejo connects to the PostgreSQL practice container running separately via `host.docker.internal`. Key concepts:

- **`host.docker.internal`** — a special DNS name that resolves to the host machine, allowing a container to reach services on the host's Docker network
- **`extra_hosts`** — explicitly maps `host.docker.internal` to the host gateway for reliable connectivity
- **Shared host network** — both containers can communicate through the host's network interface without needing a shared Docker Compose network

### Container Lifecycle

A Docker container goes through these states:

1. **Created** — `docker compose create` allocates resources
2. **Running** — `docker compose up -d` starts the process
3. **Paused** — `docker pause` suspends the container
4. **Stopped** — `docker compose stop` halts the process
5. **Removed** — `docker compose down` cleans up

The `restart: unless-stopped` policy ensures Forgejo automatically restarts after a host reboot or Docker daemon restart.

### Volume Management

Docker offers two main persistence mechanisms:

| Type | Example | Use Case |
|---|---|---|
| **Bind mount** | `${FORGEJO_DATA_DIR:-./data}:/data` | Development, easy backup access |
| **Named volume** | `forgejo-data:/data` | Production, Docker-managed storage |

Bind mounts are used in this guide because they make the data directory visible on the host, simplifying backups and inspection.

### Service Discovery

Forgejo connects to PostgreSQL using `host.docker.internal` as the `DB_HOST`. This special DNS name resolves to the host machine, allowing the Forgejo container to reach the PostgreSQL practice container running on the host's Docker network. In production, services typically share a Docker network and communicate by service name — this guide uses `host.docker.internal` because the two containers are managed by separate `docker compose` projects.

### Key Commands Reference

| Command | Purpose |
|---|---|
| `docker compose up -d` | Start services in the background |
| `docker compose down` | Stop and remove containers |
| `docker compose logs -f` | Stream logs in real time |
| `docker compose pull` | Download newer images |
| `docker compose ps` | List running containers |
| `docker inspect <container>` | View container details |
| `docker exec -it <container> sh` | Run a shell inside a container |

## Verification Checklist

Use this checklist to confirm your Forgejo setup is working correctly:

- [ ] Docker and Docker Compose are installed and running
- [ ] PostgreSQL practice container is running (`cd ../postgres && docker compose ps`)
- [ ] `docker compose up -d` starts the Forgejo container without errors
- [ ] `http://localhost:3000` loads the Forgejo web interface
- [ ] First-run installation completes successfully
- [ ] You can log in with the admin account
- [ ] A new repository can be created via the web UI
- [ ] `git clone` works over HTTP
- [ ] SSH key is added and `git clone` works over SSH (port 2223)
- [ ] Pushing changes to a repository succeeds
- [ ] Data persists after `docker compose down && docker compose up -d`
- [ ] Backup and restore procedure has been tested
- [ ] Container logs show no errors: `docker compose logs`