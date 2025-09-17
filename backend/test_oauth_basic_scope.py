#!/usr/bin/env python3
"""
Test OAuth with basic scope to verify it's working
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.amazon_oauth_service import amazon_oauth_service
from app.config import settings


async def test_oauth_basic_scope():
    """Test OAuth URL generation with basic scope"""

    print("=" * 80)
    print("Testing Amazon OAuth with Basic Scope")
    print("=" * 80)

    # Check current configuration
    print(f"\n📋 Current Configuration:")
    print(f"   Client ID: {settings.amazon_client_id[:20]}...")
    print(f"   Redirect URI: {settings.amazon_redirect_uri}")
    print(f"   Auth URL: {settings.amazon_auth_url}")
    print(f"   Token URL: {settings.amazon_token_url}")

    # Check scope configuration
    print(f"\n🔐 Scope Configuration:")
    print(f"   Configured Scopes: {amazon_oauth_service.scopes}")
    print(f"   Scope String: '{amazon_oauth_service.scope}'")

    # Generate OAuth URL
    auth_url, state = amazon_oauth_service.generate_oauth_url()

    print(f"\n✅ Generated OAuth URL Successfully!")
    print(f"   State Token: {state[:10]}...")
    print(f"\n📝 Full OAuth URL:")
    print(f"   {auth_url}")

    # Parse the URL to verify parameters
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)

    print(f"\n🔍 URL Parameters:")
    for key, values in params.items():
        value = values[0] if values else ""
        if key == "client_id":
            print(f"   {key}: {value[:20]}...")
        elif key == "state":
            print(f"   {key}: {value[:10]}...")
        else:
            print(f"   {key}: {value}")

    # Verify critical parameters
    print(f"\n✔️ Verification:")
    has_client_id = "client_id" in params
    has_scope = "scope" in params
    has_redirect = "redirect_uri" in params
    has_response_type = params.get("response_type", [""])[0] == "code"

    print(f"   Client ID present: {'✅' if has_client_id else '❌'}")
    print(f"   Scope present: {'✅' if has_scope else '❌'}")
    print(f"   Redirect URI present: {'✅' if has_redirect else '❌'}")
    print(f"   Response type is 'code': {'✅' if has_response_type else '❌'}")

    # Check if scope is basic only
    scope_value = params.get("scope", [""])[0]
    is_basic_only = scope_value == "advertising::campaign_management"
    print(f"   Using basic scope only: {'✅' if is_basic_only else '❌'} ('{scope_value}')")

    print("\n" + "=" * 80)
    print("📌 Summary:")
    if all([has_client_id, has_scope, has_redirect, has_response_type, is_basic_only]):
        print("   ✅ OAuth URL is correctly configured with basic scope only")
        print("   ✅ This should work without requiring additional app approval")
        print("\n   Next step: Test the URL in a browser to verify Amazon accepts it")
    else:
        print("   ❌ OAuth URL has configuration issues")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_oauth_basic_scope())