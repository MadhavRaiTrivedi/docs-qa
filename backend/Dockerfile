FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/ src/
RUN uv sync --locked --no-dev --no-editable

# One image runs the API, the ingestion worker and the migrations; compose picks the command.
FROM python:3.13-slim AS runtime
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations/ migrations/
COPY eval/ eval/
COPY samples/ samples/
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8080
CMD ["uvicorn", "docs_qa.main:app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
