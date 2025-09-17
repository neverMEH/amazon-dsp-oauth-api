#!/usr/bin/env python3
"""
Debug script to test OAuth URL generation for Amazon Advertising API
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.services.amazon_oauth_service import AmazonOAuthService

def debug_oauth_url():
    """Debug the OAuth URL generation"""

    print("=" * 80)
    print("Amazon Advertising API OAuth URL Debug")
    print("=" * 80)

    # Show current configuration
    print("\n📋 Current Configuration:")
    print(f"  Client ID: {settings.amazon_client_id}")
    print(f"  Auth URL: {settings.amazon_auth_url}")
    print(f"  Token URL: {settings.amazon_token_url}")
    print(f"  Redirect URI: {settings.amazon_redirect_uri}")
    print(f"  Scopes: {settings.amazon_scope}")

    # Initialize service
    service = AmazonOAuthService()

    # Generate OAuth URL
    auth_url, state = service.generate_oauth_url()

    print("\n🔗 Generated OAuth URL:")
    print(f"  Full URL: {auth_url}")

    # Parse and display components
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)

    print("\n📝 URL Components:")
    print(f"  Base URL: {parsed.scheme}://{parsed.netloc}{parsed.path}")
    print("\n  Parameters:")
    for key, values in params.items():
        value = values[0] if values else ""
        if key == "client_id":
            print(f"    {key}: {value[:20]}...")
        elif key == "state":
            print(f"    {key}: {value[:10]}...")
        else:
            print(f"    {key}: {value}")

    # Check for common issues
    print("\n✅ Validation Checks:")

    # Check 1: Scope format
    scope_value = params.get('scope', [''])[0]
    scopes_list = scope_value.split(' ') if scope_value else []
    print(f"  ✓ Scopes found: {len(scopes_list)}")
    for scope in scopes_list:
        if '::' in scope:
            print(f"    - {scope} ✅")
        else:
            print(f"    - {scope} ❌ (Invalid format)")

    # Check 2: Required parameters
    required_params = ['client_id', 'scope', 'response_type', 'redirect_uri', 'state']
    for param in required_params:
        if param in params:
            print(f"  ✓ {param}: Present")
        else:
            print(f"  ✗ {param}: MISSING ❌")

    # Check 3: Response type
    response_type = params.get('response_type', [''])[0]
    if response_type == 'code':
        print(f"  ✓ response_type: '{response_type}' (correct)")
    else:
        print(f"  ✗ response_type: '{response_type}' (should be 'code') ❌")

    # Check 4: Redirect URI format
    redirect_uri = params.get('redirect_uri', [''])[0]
    if redirect_uri.startswith('http://') or redirect_uri.startswith('https://'):
        print(f"  ✓ redirect_uri: Valid URL format")
    else:
        print(f"  ✗ redirect_uri: Invalid URL format ❌")

    print("\n" + "=" * 80)
    print("📌 Common 400 Error Causes:")
    print("  1. Missing or incorrect scopes (must include advertising::account_management)")
    print("  2. Invalid client_id or client not approved for requested scopes")
    print("  3. Redirect URI doesn't match registered URI in Amazon app settings")
    print("  4. Malformed URL encoding")
    print("=" * 80)

    # Test URL encoding manually
    print("\n🔧 Manual URL Construction Test:")
    manual_params = {
        "client_id": settings.amazon_client_id,
        "scope": settings.amazon_scope,
        "response_type": "code",
        "redirect_uri": settings.amazon_redirect_uri,
        "state": "test_state_123"
    }

    # Try different encoding approaches
    print("\n  Method 1 - Standard urlencode:")
    manual_url_1 = f"{settings.amazon_auth_url}?{urlencode(manual_params)}"
    print(f"    {manual_url_1[:100]}...")

    print("\n  Method 2 - Safe encoding (quote_via=quote):")
    from urllib.parse import quote
    manual_url_2 = f"{settings.amazon_auth_url}?{urlencode(manual_params, quote_via=quote)}"
    print(f"    {manual_url_2[:100]}...")

    print("\n💡 Recommended Action:")
    print("  1. Verify the client_id is correct and app is approved")
    print("  2. Ensure redirect_uri matches EXACTLY what's registered in Amazon")
    print("  3. Confirm all required scopes are approved for your app")
    print("  4. Try the URL in an incognito browser to test")

if __name__ == "__main__":
    debug_oauth_url()