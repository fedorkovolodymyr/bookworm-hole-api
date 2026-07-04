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
- `task up` / `task down` — start/stop full stack via docker compose
- `task shell` — shell into the running api container
- `task test-container` / `task lint-container` / `task format-container` — same, run inside the api container
- `task migrate` / `task migrate:new -- "message"` — Alembic, inside the api container
- `task seed` / `task seed:test` — load dev / test fixture data
- `task psql` — psql shell against the dev database

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

## Task Maintenance
- All developer operations go through `Taskfile.yml` — no raw `docker compose` or `uv` commands in docs/scripts.
- Adding a new dev command/workflow requires updating `Taskfile.yml` (with a `desc:`), plus README.md and this file's Commands section, in the same change.

## Architecture
Layers: `routers/` → `services/` → `repositories/` → `models/`, `schemas/`
DB queries in repositories only. Business logic in services only.

## Key Files
- `app/repositories/book_repository.py` — BookRepository (async CRUD pattern to follow)
- `app/models/mixins.py` — IdMixin, TimestampMixin (use for all models)
- `app/models/catalog.py` — Book, Release, Contributor + join tables (bidirectional relationships, see Models rule below)
- `app/core/db.py` — get_session() DI dependency
- `app/core/config.py` — Settings class (api_settings, postgres_settings, auth_settings, app_settings); import as `from app.core.config import settings`, or inject via `Depends(get_settings)` (`@lru_cache`-backed)

## Models
- Models with bidirectional `Relationship()`/`back_populates` pairs go in one shared file (e.g. `app/models/catalog.py`), not split one-class-per-file. Splitting forces circular imports resolved via `if TYPE_CHECKING:` + string forward refs — avoid that pattern here. Models with no cross-relationships (e.g. `user.py`, `refresh_token.py`) still get their own file.

## Error Handling
- Domain errors live in `app/core/errors.py`: `AppError` (base, `status_code = 500`) and subclasses `NotFoundError` (404), `ConflictError` (409), `UnauthorizedError` (401), `ExternalServiceError` (502). Each takes a `detail: str` message.
- Services raise these directly (`raise NotFoundError("...")`) instead of `raise HTTPException(...)` or wrapping calls in `try/except Exception`. A single handler in `app/main.py` (`@app.exception_handler(AppError)`) translates any `AppError` to a JSON response — no per-service try/except needed to get an HTTP response.
- Recurring error message strings go in `ErrorMessages` (`app/core/errors.py`), not inline literals, so they aren't duplicated across call sites.
- Never catch bare `except Exception`. Ruff enforces this via `flake8-blind-except` (`BLE` in `[tool.ruff.lint] extend-select`). Catch the narrowest exception type that can actually occur (e.g. `jwt.PyJWTError`, `httpx.HTTPError`, `sqlalchemy.exc.SQLAlchemyError`) and either re-raise as an `AppError` subclass or let it propagate.
- The one sanctioned bare-except is `app/core/db.py::get_session`'s commit/rollback boundary — it must catch anything to roll back the transaction, so it carries an explicit `# noqa: BLE001` with a comment explaining why.
- At the adapter boundary (`app/services/external/`), catch the external library's specific exception (e.g. `httpx.HTTPError`) and re-raise as `ExternalServiceError` — callers in `services/` then don't need their own try/except around adapter calls.

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
- Group tests in classes (e.g. `class TestCreateBook:`), one class per endpoint/unit under test.
- Cover all cases: success paths + all error paths (validation, not-found, conflict, etc).
- Assert all relevant response/model attributes, not just status code.
- Partial-update (`PATCH`) endpoints: parametrized test per field of the Update schema, asserting both the changed field and that every other field stayed at its original value (catches the update method overwriting unset fields with `None`).

## Code Style
- Keep code simple. Avoid over-engineering.
- Comments: rare, only when non-obvious.
- Files: small, well-structured. Split big files into smaller ones.
- Avoid `# type: ignore`. Allowed only in rare cases.
- Use type hints everywhere: function args, return types, variables.
- Partial-update repository methods (`update(id, data)`) take the Pydantic Update schema (e.g. `UpdateBookSchema`) directly, not `dict`/`dict[str, Any]`. Call `data.model_dump(exclude_unset=True)` then `model.sqlmodel_update(...)` inside the repository method — keeps partial-update semantics (unset fields untouched) while the signature still says what shape the data is. See `app/repositories/book_repository.py::update`.

## Git
- Commit messages: one line only, no body. Conventional Commits format: `<type>(<scope>): <description>`

## Skills
- `/gh-issue-agent <N>` — full issue-to-PR pipeline (fetch→investigate→plan→implement→lint→test→review→PR)
- `/gh-add-issue` — add issue to BACKEND_ISSUES.md
