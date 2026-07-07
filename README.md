# bookworm-hole-api

[![CI](https://github.com/fedorkovolodymyr/bookworm-hole-api/actions/workflows/ci.yml/badge.svg)](https://github.com/fedorkovolodymyr/bookworm-hole-api/actions/workflows/ci.yml)
![coverage](coverage.svg)

FastAPI + SQLModel + asyncpg backend for Bookworm Hole — a book cataloging and tracking API.

## Quick start

```bash
cp .env.example .env    # once
task up                 # build + start api, postgres, redis via docker compose
task migrate             # apply Alembic migrations
task seed                 # load dev seed data
task precommit-install    # required: installs git pre-commit hooks
```

API served at `http://localhost:${API_PORT}`, Swagger docs at `/docs`.

## Testing

Run `task test` to execute the full test suite with coverage reporting:

```bash
task test                    # full pytest suite with coverage reports (term-missing + xml)
task lint                    # ruff + pyright type checking
task format                  # import sorting + code formatting
task lint-format             # format, then lint
```

The test suite creates an isolated `bookwormhole_test` database automatically, runs migrations, executes all tests, and generates:

- Terminal coverage report (term-missing format)
- `coverage.xml` for CI consumption

Exit codes are non-zero on any failure (test, lint, or type-check), allowing CI/CD pipelines to fail fast.

All developer operations go through `task` — run `task --list` to see every available task. See [CLAUDE.md](CLAUDE.md) for the full command reference, architecture, code style, and alternative dev-environment setups (dev container / local + docker / full docker).

Versioning is automated via `python-semantic-release`, driven by Conventional Commit messages — never edit `version` in `pyproject.toml` by hand. See [CLAUDE.md](CLAUDE.md#release-flow) for the bump mapping and release process.
