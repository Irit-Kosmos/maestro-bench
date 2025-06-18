#!/usr/bin/env python3
"""
Migration script to clean up the database schema and migrate to the simplified model
"""

from sqlmodel import SQLModel, text
from db import engine
import os

def migrate_database():
    """Drop old tables and recreate with new schema"""
    print("🔄 Starting database migration...")
    
    # Connect to database
    with engine.connect() as conn:
        # Drop old tables in proper order (respecting foreign key constraints)
        tables_to_drop = [
            "experimentagentconfig",
            "experimentagentteamconfig", 
            "agentconfig",
            "experiment",
            "agent",
            "agentteam",
            "dataset"
        ]
        
        print("🗑️  Dropping old tables...")
        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"   ✓ Dropped table: {table}")
            except Exception as e:
                print(f"   ⚠️  Could not drop table {table}: {e}")
        
        conn.commit()
    
    # Create new tables
    print("🆕 Creating new tables...")
    SQLModel.metadata.create_all(engine)
    print("   ✓ All tables created successfully!")
    
    # Backup old database file if it exists
    db_file = "backend/app.db"
    if os.path.exists(db_file):
        backup_file = f"{db_file}.backup"
        try:
            import shutil
            shutil.copy2(db_file, backup_file)
            print(f"   ✓ Backup created: {backup_file}")
        except Exception as e:
            print(f"   ⚠️  Could not create backup: {e}")
    
    print("✅ Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
