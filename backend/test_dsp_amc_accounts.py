#!/usr/bin/env python3
"""
Test script to verify DSP and AMC account fetching and storage
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.base import get_supabase_service_client
from app.services.dsp_amc_service import dsp_amc_service
from app.services.account_sync_service import account_sync_service
from app.config import settings
import structlog

logger = structlog.get_logger()


async def test_dsp_amc_accounts():
    """Test fetching and storing DSP and AMC accounts"""

    # Initialize Supabase client - ensure we use service client to bypass RLS
    from app.db.base import get_supabase_service_client
    supabase = get_supabase_service_client()

    print("\n" + "="*80)
    print("DSP & AMC ACCOUNT TESTING")
    print("="*80)

    # Get a test user with valid tokens
    print("\n1. Looking for a user with valid Amazon tokens...")

    token_result = supabase.table("oauth_tokens").select("*").execute()
    if not token_result.data:
        print("❌ No users with tokens found. Please connect an Amazon account first.")
        return

    # Find a token that's not expired
    valid_token = None
    for token in token_result.data:
        expires_at = datetime.fromisoformat(token["expires_at"].replace('Z', '+00:00'))
        if expires_at > datetime.now(timezone.utc):
            valid_token = token
            break

    if not valid_token:
        print("❌ No valid (non-expired) tokens found. Please refresh tokens first.")
        return

    user_id = valid_token["user_id"]
    print(f"✅ Found valid token for user: {user_id}")

    # Decrypt the access token
    from app.services.token_service import token_service
    try:
        access_token = token_service.decrypt_token(valid_token["access_token"])
    except:
        # Token might be stored as plain text (for testing)
        access_token = valid_token["access_token"]

    print("\n2. Testing DSP and AMC API endpoints...")

    # Test fetching all account types
    try:
        print("\n   Fetching all account types (SP, DSP, AMC)...")
        account_data = await dsp_amc_service.list_all_account_types(
            access_token=access_token,
            include_regular=True,
            include_dsp=True,
            include_amc=True
        )

        advertising_count = len(account_data.get("advertising_accounts", []))
        dsp_count = len(account_data.get("dsp_advertisers", []))
        amc_count = len(account_data.get("amc_instances", []))

        print(f"\n   Results:")
        print(f"   ✅ Advertising accounts: {advertising_count}")
        print(f"   {'✅' if dsp_count > 0 else '⚠️'} DSP advertisers: {dsp_count}")
        print(f"   {'✅' if amc_count > 0 else '⚠️'} AMC instances: {amc_count}")

        if dsp_count == 0:
            print("\n   ⚠️ No DSP accounts found. This is normal if the user doesn't have DSP access.")

        if amc_count == 0:
            print("   ⚠️ No AMC instances found. AMC requires special provisioning from Amazon.")

        # Show details of DSP advertisers if found
        if dsp_count > 0:
            print("\n   DSP Advertiser Details:")
            for advertiser in account_data["dsp_advertisers"]:
                print(f"   - {advertiser.get('advertiserName', 'Unknown')}")
                print(f"     ID: {advertiser.get('advertiserId')}")
                print(f"     Type: {advertiser.get('advertiserType')}")
                print(f"     Status: {advertiser.get('advertiserStatus')}")
                print(f"     Country: {advertiser.get('countryCode')}")

        # Show details of AMC instances if found
        if amc_count > 0:
            print("\n   AMC Instance Details:")
            for instance in account_data["amc_instances"]:
                print(f"   - {instance.get('instanceName', 'Unknown')}")
                print(f"     ID: {instance.get('instanceId')}")
                print(f"     Type: {instance.get('instanceType')}")
                print(f"     Status: {instance.get('status')}")
                print(f"     Region: {instance.get('region')}")

    except Exception as e:
        print(f"❌ Error fetching account types: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    print("\n3. Testing account synchronization with new method...")

    try:
        # Test the sync service
        sync_result = await account_sync_service.sync_user_accounts(
            user_id=user_id,
            access_token=access_token,
            force_update=True
        )

        if sync_result["status"] == "success":
            results = sync_result.get("results", {})
            print(f"\n   ✅ Sync completed successfully!")
            print(f"   Total accounts processed: {results.get('total', 0)}")
            print(f"   Created: {results.get('created', 0)}")
            print(f"   Updated: {results.get('updated', 0)}")
            print(f"   Failed: {results.get('failed', 0)}")

            # Show stats by type if available
            stats_by_type = results.get("stats_by_type")
            if stats_by_type:
                print("\n   Stats by Account Type:")
                for account_type, stats in stats_by_type.items():
                    print(f"   - {account_type.upper()}:")
                    print(f"     Created: {stats['created']}")
                    print(f"     Updated: {stats['updated']}")
                    print(f"     Failed: {stats['failed']}")
        else:
            print(f"❌ Sync failed: {sync_result}")
    except Exception as e:
        print(f"❌ Error during sync: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n4. Verifying stored accounts in database...")

    # Check what's actually in the database
    db_accounts = supabase.table("user_accounts").select("*").eq("user_id", user_id).execute()

    if db_accounts.data:
        account_types = {}
        for acc in db_accounts.data:
            acc_type = acc.get("account_type", "unknown")
            account_types[acc_type] = account_types.get(acc_type, 0) + 1

        print(f"\n   Accounts in database for user:")
        for acc_type, count in account_types.items():
            emoji = "✅" if count > 0 else "❌"
            print(f"   {emoji} {acc_type}: {count}")

        # Show details of DSP and AMC accounts
        dsp_accounts = [acc for acc in db_accounts.data if acc.get("account_type") == "dsp"]
        amc_accounts = [acc for acc in db_accounts.data if acc.get("account_type") == "amc"]

        if dsp_accounts:
            print("\n   DSP Accounts in Database:")
            for acc in dsp_accounts:
                print(f"   - {acc.get('account_name')}")
                print(f"     Amazon ID: {acc.get('amazon_account_id')}")
                print(f"     Status: {acc.get('status')}")
                print(f"     Last synced: {acc.get('last_synced_at')}")

        if amc_accounts:
            print("\n   AMC Accounts in Database:")
            for acc in amc_accounts:
                print(f"   - {acc.get('account_name')}")
                print(f"     Amazon ID: {acc.get('amazon_account_id')}")
                print(f"     Status: {acc.get('status')}")
                print(f"     Last synced: {acc.get('last_synced_at')}")
    else:
        print("   ❌ No accounts found in database for this user")

    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)

    # Summary
    print("\n📊 SUMMARY:")
    if dsp_count > 0 or amc_count > 0:
        print("✅ DSP/AMC accounts are being fetched from Amazon API")

        dsp_in_db = len([acc for acc in db_accounts.data if acc.get("account_type") == "dsp"]) if db_accounts.data else 0
        amc_in_db = len([acc for acc in db_accounts.data if acc.get("account_type") == "amc"]) if db_accounts.data else 0

        if dsp_in_db == dsp_count and amc_in_db == amc_count:
            print("✅ All DSP/AMC accounts are properly stored in the database")
        else:
            print(f"⚠️ Mismatch: API returned {dsp_count} DSP and {amc_count} AMC accounts")
            print(f"   but database has {dsp_in_db} DSP and {amc_in_db} AMC accounts")
    else:
        print("ℹ️ No DSP/AMC accounts found - user may not have access to these account types")
        print("   This is normal for standard Amazon Advertising accounts")


if __name__ == "__main__":
    print("\nStarting DSP & AMC Account Test...")
    print("This script will:")
    print("1. Find a user with valid Amazon tokens")
    print("2. Test fetching DSP and AMC accounts from Amazon API")
    print("3. Test the account sync service")
    print("4. Verify accounts are stored correctly in the database")

    asyncio.run(test_dsp_amc_accounts())