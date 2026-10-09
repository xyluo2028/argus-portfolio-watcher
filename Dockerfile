# Argus in one container: the built web UI + `argus serve` (one worker by design).
# Build:  docker compose up -d --build      Data: the /data volume.

FROM node:22-slim AS ui
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY backend/ backend/
RUN uv sync --frozen --no-dev
COPY --from=ui /src/frontend/dist frontend/dist

RUN useradd --create-home --uid 10001 argus && mkdir /data && chown argus /data
USER argus
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ARGUS_DATA_DIR=/data \
    ARGUS_HOST=0.0.0.0
VOLUME /data
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/health', timeout=4)"
CMD ["argus", "serve"]
