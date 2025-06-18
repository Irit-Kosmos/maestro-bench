#!/usr/bin/env python3
"""
Initialize database with the new schema
"""

from db import engine
from models import SQLModel

def create_tables():
    """Create all tables based on the current models"""
    print("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✓ Database tables created successfully!")

if __name__ == "__main__":
    create_tables()
