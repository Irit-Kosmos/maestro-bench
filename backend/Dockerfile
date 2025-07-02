# Use Python 3.13 slim image for better performance
FROM python:3.13-slim

# Prevents Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Memory optimization environment variables
ENV PYTHONHASHSEED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash maestro \
    && chown -R maestro:maestro /app

USER maestro

# Expose port for the API
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
