#!/usr/bin/env python3
"""
Retrieve OAuth tokens directly from database
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
admin_key = os.getenv("ADMIN_KEY", "generate_a_secure_admin_key")

print("=" * 50)
print("🔑 Token Retrieval")
print("=" * 50)

# Check if backend is running
import requests

backend_url = "http://localhost:8000"

# First check if backend is running
try:
    health_response = requests.get(f"{backend_url}/api/v1/health", timeout=2)
    if health_response.status_code == 200:
        print("✅ Backend is running")
    else:
        print("⚠️  Backend returned status:", health_response.status_code)
except requests.exceptions.ConnectionError:
    print("❌ Backend is not running at", backend_url)
    print("\nTo start the backend:")
    print("  1. Install a virtual environment")
    print("  2. Install dependencies: pip install -r backend/requirements.txt")
    print("  3. Run: uvicorn backend.app.main:app --reload")
    print("\nAlternatively, since tokens exist in database, here's what would be returned:")
    
    # Direct database access as fallback
    from supabase import create_client
    from cryptography.fernet import Fernet
    from datetime import datetime, timezone
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    fernet_key = os.getenv("FERNET_KEY")
    
    if not all([supabase_url, supabase_key, fernet_key]):
        print("❌ Missing required environment variables")
        sys.exit(1)
    
    # Create clients
    supabase = create_client(supabase_url, supabase_key)
    fernet = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
    
    # Get active token
    result = supabase.table("oauth_tokens").select("*").eq("is_active", True).single().execute()
    
    if result.data:
        token_data = result.data
        print("\n📦 Active Token Found:")
        print(f"  Token ID: {token_data['id']}")
        print(f"  Expires at: {token_data['expires_at']}")
        
        # Check validity
        expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        is_valid = expires_at > datetime.now(timezone.utc)
        print(f"  Valid: {'✅ Yes' if is_valid else '❌ No (expired)'}")
        
        if is_valid:
            # Decrypt tokens
            try:
                access_token = fernet.decrypt(token_data['access_token'].encode()).decode()
                refresh_token = fernet.decrypt(token_data['refresh_token'].encode()).decode()
                
                print("\n🔐 Decrypted Tokens:")
                print(f"  Access Token: {access_token[:50]}...")
                print(f"  Refresh Token: {refresh_token[:50]}...")
                
                print("\n✅ These tokens can be used to call Amazon Ads API")
                print("\nExample API call:")
                print("  curl -X GET 'https://advertising-api.amazon.com/v2/profiles' \\")
                print(f"    -H 'Authorization: Bearer {access_token[:20]}...' \\")
                print("    -H 'Amazon-Advertising-API-ClientId: " + os.getenv("AMAZON_CLIENT_ID", "your-client-id") + "'")
                
            except Exception as e:
                print(f"\n❌ Error decrypting tokens: {e}")
                print("The FERNET_KEY may have changed since tokens were stored")
    else:
        print("\n❌ No active tokens found in database")
    
    sys.exit(0)

# If backend is running, try to get tokens via API
print(f"\n🔍 Attempting to retrieve tokens via API...")
print(f"Using Admin Key: {admin_key[:10]}...")

try:
    token_response = requests.get(
        f"{backend_url}/api/v1/auth/tokens",
        headers={"X-Admin-Key": admin_key},
        timeout=5
    )
    
    if token_response.status_code == 200:
        tokens = token_response.json()
        print("\n✅ Successfully retrieved tokens!")
        print(f"  Access Token: {tokens['access_token'][:50]}...")
        print(f"  Refresh Token: {tokens['refresh_token'][:50]}...")
        print(f"  Expires at: {tokens['expires_at']}")
        print(f"  Valid: {tokens['token_valid']}")
        
        print("\n📋 You can now use these tokens to call Amazon Ads API")
    elif token_response.status_code == 401:
        print("\n❌ Unauthorized - Invalid admin key")
        print("Check your ADMIN_KEY in .env file")
    elif token_response.status_code == 404:
        error = token_response.json().get("detail", {})
        print(f"\n❌ {error.get('error', {}).get('message', 'No tokens found')}")
    else:
        print(f"\n❌ Error: Status {token_response.status_code}")
        print(token_response.text)
        
except Exception as e:
    print(f"\n❌ Error calling API: {e}")