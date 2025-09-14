#!/usr/bin/env python3
"""
Apply database migration to Supabase
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Print instructions for applying the migration"""
    migration_file = Path(__file__).parent / "migrations" / "003_add_rate_limiting_and_token_refresh.sql"

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)

    print("=" * 80)
    print("📊 Database Migration Instructions")
    print("=" * 80)
    print()
    print("To apply the database migration, follow these steps:")
    print()
    print("Option 1: Supabase Dashboard (Recommended)")
    print("-" * 40)
    print("1. Go to your Supabase project dashboard")
    print("2. Navigate to the SQL Editor")
    print("3. Copy the contents of the migration file:")
    print(f"   {migration_file}")
    print("4. Paste and run the SQL in the editor")
    print()
    print("Option 2: Using psql command line")
    print("-" * 40)

    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')

    if db_url:
        print(f"psql '{db_url}' -f {migration_file}")
    else:
        print("Set DATABASE_URL environment variable, then run:")
        print(f"psql '$DATABASE_URL' -f {migration_file}")

    print()
    print("Option 3: Using Supabase CLI")
    print("-" * 40)
    print(f"supabase db push {migration_file}")
    print()
    print("=" * 80)
    print()

    # Show migration preview
    print("Migration Preview (first 50 lines):")
    print("-" * 40)
    with open(migration_file, 'r') as f:
        lines = f.readlines()[:50]
        for line in lines:
            print(line.rstrip())

    if len(lines) == 50:
        print("... (truncated)")

    print()
    print("=" * 80)
    print("⚠️  Note: The database columns must exist for the token refresh")
    print("    scheduler to work properly. The application will show errors")
    print("    about missing columns until the migration is applied.")
    print("=" * 80)


if __name__ == "__main__":
    main()