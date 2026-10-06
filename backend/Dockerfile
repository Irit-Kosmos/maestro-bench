# Python 3.13 slim with uv preinstalled
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# One folder per workspace with its datasets and execution results; mount a
# volume here to keep them
ENV DATA_DIR=/data

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no editable install needed for flat app)
RUN uv sync --no-dev --frozen

# Copy application code
COPY . .

# Create a non-root user
RUN useradd --create-home --shell /bin/sh maestro \
    && mkdir -p /data \
    && chown -R maestro:maestro /app /data

USER maestro

EXPOSE 8000

# Healthy once the API answers and so does the database
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"API_PORT\", \"8000\")}/health', timeout=4)"

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
