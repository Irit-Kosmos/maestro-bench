"""
Configuration module for MAESTRO Experiment Bench backend.
Centralizes environment variable loading and provides default values.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Frontend Configuration
MAESTRO_API_BASE_URL = os.getenv("MAESTRO_API_BASE_URL", "http://localhost:3000")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Database Configuration (for future use)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
