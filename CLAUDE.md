# bookworm-hole-api

## Commands
- `task format` — ruff import sort + format
- `task lint` — ruff check + pyright (both must pass)
- `task type-check` — pyright only
- `task test` — pytest (asyncio_mode=auto)
- `task test -- --collect-only` — verify pytest config loads
- `task dev` — FastAPI local (needs Docker postgres via `task docker-compose-postgres`)
- `task alembic-revision -- "message"` — create migration

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

## Testing
- pytest-asyncio `asyncio_mode = "auto"`, testpaths = `tests/`
- Route tests: `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`
- `tests/conftest.py` — shared `async_client` fixture (no DB override; for pure HTTP tests)
- For tests needing DB: override `get_session` in the test file via `app.dependency_overrides[get_session] = async_generator_fn`

## Skills
- `/gh-issue-agent <N>` — full issue-to-PR pipeline (fetch→investigate→plan→implement→lint→test→review→PR)
- `/gh-add-issue` — add issue to BACKEND_ISSUES.md
