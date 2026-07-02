# bookworm-hole-api

## Commands
- `task format` — ruff import sort + format
- `task lint` — ruff check + pyright (both must pass)
- `task type-check` — pyright only
- `task test` — pytest (asyncio_mode=auto)
- `task test -- --collect-only` — verify pytest config loads
- `task dev` — FastAPI local with hot-reload (needs services running)
- `task alembic-revision -- "message"` — create migration
- `task alembic-upgrade` — apply migrations to head

## Dev Environments

### Option A — Dev Container (recommended)
Open in VS Code → "Reopen in Container". Spins up api + postgres + redis automatically.
- All services reachable by hostname: `postgres`, `redis`
- `postCreateCommand` runs `uv sync` + `task alembic-upgrade`
- Start API inside container: `task dev`
- Ports forwarded: 8000 (API), 5432 (PG), 6379 (Redis)

### Option B — Local + Docker services
```bash
cp .env.example .env          # once
task docker-compose-up        # start postgres + redis (+ api)
task alembic-upgrade          # apply migrations
task dev                      # run FastAPI locally
```
Key tasks:
- `task docker-compose-up` — start all services (detached)
- `task docker-compose-stop` — stop without removing volumes
- `task docker-compose-down` — stop + remove containers
- `task docker-compose-postgres` — start only postgres
- `task docker-compose-logs` — follow logs

### Option C — Full Docker (production-like)
```bash
docker compose up -d          # api + postgres + redis
```
API served at `http://localhost:${API_PORT}`.

## Architecture
Layers: `routers/` → `services/` → `repositories/` → `models/`, `schemas/`
DB queries in repositories only. Business logic in services only.

## Key Files
- `app/repositories/book_repository.py` — BookRepository (async CRUD pattern to follow)
- `app/models/mixins.py` — IdMixin, TimestampMixin (use for all models)
- `app/core/db.py` — get_session() DI dependency
- `app/core/config.py` — Settings class (api_settings, postgres_settings); import as `from app.core.config import settings`

## Gotchas
- pyright `include = ["app", "scripts"]` required — omitting causes .venv scan (8600 errors)
- SQLModel needs `reportIncompatibleVariableOverride = "none"` + `reportAssignmentType = "none"`
- `alembic/` excluded from pyright (uses sqlmodel internals not in stubs)
- `.claude/` is gitignored — skills live locally only
- Inside devcontainer: `.venv` is an anonymous volume; host `.venv` not mounted (prevents arch mismatch)
- `POSTGRES_HOST` overridden to `postgres` in devcontainer/docker-compose (not `localhost`)

## Testing
- pytest-asyncio `asyncio_mode = "auto"`, testpaths = `tests/`
- Route tests: `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`
- `tests/conftest.py` — shared `async_client` fixture (no DB override; for pure HTTP tests)
- For tests needing DB: override `get_session` in the test file via `app.dependency_overrides[get_session] = async_generator_fn`

## Code Style
- Keep code simple. Avoid over-engineering.
- Comments: rare, only when non-obvious.
- Files: small, well-structured. Split big files into smaller ones.
- Avoid `# type: ignore`. Allowed only in rare cases.
- Use type hints everywhere: function args, return types, variables.

## Git
- Commit messages: short, one line only. No body.

## Skills
- `/gh-issue-agent <N>` — full issue-to-PR pipeline (fetch→investigate→plan→implement→lint→test→review→PR)
- `/gh-add-issue` — add issue to BACKEND_ISSUES.md
