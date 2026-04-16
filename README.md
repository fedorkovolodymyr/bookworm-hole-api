# bookworm-hole-api

## Task runner

Install Task (one-time): `brew install go-task/tap/go-task`
Install uv (one-time): follow <https://github.com/astral-sh/uv#installation>

Common commands:
- install deps: `task install` (additional flags via `--`, e.g.: `task install -- --dev`)
- dev run: `task dev` (FastAPI with --reload)
- add/remove pkg: `task add PKG=fastapi` / `task remove PKG=fastapi`
- update/lock: `task update` / `task lock`
- arbitrary run: `task run CMD="python -m app" ARGS="--debug"` (alias `exec`)
- clean env/lock: `task clean`

### Getting Started

1. **Setup PostgreSQL**:
   ```bash
   task docker-compose-postgres  # Start PostgreSQL in Docker
   ```

2. **Run database migrations**:
   ```bash
   task alembic-upgrade -- head   # Apply all migrations
   ```

3. **Start development server**:
   ```bash
   task dev                       # Start API locally
   ```

### Database Migrations (Alembic)
- create migration: `task alembic-revision -- "add users table"`
- apply migrations: `task alembic-upgrade` (all)
- rollback: `task alembic-downgrade` (one back)
- check status: `task alembic -- current`
- view history: `task alembic -- history`

**⚠️ Important**: Always run migrations after pulling changes or before starting the app!

### Docker
- postgres only: `task docker-compose-postgres` (for local API development)
- all services: `task docker-compose-up`
- down: `task docker-compose-down`
- logs: `task docker-compose-logs` (live, with -f)

### Environment Configuration
- **Local development**: copy `.env.example` to `.env.local` and set `POSTGRES_HOST=localhost`
- **Docker**: uses `.env.docker` automatically (set `POSTGRES_HOST=postgres`)
- See [SETUP.md](SETUP.md) for detailed configuration guide

### Code quality
- format: `task format-code` / `task format-imports` / `task format` (all)
- format + fix: `task format-fix` (auto-fix linting issues)
- lint: `task lint-ruff` / `task lint-types` / `task lint` (all)
- lint + format: `task lint-format` (formats and auto-fixes everything)
