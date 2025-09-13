#!/usr/bin/env python3
"""
Direct test of auth status endpoint logic
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment variables
load_dotenv()

from app.services.token_service import token_service
from datetime import datetime, timezone

async def test_auth_status():
    """Test the auth status logic directly"""
    print("Testing Auth Status Logic\n" + "="*50)
    
    try:
        # This is the exact logic from the /auth/status endpoint
        print("1. Calling token_service.get_active_token()...")
        token_record = await token_service.get_active_token()
        
        if not token_record:
            print("   ✗ NO ACTIVE TOKEN FOUND")
            print("   This would trigger: 'No active authentication found' error")
            return
        
        print(f"   ✓ Active token found: {token_record['id']}")
        
        # Check token validity
        print("\n2. Checking token validity...")
        expires_at = datetime.fromisoformat(
            token_record["expires_at"].replace("Z", "+00:00")
        )
        is_valid = expires_at > datetime.now(timezone.utc)
        
        print(f"   Token expires at: {expires_at}")
        print(f"   Current time:     {datetime.now(timezone.utc)}")
        print(f"   Token is valid:   {is_valid}")
        
        # Build response
        print("\n3. Building response...")
        response = {
            "authenticated": True,
            "token_valid": is_valid,
            "expires_at": str(expires_at),
            "refresh_count": token_record.get("refresh_count", 0),
            "last_refresh": token_record.get("last_refresh_at"),
            "scope": token_record["scope"]
        }
        
        print("   Response that would be returned:")
        for key, value in response.items():
            print(f"     {key}: {value}")
        
        print("\n✓ Auth status check would succeed!")
        
    except Exception as e:
        print(f"\n✗ Error during auth status check: {e}")
        import traceback
        traceback.print_exc()

async def test_tokens_endpoint():
    """Test the /tokens endpoint logic"""
    print("\n\nTesting /tokens Endpoint Logic\n" + "="*50)
    
    try:
        print("1. Calling token_service.get_decrypted_tokens()...")
        tokens = await token_service.get_decrypted_tokens()
        
        if not tokens:
            print("   ✗ NO TOKENS FOUND")
            print("   This would trigger: 'Authentication succeeded but no tokens found' error")
            return
        
        print(f"   ✓ Tokens retrieved successfully")
        print(f"   Token ID: {tokens['id']}")
        print(f"   Access token (first 50 chars): {tokens['access_token'][:50]}...")
        print(f"   Refresh token (first 50 chars): {tokens['refresh_token'][:50]}...")
        
        # Check if token is still valid
        expires_at = datetime.fromisoformat(
            tokens["expires_at"].replace("Z", "+00:00")
        )
        is_valid = expires_at > datetime.now(timezone.utc)
        
        print(f"\n2. Token validity check:")
        print(f"   Expires at: {expires_at}")
        print(f"   Is valid: {is_valid}")
        print(f"   Refresh count: {tokens['refresh_count']}")
        
        print("\n✓ Tokens endpoint would succeed!")
        
    except Exception as e:
        print(f"\n✗ Error during tokens retrieval: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_auth_status())
    asyncio.run(test_tokens_endpoint())