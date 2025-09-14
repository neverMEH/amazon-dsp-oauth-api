#!/usr/bin/env python3
"""
Test script to verify authentication and database sync fixes
"""
import asyncio
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.middleware.clerk_auth import get_user_context
from app.services.user_service import UserService
from app.db.base import get_supabase_client


async def test_user_context():
    """Test the get_user_context function with different inputs"""
    print("\n=== Testing get_user_context function ===")

    # Test case 1: With database user ID in user_data
    test_data1 = {
        "sub": "user_32fFuzeSeuB4IHRpjpotMlgywMf",
        "user_id": "52a86382-266b-4004-bfd9-6bd6a64026eb",
        "email": "test@example.com"
    }
    context1 = get_user_context(test_data1)
    print(f"Test 1 - With user_id: user_id={context1.get('user_id')}, clerk_user_id={context1.get('clerk_user_id')}")
    assert context1.get('user_id') == "52a86382-266b-4004-bfd9-6bd6a64026eb", "Database user ID should be preserved"

    # Test case 2: With db_user object
    test_data2 = {
        "sub": "user_32fFuzeSeuB4IHRpjpotMlgywMf",
        "email": "test@example.com",
        "db_user": {
            "id": "52a86382-266b-4004-bfd9-6bd6a64026eb",
            "email": "test@example.com"
        }
    }
    context2 = get_user_context(test_data2)
    print(f"Test 2 - With db_user: user_id={context2.get('user_id')}, clerk_user_id={context2.get('clerk_user_id')}")
    assert context2.get('user_id') == "52a86382-266b-4004-bfd9-6bd6a64026eb", "Database user ID should be extracted from db_user"

    # Test case 3: Without database user ID
    test_data3 = {
        "sub": "user_32fFuzeSeuB4IHRpjpotMlgywMf",
        "email": "test@example.com"
    }
    context3 = get_user_context(test_data3)
    print(f"Test 3 - Without DB ID: user_id={context3.get('user_id')}, clerk_user_id={context3.get('clerk_user_id')}")
    assert context3.get('user_id') is None, "user_id should be None when no database ID is available"

    print("✅ All get_user_context tests passed!")


async def test_database_queries():
    """Test database queries with correct user IDs"""
    print("\n=== Testing Database Queries ===")

    user_service = UserService()
    supabase = get_supabase_client()

    # Test getting user by Clerk ID
    clerk_user_id = "user_32fFuzeSeuB4IHRpjpotMlgywMf"
    print(f"Testing get_user_by_clerk_id with: {clerk_user_id}")

    user = await user_service.get_user_by_clerk_id(clerk_user_id)
    if user:
        print(f"✅ Found user: id={user.id}, email={user.email}")

        # Test user_settings query with database UUID
        print(f"\nTesting user_settings query with database UUID: {user.id}")
        try:
            response = supabase.table("user_settings").select("*").eq("user_id", user.id).maybe_single().execute()
            if response.data:
                print(f"✅ Found user settings for user_id={user.id}")
            else:
                print(f"⚠️ No user settings found for user_id={user.id} (this is OK for new users)")
        except Exception as e:
            print(f"❌ Error querying user_settings: {e}")

        # Test user_accounts query
        print(f"\nTesting user_accounts query with database UUID: {user.id}")
        try:
            response = supabase.table("user_accounts").select("*").eq("user_id", user.id).execute()
            if response.data:
                print(f"✅ Found {len(response.data)} account(s) for user_id={user.id}")
            else:
                print(f"⚠️ No accounts found for user_id={user.id}")
        except Exception as e:
            print(f"❌ Error querying user_accounts: {e}")

        # Test oauth_tokens query
        print(f"\nTesting oauth_tokens query with database UUID: {user.id}")
        try:
            response = supabase.table("oauth_tokens").select("*").eq("user_id", user.id).execute()
            if response.data:
                print(f"✅ Found {len(response.data)} token(s) for user_id={user.id}")
            else:
                print(f"⚠️ No tokens found for user_id={user.id}")
        except Exception as e:
            print(f"❌ Error querying oauth_tokens: {e}")
    else:
        print(f"⚠️ User not found with Clerk ID: {clerk_user_id}")
        print("This might be expected if the user hasn't logged in yet.")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Authentication and Database Sync Fix Verification")
    print("=" * 60)

    await test_user_context()
    await test_database_queries()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())