
FROM python:3.14-bookworm

WORKDIR /code

# Install uv and uvx from Astral's UV image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY ./pyproject.toml /code/pyproject.toml
COPY ./uv.lock /code/uv.lock

RUN uv sync --locked

COPY ./app /code/app

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
