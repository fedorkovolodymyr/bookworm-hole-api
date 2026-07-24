# bookworm-hole-api

## Commands

- `task format` — ruff import sort + format
- `task lint` — ruff check + pyright (both must pass)
- `task lint-format` — run format then lint in sequence
- `task type-check` — pyright only
- `task test` — pytest (asyncio_mode=auto), against an isolated `*_test` database auto-created/migrated at session start, with coverage report (term-missing + xml)
- `task test -- --collect-only` — verify pytest config loads
- `task precommit-install` — install git pre-commit hooks (required first-time setup)
- `task precommit` — run all pre-commit hooks against every file (same set CI runs)
- `task dev` — FastAPI local with hot-reload (needs services running)
- `task alembic-revision -- "message"` — create migration
- `task alembic-upgrade` — apply migrations to head
- `task alembic-downgrade` — rollback last migration
- `task up` / `task down` — start/stop full stack via docker compose
- `task shell` — shell into the running api container
- `task test-container` / `task lint-container` / `task format-container` — same, run inside the api container
- `task migrate` / `task migrate:new -- "message"` — Alembic, inside the api container
- `task seed` / `task seed:catalog` / `task seed:dev` / `task seed:test` — load default / catalog / dev fixtures (5 users + collections/reviews/sessions) / test seed data
- `task psql` — psql shell against the dev database
- `task refresh-metadata` — manually refresh stale release metadata from external sources (releases older than N days, default 30)
- `task purge-deleted-users` — hard-delete accounts past their GDPR deletion grace period (anonymizes their reviews first)
- `task worker` — run the `arq` background worker locally (needs Postgres + Redis running); processes catalog-import jobs
- `task worker-container` — same, inside the running api container
- `task release-dry-run` — preview next version bump from commits since last tag, no changes made
- `task release` — bump `pyproject.toml` version, tag, publish GitHub release (CI-only, see Release Flow)
- `task coverage-badge` — regenerate `coverage.svg` from the last test run (CI-only, committed on push to `main`)
- `task coverage-check` — fail if total coverage from the last test run dropped below `.coverage-baseline`
- `task coverage-update-baseline` — write current total coverage % to `.coverage-baseline` (CI-only, committed on push to `main`)

## Dev Environments

### Option A — Dev Container (recommended)

Open in VS Code → "Reopen in Container". Spins up api + postgres + redis automatically.

- All services reachable by hostname: `postgres`, `redis`
- `postCreateCommand` runs `uv sync` + `task alembic-upgrade`
- Start API inside container: `task dev`
- Ports forwarded: 8000 (API), 5432 (PG), 6379 (Redis)
- Run `task precommit-install` once after first sync (required — commits are expected to run local hooks)

### Option B — Local + Docker services

```bash
cp .env.example .env          # once
task docker-compose-up        # start postgres + redis (+ api)
task alembic-upgrade          # apply migrations
task precommit-install        # once, required — installs git pre-commit hooks
task dev                      # run FastAPI locally
```

Key tasks:

- `task docker-compose-up` — start all services (detached)
- `task docker-compose-stop` — stop without removing volumes
- `task docker-compose-down` — stop + remove containers
- `task docker-compose-postgres` — start only postgres
- `task docker-compose-api` — start only api
- `task docker-compose-logs` — follow logs

### Option C — Full Docker (production-like)

```bash
docker compose up -d          # api + postgres + redis
```

API served at `http://localhost:${API_PORT}`. Run `task precommit-install` from a local uv checkout before committing — hooks run on the host, not inside this container.

## Task Maintenance

- All developer operations go through `Taskfile.yml` — no raw `docker compose` or `uv` commands in docs/scripts.
- Adding a new dev command/workflow requires updating `Taskfile.yml` (with a `desc:`), plus README.md and this file's Commands section, in the same change.

## Architecture

Layers: `routers/` → `services/` → `repositories/` → `models/`, `schemas/`
DB queries in repositories only. Business logic in services only.

## Routers

- Every endpoint must render clearly in Swagger: set `summary` (short) and, when the behavior isn't obvious from the path/method, a docstring — both show up in the OpenAPI UI. Skip both when the path/method already say it (e.g. `GET /books/{book_id}` needs no summary).
- Keep endpoint signatures explicit and typed (path/query params, request/response schemas) — this is what Swagger renders and what test clients rely on to build valid requests.
- Endpoints must stay thin (parse input, call service, return) so they're trivial to exercise in route tests — no business logic or branching in the router itself.
- No duplicated documentation: don't restate what the schema/type already says. Add `Field(description=...)`/`examples=` only for non-obvious fields (formats, units, valid ranges) — not for self-explanatory ones like `id: UUID`.
- Error responses must never be hand-repeated per endpoint, for any status code (401/403/404/409/422/whatever an endpoint can raise). Define each once as a shared `responses` dict per error kind (e.g. `NOT_FOUND_RESPONSE`, `CONFLICT_RESPONSE`, `ADMIN_RESPONSES` in `app/core/errors.py` or `app/routers/responses.py`) and attach it automatically at whatever already carries that behavior, instead of retyping it at each route:
  - Any status tied to a dependency (401/403 from `require_admin`, `require_auth`, etc.) is declared on that dependency's shared `responses` dict once, then merged onto every `APIRouter`/route group that uses `dependencies=[Depends(require_admin)]` — the doc travels with the dependency automatically.
  - Any status tied to a domain error class (`NotFoundError` → 404, `ConflictError` → 409, ...) gets one shared dict per error class, merged into `responses=` only on endpoints whose service path can actually raise it — never re-typed inline.
  - If FastAPI/OpenAPI tooling can generate a status's schema from the exception type automatically, prefer that over any hand-maintained dict.

## Project Structure

```text
app/
  core/         config, db session, errors, auth deps, lifespan (Sentry init)
  models/       SQLModel tables (catalog.py: Book/Release/Contributor + joins; mixins.py: IdMixin, TimestampMixin)
  repositories/ async CRUD, DB queries only (book_repository.py — pattern to follow)
  routers/      FastAPI endpoints, thin (parse input, call service, return)
  schemas/      Pydantic request/response models
  services/     business logic (services/external/ — BookSourceAdapter + OpenLibrary etc.)
```

## Models

- Models with bidirectional `Relationship()`/`back_populates` pairs go in one shared file (e.g. `app/models/catalog.py`), not split one-class-per-file. Splitting forces circular imports resolved via `if TYPE_CHECKING:` + string forward refs — avoid that pattern here. Models with no cross-relationships (e.g. `user.py`, `refresh_token.py`) still get their own file.

## Error Handling

- Domain errors live in `app/core/errors.py`: `AppError` (base, `status_code = 500`) and subclasses `NotFoundError` (404), `ConflictError` (409), `UnauthorizedError` (401), `ExternalServiceError` (502). Each takes a `detail: str` message.
- Services raise these directly (`raise NotFoundError("...")`) instead of `raise HTTPException(...)` or wrapping calls in `try/except Exception`. A single handler in `app/main.py` (`@app.exception_handler(AppError)`) translates any `AppError` to a JSON response — no per-service try/except needed to get an HTTP response.
- Recurring error message strings go in `ErrorMessages` (`app/core/errors.py`), not inline literals, so they aren't duplicated across call sites.
- Never catch bare `except Exception`. Ruff enforces this via `flake8-blind-except` (`BLE` in `[tool.ruff.lint] extend-select`). Catch the narrowest exception type that can actually occur (e.g. `jwt.PyJWTError`, `httpx.HTTPError`, `sqlalchemy.exc.SQLAlchemyError`) and either re-raise as an `AppError` subclass or let it propagate.
- The one sanctioned bare-except is `app/core/db.py::get_session`'s commit/rollback boundary — it must catch anything to roll back the transaction. No `# noqa` needed: ruff's `BLE001` doesn't flag `except Exception` blocks that end in a bare `raise` (pure re-raise, nothing swallowed).
- At the adapter boundary (`app/services/external/`), catch the external library's specific exception (e.g. `httpx.HTTPError`) and re-raise as `ExternalServiceError` — callers in `services/` then don't need their own try/except around adapter calls.

## Release Flow

- Versioning is fully automated via `python-semantic-release` (`[tool.semantic_release]` in `pyproject.toml`), driven by Conventional Commit messages since the last tag — never hand-edit `version` in `pyproject.toml`.
- Bump mapping: `fix:` → patch, `feat:` → minor, `BREAKING CHANGE:`/`!` → major (`major_on_zero = true`, so this applies even pre-1.0), `chore:`/`docs:`/`test:` → no bump.
- `.github/workflows/post-merge.yml` (`post-merge` job, `on: push: branches: [main]`) runs the release step first: bumps the version, creates a `vX.Y.Z` tag, and updates the changelog locally via `semantic-release version --commit --tag --changelog --no-push --no-vcs-release` — a no-op (no commit/tag created) when there are no releasable commits since the last tag, so it's safe to run unconditionally. Since branch protection on `main` blocks direct pushes even from the workflow's own token (required status checks apply regardless of `enforce_admins`), it can't `git push` the bump commit straight to `main`: it pushes the tag directly (tags aren't covered by branch protection), then lands the version-bump commit via a bot branch + auto-merged PR (`--merge`, not `--squash`, so the tagged commit stays reachable in `main`'s history), then publishes the GitHub release against the already-pushed tag. The same job then runs the coverage-badge steps (see Gotchas) — merged into one job so checkout/`setup-uv`/`setup-task`/`task install` run once instead of twice; the `main-push-writes` concurrency group is kept to prevent overlapping runs of this workflow itself.
- The `release` job in `.github/workflows/ci.yml` (`workflow_dispatch`, gated to `main`, after the `ci` job passes) still exists for an on-demand manual re-run/troubleshooting — normally unused now that `post-merge.yml` covers every merge.
- `HealthService.get_version()` (`app/services/health_service.py`) resolves the running version via `importlib.metadata.version("bookworm-hole-api")`, falling back to `"unknown"` if package metadata isn't installed — never hardcode it. Used by `check_overall()` and by `GET /health/version`.

## Error Tracking (Sentry)

- `SentrySettings` (`app/core/config.py`, `env_prefix="SENTRY_"`): `dsn`, `traces_sample_rate`, `profiles_sample_rate`. `dsn` unset (default) → Sentry stays disabled, no-op, no external calls — safe default for local dev/test.
- `sentry_sdk.init(...)` is called from `app/core/lifespan.py` startup, guarded by `if sentry_settings.dsn`. `send_default_pii` is always `False` — never send emails/tokens/PII to Sentry.
- To enable locally: set `SENTRY_DSN` in `.env` (see `.env.example`).

## Catalog Imports

- Bulk catalog growth (populating books/comics/manga from external sources) runs on an `arq` (async, Redis-backed) background worker — not Celery, since the whole stack (SQLAlchemy, httpx adapters) is already async and arq avoids a sync/async bridge. `RedisSettings` (`app/core/config.py`, `env_prefix="REDIS_"`) points at the same Redis instance already provisioned for dev/docker-compose (`redis` service, previously unused by app code).
- `app/core/redis.py` holds a module-level `ArqRedis` pool (same pattern as `async_engine` in `app/core/db.py`), initialized/closed from `app/core/lifespan.py`'s `lifespan()`.
- `app/worker/settings.py::WorkerSettings` is the `arq` CLI entrypoint (`task worker` runs `arq app.worker.settings.WorkerSettings`). `app/worker/tasks.py::import_catalog_profile(ctx, profile_name)` opens its own `AsyncSession` (workers run outside FastAPI's request-scoped `get_session`), runs `CatalogImportService.run_profile`, and commits once at the end.
- `app/services/catalog_import_profiles.py` defines fixed, curated `CatalogImportProfile`s (`books` target 1000, `comics` target 100, `manga` target 100) as lists of `subject:`-scoped search queries (Google Books search operator) — deliberately narrow/curated rather than an unbounded crawl, so imports stay on-topic per profile.
- `app/services/catalog_import_service.py::CatalogImportService.run_profile` composes the existing `ExternalSearchService` (multi-source search + dedup) and `ImportService` (single-book import by `source`/`source_id`, already used by `POST /external/import`) — no new import logic, just orchestration + a target-count stop condition. "Imported" count is measured as the net new `Book` row count before/after the run (existing services don't report created-vs-matched), checked once per query (not per hit), so a batch can slightly overshoot the target.
- Manual trigger only, by design — no `cron_jobs` are registered on `WorkerSettings`. `POST /admin/catalog-imports` (`require_admin`) enqueues `import_catalog_profile` and returns a job id; `GET /admin/catalog-imports/{job_id}` reads status/result straight from `arq`'s `Job` (via the same Redis pool) — no DB table for job tracking.
- Real-world query yield is capped by each adapter's single unpaginated request (Google Books' unauthenticated default page size, no `startIndex`) and its free-tier rate limit — profiles are a best-effort ceiling, not a guarantee; re-running a profile (idempotent, dedups by ISBN/title like all `ImportService` calls) is the intended way to top up the catalog over time.

## Gotchas

- pyright `include = ["app", "scripts"]` required — omitting causes .venv scan (8600 errors)
- pyright runs `typeCheckingMode = "strict"` — new code must pass strict with no `# type: ignore`
- SQLModel needs `reportIncompatibleVariableOverride = "none"` + `reportAssignmentType = "none"`
- `pyjwt` is installed as `pyjwt[crypto]` — without the `cryptography` extra, pyright can't resolve `AllowedPrivateKeys`/`AllowedPublicKeys` and flags `jwt.encode`/`jwt.decode` as partially unknown even though the app only uses HS256
- `alembic/` excluded from pyright (uses sqlmodel internals not in stubs)
- `.claude/` is gitignored — skills live locally only
- Inside devcontainer: `.venv` is an anonymous volume; host `.venv` not mounted (prevents arch mismatch)
- `POSTGRES_HOST` overridden to `postgres` in devcontainer/docker-compose (not `localhost`)
- `.pre-commit-config.yaml` hooks call `task format`/`task lint` (not raw `ruff`/`pyright`) per Task Maintenance rule; format-only hooks (json/yaml/toml/md/whitespace) use the standard `pre-commit-hooks`/`mdformat`/`taplo-pre-commit`/`yamllint` repos directly
- `taplo.toml` pins TOML formatting to 4-space indent (taplo's default is 2-space) — keep in sync if repo indent convention changes; `taplo-lint` runs with `--no-schema` since CI has no network access to the online schema catalog
- `yamllint` config (inline in `.pre-commit-config.yaml`) disables `document-start`/`truthy`/`line-length` and relaxes `comments` spacing to 1 — matches this repo's existing YAML style (no `---` headers, bare `on:` in GH workflows) rather than rewriting every file
- No YAML auto-formatter hook (deliberately) — `google/yamlfmt`'s pre-commit hook is `language: golang`, meaning every cache-miss rebuilds it from source via a Go toolchain, dwarfing every other hook's runtime. `yamllint` (pure Python, fast) covers style; format YAML by hand
- `.github/workflows/ci.yml` triggers on `pull_request` (not `push`), single job `ci`, so lint/test/precommit run once per PR commit and never again on the merge to `main` — avoids rerunning the whole suite (and re-surfacing flaky/env-only failures) on a commit already validated on the PR branch. Lint, precommit (formatting hooks only — skips `task-format`/`task-lint` since the lint step already covers ruff/pyright), and test run as sequential steps in one job (not parallel jobs) so checkout/`setup-uv`/`setup-task`/`task install` run once instead of three times — trades wall-clock (steps are now `sum()` not `max()`) for fewer billed runner-minutes
- `.github/workflows/post-merge.yml` (`post-merge` job, `on: push: branches: [main]`) runs the coverage-badge steps after the release steps (see Release Flow), in the same job. It does not rerun tests: the PR's `ci` job uploads its `.coverage` file as the `coverage-data` artifact, and this workflow resolves the just-merged PR (`gh api commits/{sha}/pulls`), finds that PR's successful `ci.yml` run, downloads its `coverage-data` artifact, then runs `task coverage-badge`/`coverage-update-baseline`. It can't push straight to `main` (branch protection blocks that even for this workflow's own token), so it lands the badge/baseline update via a bot branch + auto-merged PR instead. Falls back to actually running the tests (spinning up postgres via `docker run`) if the PR/run lookup or artifact download fails. Not part of branch protection's required checks itself, so its job name/status doesn't gate merges or duplicate the PR's `ci` check
- `.coverage-baseline` is a coverage-percentage ratchet, not a fixed floor: PR's `ci` job runs `task coverage-check` and fails if the current run's total coverage (`coverage report --format=total`) drops below the committed value; `post-merge.yml` auto-advances the baseline upward (never down) alongside `coverage.svg` in the same auto-commit after merge to `main`. `[tool.coverage.report] fail_under = 90` in `pyproject.toml` is the separate absolute floor underneath the ratchet
- Repo is public; branch protection on `main` requires the `ci` status check (single job now, was `lint`/`test`/`precommit`) and blocks force-push/deletion — a failing check now blocks the merge button (previously informational-only while the repo was private on the free plan). **Required status checks in the GitHub repo settings must be updated to `ci` after this change** — they still reference the old `lint`/`test`/`precommit` job names and won't be satisfied by the merged job until updated
- `coverage-badge` (PyPI package) imports `pkg_resources`, which Python 3.14 doesn't bundle by default — `setuptools` is pinned as a dev dependency in `pyproject.toml` solely to provide it; removing `setuptools` breaks `task coverage-badge` with `ModuleNotFoundError: No module named 'pkg_resources'`
- `.deepsource.toml` Python analyzer config mirrors the ruff/pyright rule set above — keep them in sync when either changes

## Testing

- pytest-asyncio `asyncio_mode = "auto"`, testpaths = `tests/`
- Route tests: `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`
- `tests/conftest.py` — shared `async_client` fixture (no DB override; for pure HTTP tests)
- For tests needing DB: override `get_session` in the test file via `app.dependency_overrides[get_session] = async_generator_fn`
- Group tests in classes (e.g. `class TestCreateBook:`), one class per endpoint/unit under test.
- Cover all cases: success paths + all error paths (validation, not-found, conflict, etc).
- Assert all relevant response/model attributes, not just status code.
- Partial-update (`PATCH`) endpoints: parametrized test per field of the Update schema, asserting both the changed field and that every other field stayed at its original value (catches the update method overwriting unset fields with `None`).
- Tests must be fast and simple — minimal setup, no unnecessary work.
- Structure each test Arrange-Act-Assert, but don't label the sections with comments.
- Write tests to be easy to read and understand at a glance.
- Cover every variable/argument combination that matters, not just the happy path.
- Cover the success path and every error path.
- Cover all possible execution branches.
- Prefer fakes over mocks — cheaper to run, closer to real behavior.

## Code Style

- Keep code simple. Avoid over-engineering.
- Comments: rare, only when non-obvious.
- Files: small, well-structured. Split big files into smaller ones.
- Avoid `# type: ignore`. Allowed only in rare cases.
- No inline `# noqa` / `# pyright: ignore` suppression comments. If a lint/type rule is a real false positive, fix the root cause structurally (e.g. a shared typed helper — see `app/repositories/loading.py::eager`/`eager_nested` for the SQLModel `selectinload()` + pyright mismatch) instead of silencing it at each call site.
- Use type hints everywhere: function args, return types, variables.
- Don't pass a value equal to a parameter's default — omit the argument instead (applies to function calls, `Field(...)`, decorators, config kwargs, etc).
- Partial-update repository methods (`update(id, data)`) take the Pydantic Update schema (e.g. `UpdateBookSchema`) directly, not `dict`/`dict[str, Any]`. Call `data.model_dump(exclude_unset=True)` then `model.sqlmodel_update(...)` inside the repository method — keeps partial-update semantics (unset fields untouched) while the signature still says what shape the data is. See `app/repositories/book_repository.py::update`.

## Git

- Commit messages: one line only, no body. Conventional Commits format: `<type>(<scope>): <description>`
