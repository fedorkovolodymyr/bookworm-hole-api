# ── builder ────────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /code

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY ./app ./app
COPY ./scripts ./scripts
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev

# ── runtime ────────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

WORKDIR /code

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=builder /code/.venv /code/.venv
COPY --from=builder /code/app /code/app
COPY --from=builder /code/scripts /code/scripts
COPY --from=builder /code/alembic /code/alembic
COPY --from=builder /code/alembic.ini /code/alembic.ini
COPY --from=builder /code/pyproject.toml /code/pyproject.toml
COPY --from=builder /code/uv.lock /code/uv.lock
COPY ./docker-entrypoint.sh /code/docker-entrypoint.sh
RUN chmod +x /code/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/code/docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
