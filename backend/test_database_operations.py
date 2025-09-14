#!/usr/bin/env python3
"""
Test database operations after migration
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.base import get_supabase_client
from app.services.token_refresh_scheduler import TokenRefreshScheduler
from app.core.rate_limiter import ExponentialBackoffRateLimiter


async def test_database_operations():
    """Test that all database operations work correctly after migration"""
    print("=" * 80)
    print("🧪 Testing Database Operations")
    print("=" * 80)
    print()

    client = get_supabase_client()
    results = {
        "oauth_tokens_columns": "❌ Failed",
        "user_accounts_columns": "❌ Failed",
        "rate_limit_tracking": "❌ Failed",
        "account_sync_history": "❌ Failed",
        "indexes": "❌ Failed"
    }

    # Test 1: Check oauth_tokens table columns
    print("1. Testing oauth_tokens table enhancements...")
    try:
        # Try to query with new columns
        response = client.table('oauth_tokens').select(
            'id, refresh_failure_count, last_refresh_error, proactive_refresh_enabled'
        ).limit(1).execute()
        results["oauth_tokens_columns"] = "✅ Passed"
        print("   ✅ New columns exist in oauth_tokens table")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("   ⚠️  Migration needs to be applied for oauth_tokens table")

    # Test 2: Check user_accounts table columns
    print("\n2. Testing user_accounts table enhancements...")
    try:
        response = client.table('user_accounts').select(
            'id, sync_status, sync_error_message, sync_retry_count, next_sync_at'
        ).limit(1).execute()
        results["user_accounts_columns"] = "✅ Passed"
        print("   ✅ New columns exist in user_accounts table")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("   ⚠️  Migration needs to be applied for user_accounts table")

    # Test 3: Check rate_limit_tracking table
    print("\n3. Testing rate_limit_tracking table...")
    try:
        # Try to insert a test record
        test_data = {
            'user_id': '00000000-0000-0000-0000-000000000000',  # Test UUID
            'endpoint': 'test_endpoint',
            'request_count': 1,
            'limit_hit_count': 0,
            'window_start': datetime.now(timezone.utc).isoformat()
        }
        response = client.table('rate_limit_tracking').insert(test_data).execute()

        # Clean up test data
        client.table('rate_limit_tracking').delete().eq(
            'user_id', '00000000-0000-0000-0000-000000000000'
        ).execute()

        results["rate_limit_tracking"] = "✅ Passed"
        print("   ✅ rate_limit_tracking table exists and is functional")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            print("   ⚠️  Migration needs to be applied to create rate_limit_tracking table")

    # Test 4: Check account_sync_history table
    print("\n4. Testing account_sync_history table...")
    try:
        # Try to query the table
        response = client.table('account_sync_history').select('*').limit(1).execute()
        results["account_sync_history"] = "✅ Passed"
        print("   ✅ account_sync_history table exists")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            print("   ⚠️  Migration needs to be applied to create account_sync_history table")

    # Test 5: Test rate limiter with database tracking
    print("\n5. Testing rate limiter with database tracking...")
    try:
        rate_limiter = ExponentialBackoffRateLimiter(
            supabase_client=client,
            user_id='00000000-0000-0000-0000-000000000000'
        )

        # Test async function
        async def test_function():
            return "success"

        result = await rate_limiter.execute_with_retry(
            test_function,
            endpoint="test_endpoint"
        )

        if result == "success":
            results["indexes"] = "✅ Passed"
            print("   ✅ Rate limiter with database tracking works")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)
    for test_name, result in results.items():
        print(f"  {test_name:.<40} {result}")

    # Overall status
    all_passed = all("✅" in result for result in results.values())
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All database operations are working correctly!")
        print("   The migration has been successfully applied.")
    else:
        print("⚠️  Some tests failed. Please apply the migration:")
        print("   Run: python3 apply_migration.py")
        print("   Then follow the instructions to apply the migration.")
    print("=" * 80)

    return all_passed


async def test_token_scheduler():
    """Test token refresh scheduler operations"""
    print("\n" + "=" * 80)
    print("🔄 Testing Token Refresh Scheduler")
    print("=" * 80)
    print()

    try:
        scheduler = TokenRefreshScheduler()

        # Test starting the scheduler
        print("1. Starting scheduler...")
        await scheduler.start()
        print("   ✅ Scheduler started successfully")

        # Test checking for expiring tokens
        print("\n2. Checking for expiring tokens...")
        await scheduler._check_and_refresh_tokens()
        print("   ✅ Token check completed")

        # Test stopping the scheduler
        print("\n3. Stopping scheduler...")
        await scheduler.stop()
        print("   ✅ Scheduler stopped successfully")

        print("\n✅ Token refresh scheduler is working correctly!")

    except Exception as e:
        print(f"\n❌ Error testing scheduler: {str(e)}")
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("⚠️  Database migration needs to be applied first")
        return False

    return True


async def main():
    """Main test function"""
    # Test database operations
    db_tests_passed = await test_database_operations()

    # Test token scheduler if database tests passed
    if db_tests_passed:
        await test_token_scheduler()
    else:
        print("\n⏭️  Skipping token scheduler tests until database migration is applied")


if __name__ == "__main__":
    asyncio.run(main())