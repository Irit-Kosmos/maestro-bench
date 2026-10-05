import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://maestro:maestro@localhost:5432/maestro"
)
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# Root of everything the app stores on disk: datasets live in <DATA_DIR>/datasets
# and execution results in <DATA_DIR>/results. Paths kept in the database are
# relative to the directory of their kind (datasets) or to DATA_DIR (results).
DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).resolve().parent.parent)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
