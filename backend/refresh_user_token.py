#!/usr/bin/env python3
"""
Refresh tokens for a user
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.base import get_supabase_service_client
from app.services.amazon_oauth_service import amazon_oauth_service
from app.services.token_service import token_service
import structlog

logger = structlog.get_logger()


async def refresh_user_token():
    """Refresh token for a user"""

    # Initialize Supabase client
    supabase = get_supabase_service_client()

    print("\n" + "="*80)
    print("TOKEN REFRESH")
    print("="*80)

    # Get a user with tokens
    print("\n1. Looking for users with tokens...")

    token_result = supabase.table("oauth_tokens").select("*").execute()
    if not token_result.data:
        print("❌ No users with tokens found.")
        return

    # Find the first token (expired or not)
    token_data = token_result.data[0]
    user_id = token_data["user_id"]

    expires_at = datetime.fromisoformat(token_data["expires_at"].replace('Z', '+00:00'))
    is_expired = expires_at <= datetime.now(timezone.utc)

    print(f"✅ Found token for user: {user_id}")
    print(f"   Expires at: {expires_at}")
    print(f"   Status: {'EXPIRED' if is_expired else 'VALID'}")

    if not is_expired:
        print("\n   Token is still valid. Do you want to force refresh? (y/n): ", end="")
        response = input().strip().lower()
        if response != 'y':
            print("   Skipping refresh.")
            return

    print("\n2. Refreshing token...")

    # Decrypt the refresh token
    try:
        refresh_token = token_service.decrypt_token(token_data["refresh_token"])
    except:
        # Token might be stored as plain text
        refresh_token = token_data["refresh_token"]

    try:
        # Refresh the token
        new_tokens = await amazon_oauth_service.refresh_access_token(refresh_token)

        print("✅ Token refreshed successfully!")

        # Update in database
        new_expires = datetime.now(timezone.utc) + timedelta(seconds=new_tokens.expires_in)

        update_data = {
            "access_token": token_service.encrypt_token(new_tokens.access_token),
            "refresh_token": token_service.encrypt_token(new_tokens.refresh_token),
            "expires_at": new_expires.isoformat(),
            "refresh_count": token_data.get("refresh_count", 0) + 1,
            "last_refresh_at": datetime.now(timezone.utc).isoformat()
        }

        supabase.table("oauth_tokens").update(update_data).eq("user_id", user_id).execute()

        print(f"✅ Token updated in database")
        print(f"   New expiry: {new_expires}")
        print(f"   Valid for: {new_tokens.expires_in} seconds")

        # Update all user accounts' last_synced_at
        supabase.table("user_accounts").update({
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }).eq("user_id", user_id).execute()

        print("✅ Account sync timestamps updated")

    except Exception as e:
        print(f"❌ Failed to refresh token: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("DONE")
    print("="*80)


if __name__ == "__main__":
    print("\nStarting Token Refresh...")
    asyncio.run(refresh_user_token())