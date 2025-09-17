#!/usr/bin/env python3
"""
Test the fixed DSP advertisers retrieval
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.dsp_amc_service import dsp_amc_service
from app.services.account_service import account_service
from app.db.base import get_supabase_service_client
import structlog

logger = structlog.get_logger()


async def test_dsp_advertisers():
    """Test DSP advertisers retrieval with fixed implementation"""

    print("=" * 80)
    print("Testing Fixed DSP Advertisers Retrieval")
    print("=" * 80)

    # Get Supabase client
    supabase = get_supabase_service_client()

    # Get a user with valid tokens
    users_response = supabase.table("oauth_tokens").select("*").limit(1).execute()
    if not users_response.data:
        print("❌ No users with tokens found")
        return

    token_data = users_response.data[0]
    user_id = token_data.get("user_id", "unknown")

    # Check available fields
    print(f"   Available fields: {list(token_data.keys())}")

    # Tokens in this table are NOT encrypted, they're plain text
    access_token = token_data.get("access_token")

    if not access_token:
        print("   ❌ No access token found")
        return

    print(f"\n📝 Testing with user: {user_id[:8] if user_id else 'unknown'}...")

    # Test 1: Get profiles first
    print("\n🔍 Step 1: Getting profiles...")
    try:
        profiles_response = await account_service.list_profiles(access_token)

        # Handle response format
        if isinstance(profiles_response, list):
            profiles = profiles_response
        elif isinstance(profiles_response, dict):
            profiles = profiles_response.get("profiles", [])
        else:
            profiles = []

        print(f"   ✅ Found {len(profiles)} profiles")

        for profile in profiles[:3]:  # Show first 3
            print(f"      - Profile ID: {profile.get('profileId')}, Country: {profile.get('countryCode')}")

    except Exception as e:
        print(f"   ❌ Error getting profiles: {str(e)}")
        return

    # Test 2: Get DSP advertisers using new method
    print("\n🔍 Step 2: Getting DSP advertisers for each profile...")

    if not profiles:
        print("   ⚠️  No profiles available to test DSP advertisers")
        return

    total_advertisers = 0
    for profile in profiles[:2]:  # Test with first 2 profiles only
        profile_id = str(profile.get("profileId"))
        print(f"\n   Testing Profile {profile_id}:")

        try:
            result = await dsp_amc_service.list_dsp_advertisers(
                access_token=access_token,
                profile_id=profile_id,
                count=10  # Small count for testing
            )

            total_results = result.get("totalResults", 0)
            advertisers = result.get("response", [])

            print(f"      Total results: {total_results}")
            print(f"      Retrieved: {len(advertisers)}")

            for adv in advertisers[:2]:  # Show first 2
                print(f"         - {adv.get('name', 'N/A')} (ID: {adv.get('advertiserId', 'N/A')})")

            total_advertisers += len(advertisers)

        except Exception as e:
            print(f"      ❌ Error: {str(e)}")

    # Test 3: Test the integrated method
    print("\n🔍 Step 3: Testing integrated list_all_account_types method...")

    try:
        all_accounts = await dsp_amc_service.list_all_account_types(
            access_token=access_token,
            include_regular=True,
            include_dsp=True,
            include_amc=False  # Skip AMC for speed
        )

        print(f"   ✅ Results:")
        print(f"      Advertising accounts: {len(all_accounts.get('advertising_accounts', []))}")
        print(f"      DSP advertisers: {len(all_accounts.get('dsp_advertisers', []))}")

        # Show sample DSP advertisers
        dsp_advertisers = all_accounts.get('dsp_advertisers', [])
        if dsp_advertisers:
            print(f"\n   Sample DSP Advertisers:")
            for adv in dsp_advertisers[:3]:
                print(f"      - {adv.get('name', 'N/A')} (Profile: {adv.get('profileId', 'N/A')})")

    except Exception as e:
        print(f"   ❌ Error in integrated method: {str(e)}")

    print("\n" + "=" * 80)
    print("📌 Summary:")
    print(f"   Profiles found: {len(profiles)}")
    print(f"   DSP advertisers found (individual calls): {total_advertisers}")
    print(f"   DSP advertisers found (integrated): {len(all_accounts.get('dsp_advertisers', []))}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_dsp_advertisers())