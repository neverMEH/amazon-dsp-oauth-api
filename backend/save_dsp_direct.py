#!/usr/bin/env python3
"""
Direct script to save DSP advertiser to database
"""
import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import get_supabase_service_client
from app.services.token_service import token_service
from app.services.dsp_amc_service import DSPAMCService
import uuid

async def save_dsp_advertiser():
    """Save DSP advertiser directly to database"""
    try:
        # Get tokens
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            print("❌ No OAuth tokens found. Please authenticate first.")
            return

        access_token = tokens["access_token"]
        print(f"✅ Got access token")

        # Initialize Supabase with service role
        supabase = get_supabase_service_client()
        print("✅ Initialized Supabase client")

        # Hardcoded values we know
        db_user_id = "52a86382-266b-4004-bfd9-6bd6a64026eb"

        # Get DSP advertisers using the API
        dsp_service = DSPAMCService()
        profile_id = "3335273396303954"  # Agency profile that has DSP access

        # Get DSP advertisers from this profile
        dsp_response = await dsp_service.list_dsp_advertisers(
            access_token=access_token,
            profile_id=profile_id
        )

        print(f"DSP Response: {dsp_response}")

        if not dsp_response:
            print("❌ No DSP response")
            return

        # Check for different response formats
        if "advertisers" in dsp_response:
            advertisers = dsp_response["advertisers"]
        elif "response" in dsp_response:
            advertisers = dsp_response["response"]
        elif "results" in dsp_response:
            advertisers = dsp_response["results"]
        elif isinstance(dsp_response, list):
            advertisers = dsp_response
        else:
            print(f"❌ Unknown response format: {list(dsp_response.keys())}")
            return
        print(f"✅ Found {len(advertisers)} DSP advertiser(s)")

        for advertiser in advertisers:
            advertiser_id = advertiser.get("advertiserId")
            advertiser_name = advertiser.get("name") or advertiser.get("advertiserName", "Unknown DSP")

            print(f"\n📥 Saving DSP advertiser: {advertiser_name} ({advertiser_id})")

            # Create the account data
            account_data = {
                "id": str(uuid.uuid4()),
                "user_id": db_user_id,
                "account_name": advertiser_name,
                "amazon_account_id": advertiser_id,
                "account_type": "dsp",  # IMPORTANT: Set as DSP type
                "status": "active",
                "is_default": False,
                "connected_at": datetime.utcnow().isoformat(),
                "last_synced_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "country": advertiser.get("country"),
                    "timezone": advertiser.get("timezone"),
                    "profileId": profile_id,
                    "raw_data": advertiser
                }
            }

            # Insert into database (using service role to bypass RLS)
            result = supabase.table("user_accounts").insert(account_data).execute()

            if result.data:
                print(f"✅ Saved DSP advertiser: {advertiser_name}")
            else:
                print(f"❌ Failed to save: {advertiser_name}")

        # Verify the save
        print("\n📊 Checking database...")
        dsp_count = supabase.table("user_accounts").select("id, account_name, account_type").eq(
            "user_id", db_user_id
        ).eq("account_type", "dsp").execute()

        if dsp_count.data:
            print(f"✅ Found {len(dsp_count.data)} DSP accounts in database:")
            for account in dsp_count.data:
                print(f"  - {account['account_name']} (type: {account['account_type']})")
        else:
            print("❌ No DSP accounts found in database")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Direct DSP Save...")
    result = asyncio.run(save_dsp_advertiser())
    if result:
        print("\n✅ DSP advertiser saved successfully!")
    else:
        print("\n❌ Failed to save DSP advertiser!")