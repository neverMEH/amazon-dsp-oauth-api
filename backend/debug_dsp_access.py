#!/usr/bin/env python3
"""
Debug script to test DSP API access and investigate sync issues.
This script helps diagnose why DSP accounts aren't syncing from Amazon.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the backend directory to the Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.db.supabase_client import get_supabase_client
from app.services.dsp_amc_service import DSPAMCService
from app.services.encryption_service import EncryptionService

async def check_oauth_tokens():
    """Check available OAuth tokens and their scopes."""
    print("🔍 Checking OAuth tokens in database...")

    supabase = get_supabase_client()

    # Get all active tokens
    result = supabase.table("oauth_tokens").select(
        "id, user_id, expires_at, scope, refresh_count, last_refresh"
    ).eq("is_active", True).execute()

    if not result.data:
        print("❌ No active OAuth tokens found in database")
        return None

    print(f"✅ Found {len(result.data)} active OAuth token(s)")

    for token in result.data:
        print(f"\n📋 Token ID: {token['id']}")
        print(f"   User ID: {token['user_id']}")
        print(f"   Expires: {token['expires_at']}")
        print(f"   Scope: {token['scope']}")
        print(f"   Refresh Count: {token['refresh_count']}")
        print(f"   Last Refresh: {token['last_refresh']}")

        # Check if DSP scope is included
        scope = token['scope'] or ""
        has_dsp_scope = "advertising::dsp_campaigns" in scope
        print(f"   Has DSP Scope: {'✅' if has_dsp_scope else '❌'}")

    return result.data[0] if result.data else None

async def test_dsp_api_access(token_record):
    """Test direct DSP API access with the user's token."""
    print("\n🔧 Testing DSP API access...")

    if not token_record:
        print("❌ No token available for testing")
        return False

    try:
        supabase = get_supabase_client()
        encryption_service = EncryptionService()

        # Get the full token record with encrypted data
        full_token = supabase.table("oauth_tokens").select("*").eq(
            "id", token_record['id']
        ).single().execute()

        if not full_token.data:
            print("❌ Could not retrieve full token data")
            return False

        # Decrypt the access token
        encrypted_token = full_token.data['encrypted_access_token']
        access_token = encryption_service.decrypt_token(encrypted_token)

        print(f"✅ Successfully decrypted access token (length: {len(access_token)})")

        # Initialize DSP service
        dsp_service = DSPAMCService()

        # Test 1: List DSP advertisers
        print("\n🧪 Test 1: Listing DSP advertisers...")
        try:
            advertisers = await dsp_service.list_dsp_advertisers(access_token)
            print(f"✅ DSP Advertisers found: {len(advertisers.get('advertisers', []))}")

            for adv in advertisers.get('advertisers', [])[:3]:  # Show first 3
                print(f"   - {adv.get('name', 'Unknown')} (ID: {adv.get('advertiserId', 'N/A')})")

            if advertisers.get('advertisers'):
                # Test 2: Get seats for first advertiser
                first_adv_id = advertisers['advertisers'][0]['advertiserId']
                print(f"\n🧪 Test 2: Getting seats for advertiser {first_adv_id}...")

                try:
                    seats = await dsp_service.list_advertiser_seats(access_token, first_adv_id)
                    print(f"✅ Seats found: {len(seats.get('advertiserSeats', []))}")

                    for seat in seats.get('advertiserSeats', [])[:2]:  # Show first 2
                        current_seats = seat.get('currentSeats', [])
                        print(f"   - Advertiser {seat.get('advertiserId')}: {len(current_seats)} seats")

                except Exception as e:
                    print(f"❌ Error getting seats: {str(e)}")

            return True

        except Exception as e:
            print(f"❌ Error listing DSP advertisers: {str(e)}")

            # Check if it's a permissions error
            if "403" in str(e) or "Forbidden" in str(e):
                print("🚨 This appears to be a permissions issue!")
                print("   The user may not have DSP access or the token lacks required scopes.")
            elif "401" in str(e) or "Unauthorized" in str(e):
                print("🚨 Authentication failed!")
                print("   The token may be expired or invalid.")

            return False

    except Exception as e:
        print(f"❌ Error in DSP API test: {str(e)}")
        return False

async def check_user_accounts():
    """Check what accounts are currently stored for users."""
    print("\n📊 Checking stored user accounts...")

    supabase = get_supabase_client()

    # Get all user accounts
    result = supabase.table("user_accounts").select(
        "id, user_id, account_name, amazon_account_id, account_type, status, metadata"
    ).execute()

    if not result.data:
        print("❌ No user accounts found in database")
        return

    print(f"✅ Found {len(result.data)} user account(s)")

    account_types = {}
    for account in result.data:
        acc_type = account.get('account_type', 'unknown')
        if acc_type not in account_types:
            account_types[acc_type] = []
        account_types[acc_type].append(account)

    for acc_type, accounts in account_types.items():
        print(f"\n📂 {acc_type.upper()} Accounts: {len(accounts)}")
        for acc in accounts[:3]:  # Show first 3
            print(f"   - {acc.get('account_name', 'Unknown')} (ID: {acc.get('amazon_account_id', 'N/A')})")
            print(f"     Status: {acc.get('status', 'unknown')}")

            # Check for DSP-specific metadata
            if acc_type == 'dsp' and acc.get('metadata'):
                metadata = acc['metadata']
                if 'seats_metadata' in metadata:
                    print(f"     Has Seats Metadata: ✅")
                else:
                    print(f"     Has Seats Metadata: ❌")

async def main():
    """Main debug function."""
    print("🔍 DSP Access Debug Tool")
    print("=" * 50)

    # Check environment
    settings = get_settings()
    print(f"Environment: {settings.environment}")
    print(f"Database URL configured: {'✅' if settings.supabase_url else '❌'}")
    print(f"Encryption key configured: {'✅' if settings.fernet_key else '❌'}")

    # Check OAuth tokens
    token_record = await check_oauth_tokens()

    # Test DSP API access
    if token_record:
        success = await test_dsp_api_access(token_record)
        if not success:
            print("\n🔍 Investigating potential issues:")
            print("   1. Missing DSP scope in OAuth token")
            print("   2. User account lacks DSP permissions in Amazon")
            print("   3. Token expired or invalid")
            print("   4. API endpoint or network issues")

    # Check stored accounts
    await check_user_accounts()

    print("\n" + "=" * 50)
    print("Debug complete. Check output above for issues.")

if __name__ == "__main__":
    asyncio.run(main())