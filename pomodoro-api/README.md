# pomodoro-api

FastAPI **Pomodoro Attention API**: records and reads finished pomodoro sessions directly in the Focus To-Do export schema (`schema.sql`) in PostgreSQL, so browser-extension exports (`data.sql`) and API-written rows share the same tables.

The Python package remains `app`. This directory was previously named `PythonProject`.

## Requirements

- Python 3.12+ (Docker image uses `python:3.12-slim`)
- PostgreSQL (the API image does **not** start a database)

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:5432/focustodo
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Do not put real credentials in `.env` or in this repository. Export `DATABASE_URL` in the shell (or pass `-e` to Docker). `.env.example` lists variable **names** and placeholder values only. This directory’s `.gitignore` ignores `.env`, virtualenvs, and Python caches, and keeps `.env.example`.

Required environment variable:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Postgres URL for the API and Alembic. `Settings` can also load this from a `.env` file in the working directory if present; prefer exporting it instead of storing secrets on disk. |

Optional:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8000` | Used **only** by `docker-entrypoint.sh` (`uvicorn` on `0.0.0.0:$PORT`). The local command above binds port `8000` explicitly; `Settings.port` does not bind a socket. For Docker, pass `-e PORT=...`. A file at `/app/.env` may supply `DATABASE_URL` but does **not** change `PORT`. |
| `DB_CONNECT_TIMEOUT` | `3` | SQLAlchemy connect timeout (seconds). |
| `DB_POOL_TIMEOUT` | `5` | Pool checkout timeout (seconds). |
| `TEST_DATABASE_URL` | see Tests | Overrides the pytest default URL. |

## Database

The API targets the `focustodo` database on the PG15 `postgres-practice` container. Its four tables (`projects`, `tasks`, `subtasks`, `pomodoro_sessions`) are defined by `schema.sql` and must stay exactly as the extension export expects; the API adds no columns or tables except Alembic's `alembic_version`.

- **Baseline migration** `0001_focus_todo_baseline` embeds the `schema.sql` DDL verbatim with `CREATE TABLE/INDEX IF NOT EXISTS`. On a database already loaded from the export, `alembic upgrade head` only creates `alembic_version`; on an empty database it creates the schema. `tests/test_migration.py` fails if the migration drifts from `schema.sql` or the ORM drifts from the database. If `schema.sql` changes, add a new migration.
- **Privileges** for the `DATABASE_URL` role (tables are owned by `postgres`):

  ```sql
  GRANT CONNECT ON DATABASE focustodo TO pomodoro_api;
  GRANT USAGE, CREATE ON SCHEMA public TO pomodoro_api;          -- CREATE for alembic_version
  GRANT SELECT ON projects, tasks, subtasks TO pomodoro_api;
  GRANT SELECT, INSERT, UPDATE ON pomodoro_sessions TO pomodoro_api;
  ```

### Data model notes

- **Finished sessions only**, like the extension: a row is written when a pomodoro ends. There is no server-side running timer.
- **Seconds everywhere**: `interval_seconds` is the actual focused time, `pomodoro_interval` the planned length (defaults to the task's `pomodoro_interval`).
- **Derived fields** in responses: `started_at = end_date - interval_seconds`, `completed = interval_seconds >= pomodoro_interval`, and `task_name` from `tasks`.
- **Ids are opaque text**, matched exactly (the extension mixes upper- and lower-case UUIDs). The API generates upper-case UUIDs.
- **API-written rows** get `obj_type='POMODORO'`, `state=0`, `sync=0` (never synced to the Focus To-Do cloud; imported rows carry `sync=1`) and `creation_date = end_date`.
- **Soft delete**: `state = -1`, as in the extension. All reads exclude such rows.
- **Re-imports are safe**: `data.sql` uses `INSERT ... ON CONFLICT (id) DO NOTHING`, so it never overwrites API rows.
- `tasks.actual_pomo_num` is not maintained (the extension does not keep it consistent either).

## HTTP API

OpenAPI title: **Pomodoro Attention API**. Interactive docs: `/docs`.

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/health` | Liveness: `{"status":"ok"}` |
| `GET` | `/ready` | Readiness: `SELECT 1` against Postgres; `503` if unavailable |
| `POST` | `/sessions` | Record a finished session (`201`). Body: `task_id`, `interval_seconds` (1–86400, integer); optional `pomodoro_interval` (1–86400), `subtask_id`, `end_date` (default now; naive = UTC), `is_manual` (default `false`). `404` for an unknown/deleted task or subtask, `422` if the subtask belongs to another task or the body is invalid. |
| `GET` | `/sessions` | List non-deleted sessions, newest `end_date` first. Optional query `from`, `to` (datetimes on `end_date`; naive = UTC) and `task_id`. |
| `GET` | `/sessions/{session_id}` | One session; `404` if missing or deleted. |
| `DELETE` | `/sessions/{session_id}` | Soft-delete (`state=-1`), `204`; `404` if missing or already deleted. |
| `GET` | `/projects` | Read-only list of non-deleted projects. |
| `GET` | `/tasks` | Read-only list of non-deleted tasks. Optional query `project_id`. |

Example:

```bash
curl -sS http://127.0.0.1:8000/tasks
curl -sS -X POST http://127.0.0.1:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{"task_id":"TASK-ID","interval_seconds":1500}'
curl -sS 'http://127.0.0.1:8000/sessions?from=2026-11-12T00:00:00Z&task_id=TASK-ID'
```

## Tests

Domain and schema-drift tests do not need Postgres. API tests use the `client` fixture in `tests/conftest.py`: they skip if the database is unreachable, run `alembic upgrade head` on it, and seed (then delete) their own projects, tasks and subtasks via the `catalog` fixture. Migration tests create and drop scratch databases on the same server. Use a **throwaway** server — never the live `focustodo` database (tests write rows and force session timezone `America/New_York`).

Default URL when `TEST_DATABASE_URL` is unset: user `postgres`, database `postgres`, host `127.0.0.1:55432`. The password must match `DEFAULT_TEST_DATABASE_URL` in `tests/conftest.py` or the reachability check fails and API tests skip.

```bash
(
  set -euo pipefail

  # Throwaway Postgres matching the pytest default (password is the test fixture, not a production secret)
  docker run --rm -d --name pomodoro-api-test-pg \
    -p 127.0.0.1:55432:5432 \
    -e POSTGRES_PASSWORD=review \
    postgres:15
  trap 'docker stop pomodoro-api-test-pg >/dev/null 2>&1 || true' EXIT

  # Wait up to 30 seconds for TCP readiness inside the container (socket-only checks can pass during init).
  for attempt in {1..30}; do
    if docker exec pomodoro-api-test-pg pg_isready -h 127.0.0.1 -U postgres -d postgres -q; then
      break
    fi
    if [ "$attempt" -eq 30 ]; then
      echo "Postgres did not become ready within 30 seconds" >&2
      exit 1
    fi
    sleep 1
  done

  export TEST_DATABASE_URL=postgresql://postgres:review@127.0.0.1:55432/postgres
  pytest
)
```

The parentheses run the block in a subshell, so `set -euo pipefail`, the `trap`, and `exit` do not affect your interactive shell. The exit trap stops the disposable container when the subshell exits (after the commands finish or fail). If you interrupt the subshell or the container is left behind, stop it manually with `docker stop pomodoro-api-test-pg`.

To use another password or host, set `TEST_DATABASE_URL` to that instance (the role needs `CREATEDB` for the migration tests). Prefer `.venv/bin/python -m pytest` if the venv was created on another path.

## Docker

Standalone image (no Compose). Startup runs `alembic upgrade head`, then uvicorn on `0.0.0.0:${PORT:-8000}`. A failed migration exits the container.

```bash
docker build -t pomodoro-api .
docker run --rm -p 8000:8000 \
  --network postgres_default \
  -e DATABASE_URL=postgresql://USER:PASSWORD@postgres-practice:5432/focustodo \
  pomodoro-api
```

`localhost` inside the container is the container itself. Prefer attaching to the Postgres Docker network (for this lab: `postgres-practice` on `postgres_default`). See comments in `.env.example` for `host.docker.internal` and host-bind caveats.
