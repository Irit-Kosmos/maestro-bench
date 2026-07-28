# Python 3.13 slim with uv preinstalled
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no editable install needed for flat app)
RUN uv sync --no-dev --frozen

# Copy application code
COPY . .

# Create a non-root user
RUN useradd --create-home --shell /bin/sh maestro \
    && chown -R maestro:maestro /app

USER maestro

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
