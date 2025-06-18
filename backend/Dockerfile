# Dockerfile (put at project root)

# 1. Base image
FROM python:3.11-slim

# 2. Prevents Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# 3. Set working dir
WORKDIR /app

# 4. Install system deps (if needed) and Python deps
#    adjust libpq-dev if you need PostgreSQL client headers for psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy and install Python requirements
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 6. Copy application code
COPY . .

# 7. Default command (for backend)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
