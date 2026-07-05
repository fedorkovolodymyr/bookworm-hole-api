# bookworm-hole-api

FastAPI + SQLModel + asyncpg backend. See [CLAUDE.md](CLAUDE.md) for architecture, code style, and dev-environment options (dev container / local + docker / full docker).

## Task runner

Install Task (one-time): `brew install go-task/tap/go-task`
Install uv (one-time): follow <https://github.com/astral-sh/uv#installation>

All developer operations go through `task` — don't run raw `docker compose` or `uv` commands directly. Run `task --list` to see every task with its description.

### Getting started

```bash
cp .env.example .env   # once
task up                 # build + start api, postgres, redis via docker compose
task migrate            # apply Alembic migrations, inside the api container
task seed                # load dev seed data
task precommit-install   # required: installs git pre-commit hooks
```

API served at `http://localhost:${API_PORT}`.

### Local development (no full container rebuild per change)

```bash
task docker-compose-postgres  # start only postgres (+ redis if needed)
task alembic-upgrade          # apply migrations locally via uv
task dev                      # run FastAPI locally with --reload
```

### Container-based tasks

Run against the containers started by `task up` (uses `docker compose exec`, so changes are picked up live via the bind-mounted `./app` and `./scripts`):

- `task shell` — interactive shell in the api container
- `task test-container` — pytest inside the api container
- `task lint-container` / `task format-container` — ruff inside the api container
- `task migrate` — apply Alembic migrations to head
- `task migrate:new -- "message"` — generate a new Alembic migration
- `task seed` — load dev seed data
- `task seed:test` — load fixtures into the test database (`bookwormhole_test`)
- `task psql` — open a psql shell against the dev database
- `task refresh-metadata` — manually refresh stale release metadata from external sources
- `task down` — stop and remove the stack

### Local (uv-based) tasks

Used inside the dev container or a local venv (see [CLAUDE.md](CLAUDE.md) for setup):

- `task install` — install dependencies
- `task dev` — run FastAPI locally with `--reload`
- `task format` — ruff import sort + format
- `task lint` — ruff check + pyright
- `task lint-format` — run format then lint in sequence
- `task type-check` — pyright only
- `task test` — pytest, against an isolated `*_test` database (auto-created/migrated), with coverage report
- `task precommit-install` — install git pre-commit hooks (required first-time setup)
- `task precommit` — run all pre-commit hooks against every file
- `task alembic-revision -- "message"` / `task alembic-upgrade` — migrations via local uv
- `task alembic-downgrade` — rollback last migration
- `task release-dry-run` — preview the next version bump without making changes
- `task release` — bump version, tag, and publish a GitHub release (CI-only, see below)

**⚠️ Important**: Always run migrations after pulling changes or before starting the app.

### Docker compose (services only)

- postgres only: `task docker-compose-postgres`
- api only: `task docker-compose-api`
- all services: `task docker-compose-up`
- stop: `task docker-compose-stop` / down: `task docker-compose-down`
- logs: `task docker-compose-logs` (live, with `-f`)

### Environment configuration

Copy `.env.example` to `.env` (single file, used both locally and by docker compose). `POSTGRES_HOST`/`REDIS_HOST` are overridden to `postgres`/`redis` automatically inside docker compose — no separate `.env.docker` needed.

### Release flow

Versioning is automated via `python-semantic-release`, driven entirely by Conventional Commit messages — never edit `version` in `pyproject.toml` by hand. Bump mapping: `fix:` → patch, `feat:` → minor, `BREAKING CHANGE:`/`!` → major, `chore:`/`docs:`/`test:` → no bump.

The `release` job in `.github/workflows/ci.yml` is manually triggered (`workflow_dispatch`, `main` branch only) and runs after the `ci` job passes. It bumps `pyproject.toml`, creates a `vX.Y.Z` git tag, and publishes a GitHub release with a changelog from commit messages. Run `task release-dry-run` locally to preview the next version before triggering a release.

### Error tracking (Sentry)

Set `SENTRY_DSN` in `.env` to enable Sentry. Leave it blank to disable (default in local dev — no-op, no external calls). See CLAUDE.md for details.
