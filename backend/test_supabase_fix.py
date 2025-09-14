#!/usr/bin/env python3
"""
Test script to verify Supabase RLS fix
"""
import asyncio
from app.db.base import get_supabase_client, get_supabase_service_client
from app.config import settings

async def test_supabase_connection():
    """Test both client types"""
    print("Testing Supabase connections...")

    # Test anon client
    try:
        anon_client = get_supabase_client()
        print("✓ Anon client initialized")

        # Try to read users (should work with anon key for SELECT)
        result = anon_client.table("users").select("count", count="exact").execute()
        print(f"✓ Anon client can read users table (count: {result.count})")
    except Exception as e:
        print(f"✗ Anon client error: {e}")

    # Test service client
    try:
        service_client = get_supabase_service_client()
        key_type = "service role" if settings.supabase_service_role_key else "anon (fallback)"
        print(f"✓ Service client initialized (using {key_type} key)")

        # Try to read users
        result = service_client.table("users").select("count", count="exact").execute()
        print(f"✓ Service client can read users table (count: {result.count})")

        # Check if we're using the actual service role key
        if not settings.supabase_service_role_key:
            print("\n⚠️  WARNING: No service role key configured!")
            print("   The system is falling back to anon key which cannot bypass RLS.")
            print("   To fix user creation, add SUPABASE_SERVICE_ROLE_KEY to your .env file")
    except Exception as e:
        print(f"✗ Service client error: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase_connection())