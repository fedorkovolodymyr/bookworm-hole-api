# ── builder ────────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /code

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY ./app ./app
RUN uv sync --frozen --no-dev

# ── runtime ────────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

WORKDIR /code

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=builder /code/.venv /code/.venv
COPY --from=builder /code/app /code/app
COPY --from=builder /code/pyproject.toml /code/pyproject.toml
COPY --from=builder /code/uv.lock /code/uv.lock

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
