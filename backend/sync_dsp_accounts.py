#!/usr/bin/env python3
"""
Script to sync DSP accounts and save them to the database
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.account_sync_service import account_sync_service
from app.services.token_service import token_service
from app.db.base import get_supabase_service_client

async def sync_dsp_accounts():
    """Sync DSP accounts and save to database"""
    try:
        # Get tokens
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            print("❌ No OAuth tokens found. Please authenticate first.")
            return

        access_token = tokens["access_token"]
        print(f"✅ Got access token")

        # Get user ID from database - use hardcoded ID we know exists
        db_user_id = "52a86382-266b-4004-bfd9-6bd6a64026eb"
        print(f"✅ Using user ID: {db_user_id}")

        # Fetch all account types
        print("\n📥 Fetching account data from Amazon API...")
        all_data = await account_sync_service._fetch_all_account_types(access_token)

        print(f"  - Advertising accounts: {len(all_data.get('advertising_accounts', []))}")
        print(f"  - DSP advertisers: {len(all_data.get('dsp_advertisers', []))}")
        print(f"  - AMC instances: {len(all_data.get('amc_instances', []))}")

        # Process and save to database
        print("\n💾 Saving to database...")
        result = await account_sync_service._process_all_account_types(
            user_id=db_user_id,
            account_data=all_data
        )

        print(f"\n✅ Sync Results:")
        print(f"  - Created: {result.get('created', 0)} accounts")
        print(f"  - Updated: {result.get('updated', 0)} accounts")
        print(f"  - Failed: {result.get('failed', 0)} accounts")
        print(f"  - Total processed: {result.get('total', 0)} accounts")

        # Check database counts - need to get Supabase client
        supabase = get_supabase_service_client()
        dsp_count = supabase.table("user_accounts").select("id, account_name").eq(
            "user_id", db_user_id
        ).eq("account_type", "dsp").execute()

        advertising_count = supabase.table("user_accounts").select("id").eq(
            "user_id", db_user_id
        ).eq("account_type", "advertising").execute()

        print(f"\n📊 Database Counts After Sync:")
        print(f"  - DSP accounts in database: {len(dsp_count.data) if dsp_count.data else 0}")
        print(f"  - Advertising accounts in database: {len(advertising_count.data) if advertising_count.data else 0}")

        if dsp_count.data:
            print(f"\n🎯 DSP Accounts in Database:")
            for account in dsp_count.data:
                print(f"    - {account['account_name']}")

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Starting DSP Account Sync...")
    result = asyncio.run(sync_dsp_accounts())
    if result:
        print("\n✅ Sync completed successfully!")
    else:
        print("\n❌ Sync failed!")