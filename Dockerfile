FROM python:3.11-slim

# Install uv for fast, reproducible dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Minimal runtime shared library required by Pillow/GLib decoders
RUN apt-get update -y && \
    apt-get install -qq --no-install-recommends \
      libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Create non-root user and group
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -d /app -s /bin/bash appuser

ENV PYTHONUNBUFFERED=1 \
    CONFIG_FILE=/config/config.ini \
    METER_CONFIG_DIR=/config \
    METER_DATA_DIR=/data

WORKDIR /app

# Install Python dependencies with layer caching directly from uv.lock
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --format requirements-txt | \
    uv pip install --system --no-cache -r - && \
    find /usr/local/lib/python3.11 -name '__pycache__' -exec rm -r {} + 2>/dev/null || true

# Create application directories, populate seed config template, and set ownership
RUN mkdir -p /config /data /app /app/default_config
COPY ./config/ /app/default_config/
RUN chown -R appuser:appuser /config /data /app

# Copy application source code
COPY --chown=appuser:appuser ./src/ /app/

# Switch to non-root user
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/healthcheck')" || exit 1

CMD ["python", "./main.py"]
