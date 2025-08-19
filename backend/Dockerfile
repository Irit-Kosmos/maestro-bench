# Python 3.13 slim with uv preinstalled
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Runtime settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Install into the system Python (container is already isolated)
ENV UV_SYSTEM_PYTHON=1

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with uv (system environment via UV_SYSTEM_PYTHON)
RUN uv pip install -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security (use /bin/sh which exists on slim images)
RUN useradd --create-home --shell /bin/sh maestro \
    && chown -R maestro:maestro /app

USER maestro

# Expose port for the API
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
