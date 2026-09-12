# ==========================================
# Stage 1: Build & dependency resolution
# ==========================================
FROM python:3.11-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install binutils for stripping .so binaries
RUN apt-get update -y && \
    apt-get install -qq --no-install-recommends binutils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install only production dependencies into virtual environment
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Strip debug symbols from C-extensions and remove bytecode/tests from site-packages
RUN find /app/.venv -name '*.so*' -exec strip --strip-unneeded {} + 2>/dev/null || true && \
    find /app/.venv -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name 'testing' -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -name '*.pyi' -delete 2>/dev/null || true

# ==========================================
# Stage 2: Clean, minimal runtime image
# ==========================================
FROM python:3.11-slim AS runtime

# Create non-root user and group
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -d /app -s /bin/bash appuser

ENV PYTHONUNBUFFERED=1 \
    CONFIG_FILE=/config/config.ini \
    METER_CONFIG_DIR=/config \
    METER_DATA_DIR=/data \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create application directories and set ownership before copying virtualenv
RUN mkdir -p /config /data /app /app/default_config && \
    chown -R appuser:appuser /config /data /app

# Copy stripped virtualenv directly with appuser ownership (avoids duplicate layer)
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy default config template and source code with appuser ownership
COPY --chown=appuser:appuser ./config/ /app/default_config/
COPY --chown=appuser:appuser ./src/ /app/

# Switch to non-root user
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/healthcheck')" || exit 1

CMD ["python", "./main.py"]
