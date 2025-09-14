#!/usr/bin/env python3
"""
Run database migrations for the Amazon DSP OAuth API
"""
import os
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import get_supabase_client


def run_migrations():
    """Run all SQL migrations in order"""
    print("=" * 60)
    print("Running Database Migrations")
    print("=" * 60)

    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted([f for f in migrations_dir.glob("*.sql") if not "rollback" in f.name])

    if not migration_files:
        print("No migration files found!")
        return

    # Get Supabase client
    client = get_supabase_client()

    for migration_file in migration_files:
        print(f"\n📝 Running migration: {migration_file.name}")

        try:
            with open(migration_file, 'r') as f:
                sql = f.read()

            # Note: Supabase Python client doesn't have direct SQL execution
            # We need to use the REST API directly or use psycopg2
            print(f"⚠️  Migration {migration_file.name} needs to be run manually via Supabase dashboard or psql")
            print(f"   SQL file location: {migration_file}")

        except Exception as e:
            print(f"❌ Error reading migration {migration_file.name}: {e}")

    print("\n" + "=" * 60)
    print("Migration Instructions:")
    print("=" * 60)
    print("1. Go to your Supabase project dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Run each migration file in order:")
    for migration_file in migration_files:
        print(f"   - {migration_file.name}")
    print("\nAlternatively, use psql or another PostgreSQL client to run the migrations.")


if __name__ == "__main__":
    run_migrations()