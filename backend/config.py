"""
Configuration module for MAESTRO Experiment Bench backend.
Centralizes environment variable loading and provides default values.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# MAESTRO Configuration
MAESTRO_API_BASE_URL = os.getenv(
    "MAESTRO_API_BASE_URL", "http://host.docker.internal:8001"
)

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# CORS Configuration — comma-separated list of allowed origins
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
