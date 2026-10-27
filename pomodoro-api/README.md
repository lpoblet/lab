# pomodoro-api

FastAPI **Pomodoro Attention API**: create, list, complete, and interrupt pomodoro sessions stored in PostgreSQL.

The Python package remains `app`. This directory was previously named `PythonProject`.

## Requirements

- Python 3.12+ (Docker image uses `python:3.12-slim`)
- PostgreSQL (the API image does **not** start a database)

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:5432/DBNAME
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

## HTTP API

OpenAPI title: **Pomodoro Attention API**. Interactive docs: `/docs`.

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/health` | Liveness: `{"status":"ok"}` |
| `GET` | `/ready` | Readiness: `SELECT 1` against Postgres; `503` if unavailable |
| `POST` | `/sessions` | Start a session (`201`). Body: `kind`, `duration_minutes` (1–1440), optional `label` (max 256). `kind`: `focus`, `short_break`, `long_break`. |
| `GET` | `/sessions` | List sessions. Optional query `from` and `to` (datetimes). |
| `POST` | `/sessions/{session_id}/complete` | Complete a running session. `404` if missing, `409` if invalid transition. |
| `POST` | `/sessions/{session_id}/interrupt` | Interrupt a running session. Same error codes. |

Example:

```bash
curl -sS -X POST http://127.0.0.1:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{"kind":"focus","duration_minutes":25,"label":"deep work"}'
```

## Tests

Domain tests do not need Postgres. API tests use the `client` fixture in `tests/conftest.py`: they skip if the database is unreachable, and they **do not** run Alembic or `create_all`. Use a **throwaway** database (tests write rows and force session timezone `America/New_York`).

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
  export DATABASE_URL="$TEST_DATABASE_URL"
  alembic upgrade head
  pytest
)
```

The parentheses run the block in a subshell, so `set -euo pipefail`, the `trap`, and `exit` do not affect your interactive shell. The exit trap stops the disposable container when the subshell exits (after the commands finish or fail). If you interrupt the subshell or the container is left behind, stop it manually with `docker stop pomodoro-api-test-pg`.

To use another password or host, set `TEST_DATABASE_URL` to that instance and migrate it the same way. Prefer `.venv/bin/python -m pytest` if the venv was created on another path.

## Docker

Standalone image (no Compose). Startup runs `alembic upgrade head`, then uvicorn on `0.0.0.0:${PORT:-8000}`. A failed migration exits the container.

```bash
docker build -t pomodoro-api .
docker run --rm -p 8000:8000 \
  --network postgres_default \
  -e DATABASE_URL=postgresql://USER:PASSWORD@postgres-practice:5432/DBNAME \
  pomodoro-api
```

`localhost` inside the container is the container itself. Prefer attaching to the Postgres Docker network (for this lab: `postgres-practice` on `postgres_default`). See comments in `.env.example` for `host.docker.internal` and host-bind caveats.
