FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first: this layer is cached until pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Then the project itself. README.md is needed because pyproject.toml declares it.
COPY README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN uv sync --locked --no-dev

RUN useradd --system --no-create-home app
USER app

EXPOSE 8000
CMD ["uvicorn", "tally_chat_logger.app:app", "--host", "0.0.0.0", "--port", "8000"]
