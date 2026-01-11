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

### Docker
- up: `task docker-compose-up` (add `--` for extra flags, e.g. `task docker-compose-up -- -d`)
- down: `task docker-compose-down`
- build: `task docker-compose-build`
- logs: `task docker-compose-logs` (live, with -f)

### .env file
Create a `.env` file (or copy from `.env.example`) and set the required variables.

### Code quality
- format: `task format-code` / `task format-imports` / `task format` (all)
- format + fix: `task format-fix` (auto-fix linting issues)
- lint: `task lint-ruff` / `task lint-types` / `task lint` (all)
- lint + format: `task lint-format` (formats and auto-fixes everything)
