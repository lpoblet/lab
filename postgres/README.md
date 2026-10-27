# PostgreSQL Practice Environment

This directory contains a Docker-based PostgreSQL server for hands-on practice. It is designed to help you learn database administration skills relevant to the **LPIC-1 Linux certification**, particularly around service management, configuration, user management, and backups.

## Quick Start

```bash
# Start the PostgreSQL server
./bin/start.sh

# Connect to the database shell
./bin/connect.sh

# Stop the server
./bin/stop.sh
```

## What is PostgreSQL?

PostgreSQL (often called "Postgres") is a powerful, open-source relational database management system. It extends the SQL standard with features like:

- **ACID compliance** — reliable transactions
- **Advanced data types** — arrays, JSON, hstore, full-text search
- **Extensibility** — custom types, operators, and languages (PL/pgSQL, Python, etc.)
- **Concurrency** — MVCC (Multi-Version Concurrency Control)

For LPIC-1, you don't need to be a PostgreSQL expert, but you should understand how to install, configure, start/stop, and manage a database service on Linux.

## Why Practice with Docker?

Running PostgreSQL in Docker gives you:

- **Isolation** — no risk of conflicting with a system-wide installation.
- **Clean slate** — destroy and recreate the environment anytime.
- **Portability** — works the same on any machine with Docker.
- **Realistic practice** — you still interact with the database via `psql`, `pg_dump`, etc., just like on a real server.

## Project Structure

```
postgres/
├── README.md            # This file
├── docker-compose.yml   # PostgreSQL container configuration
├── bin/
│   ├── start.sh         # Start the container
│   ├── stop.sh          # Stop the container
│   ├── connect.sh       # Connect to psql shell
│   └── backup.sh        # Run pg_dump for backup practice
└── templates/
    ├── pg_hba.conf.example
    └── postgresql.conf.example
```

## Configuration Files

### `postgresql.conf`

The main configuration file controls server behavior: listening address, ports, memory settings, logging, and more. Key settings for learning:

| Setting | Description |
|---|---|
| `listen_addresses` | Which network interfaces to accept connections on |
| `port` | TCP port (default: 5432) |
| `max_connections` | Maximum simultaneous connections |
| `shared_buffers` | Memory allocated for caching data |
| `log_destination` | Where to write log messages |
| `logging_collector` | Enable/disable log collection |

See `templates/postgresql.conf.example` for a commented example.

### `pg_hba.conf`

The Host-Based Authentication file controls **who** can connect, **from where**, and **how** they authenticate. Each line defines a rule:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     peer
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
```

Authentication methods:
- **trust** — no password required (dangerous, for testing only)
- **peer** — OS username must match database username (local only)
- **md5** / **scram-sha-256** — password-based authentication
- **reject** — explicitly deny connections

See `templates/pg_hba.conf.example` for a commented example.

## Practice Exercises

### 1. Service Management

```bash
# Start the database
./bin/start.sh

# Check it's running
docker compose ps

# View logs
docker compose logs

# Stop the database
./bin/stop.sh
```

**Try:** Start the server, check the logs for the "ready to accept connections" message, then stop it.

### 2. Connecting to the Database

```bash
./bin/connect.sh
```

This opens the `psql` interactive shell. From here:

```sql
-- List all databases
\l

-- Connect to a database
\c postgres

-- List all tables in the current database
\dt

-- List all roles (users)
\du

-- Exit
\q
```

### 3. User (Role) Management

In PostgreSQL, users are called **roles**. Practice creating and managing them:

```sql
-- Create a new role with a password
CREATE ROLE app_user WITH LOGIN PASSWORD 'secret123';

-- Grant database creation privilege
ALTER ROLE app_user CREATEDB;

-- Revoke a privilege
ALTER ROLE app_user NOCREATEDB;

-- Drop a role
DROP ROLE app_user;
```

**Exercise:** Create a role called `lpic_student` with login and createdb privileges, then verify it with `\du`.

### 4. Database Creation

```sql
-- Create a new database
CREATE DATABASE practice_db OWNER app_user;

-- List databases
\l

-- Connect to the new database
\c practice_db

-- Drop a database
DROP DATABASE practice_db;
```

**Exercise:** Create a database, connect to it, create a simple table, insert some rows, query them, then drop the database.

### 5. Tables and Data

```sql
-- Create a table
CREATE TABLE pomodoros (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    duration_minutes INTEGER,
    status TEXT CHECK (status IN ('completed', 'abandoned', 'interrupted')),
    notes TEXT
);

-- Insert data
INSERT INTO pomodoros (duration_minutes, status, notes)
VALUES (25, 'completed', 'Focus on Linux file permissions');

-- Query data
SELECT * FROM pomodoros;
SELECT COUNT(*) FROM pomodoros WHERE status = 'completed';
SELECT SUM(duration_minutes) AS total_minutes FROM pomodoros;

-- Update a row
UPDATE pomodoros SET status = 'abandoned' WHERE id = 1;

-- Delete a row
DELETE FROM pomodoros WHERE id = 1;

-- Drop the table
DROP TABLE pomodoros;
```

### 6. Backups and Restore

```bash
# Full backup of a database
./bin/backup.sh practice_db

# Restore from a backup
pg_restore -U postgres -d practice_db backup_file.sql
```

**Exercise:** Create a database with some data, back it up, drop the database, then restore it from the backup.

### 7. Monitoring

```sql
-- View current connections
SELECT pid, usename, datname, state, query FROM pg_stat_activity;

-- View database sizes
\du+
\l+

-- View table sizes
SELECT pg_size_pretty(pg_total_relation_size('pomodoros'));
```

## LPIC-1 Relevant Topics

The LPIC-1 exam covers database administration at a basic level. Key topics:

1. **Installing and starting a database service** — covered by `start.sh` and Docker Compose.
2. **Configuring a database server** — practice with `postgresql.conf` and `pg_hba.conf` templates.
3. **Creating and managing users** — role creation, privileges, and authentication.
4. **Database backups** — using `pg_dump` and `pg_restore`.
5. **Service monitoring** — checking logs, connections, and resource usage.

## Custom Configuration

To override the default configuration, mount your custom files via Docker Compose:

```yaml
volumes:
  - ./my-postgresql.conf:/etc/postgresql/postgresql.conf:ro
  - ./my-pg-hba.conf:/etc/postgresql/pg_hba.conf:ro
```

Then restart the container. Use the `templates/` examples as a starting point.
