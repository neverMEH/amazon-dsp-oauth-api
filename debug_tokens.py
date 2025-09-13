#!/usr/bin/env python3
"""
Debug script to check token storage and retrieval issues
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment variables
load_dotenv()

from supabase import create_client
from app.config import settings
from app.services.token_service import TokenService

async def main():
    """Debug token storage and retrieval"""
    print("=== Amazon Ads API OAuth Token Debugging ===\n")
    
    # Initialize Supabase client
    print(f"Connecting to Supabase...")
    print(f"URL: {settings.supabase_url}")
    
    try:
        client = create_client(settings.supabase_url, settings.supabase_key)
        print("✓ Connected to Supabase\n")
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        return
    
    # Check all tokens in database
    print("Checking all tokens in database...")
    try:
        all_tokens = client.table("oauth_tokens").select("*").execute()
        print(f"Total tokens found: {len(all_tokens.data) if all_tokens.data else 0}")
        
        if all_tokens.data:
            for token in all_tokens.data:
                print(f"\nToken ID: {token['id']}")
                print(f"  Is Active: {token['is_active']}")
                print(f"  Created: {token['created_at']}")
                print(f"  Expires: {token['expires_at']}")
                print(f"  Refresh Count: {token.get('refresh_count', 0)}")
                
                # Check if expired
                expires_at = datetime.fromisoformat(token['expires_at'].replace('Z', '+00:00'))
                is_expired = expires_at < datetime.now(timezone.utc)
                print(f"  Status: {'EXPIRED' if is_expired else 'VALID'}")
    except Exception as e:
        print(f"✗ Error fetching tokens: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Check active tokens specifically
    print("Checking for active tokens (is_active=True)...")
    try:
        # Method 1: Using eq filter without single()
        active_tokens = client.table("oauth_tokens").select("*").eq("is_active", True).execute()
        print(f"Active tokens found (using eq): {len(active_tokens.data) if active_tokens.data else 0}")
        
        if active_tokens.data:
            for token in active_tokens.data:
                print(f"  - Token ID: {token['id']}")
        
        # Method 2: Using single() - this is what the code uses
        print("\nTrying with .single() method (current implementation)...")
        try:
            single_result = client.table("oauth_tokens").select("*").eq("is_active", True).single().execute()
            print(f"Single result data: {single_result.data}")
            if single_result.data:
                print(f"  Token ID: {single_result.data['id']}")
        except Exception as e:
            print(f"  Error with single(): {e}")
            
    except Exception as e:
        print(f"✗ Error checking active tokens: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test TokenService methods
    print("Testing TokenService methods...")
    token_service = TokenService(client)
    
    try:
        print("Calling get_active_token()...")
        active_token = await token_service.get_active_token()
        if active_token:
            print(f"✓ Active token found: {active_token['id']}")
        else:
            print("✗ No active token returned")
            
        print("\nCalling get_decrypted_tokens()...")
        decrypted = await token_service.get_decrypted_tokens()
        if decrypted:
            print(f"✓ Decrypted tokens retrieved")
            print(f"  Access token: {decrypted['access_token'][:50]}...")
            print(f"  Refresh token: {decrypted['refresh_token'][:50]}...")
        else:
            print("✗ No decrypted tokens returned")
            
    except Exception as e:
        print(f"✗ Error with TokenService: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Check for data consistency issues
    print("Checking for data consistency issues...")
    
    # Check for multiple active tokens
    try:
        active_count = client.table("oauth_tokens").select("id", count="exact").eq("is_active", True).execute()
        if hasattr(active_count, 'count') and active_count.count:
            if active_count.count > 1:
                print(f"⚠ WARNING: Multiple active tokens found ({active_count.count})")
                print("  This could cause issues with .single() method")
            elif active_count.count == 0:
                print("⚠ WARNING: No active tokens in database")
                print("  The OAuth flow may not have completed successfully")
            else:
                print(f"✓ Exactly one active token found")
        else:
            print("Could not get count of active tokens")
    except Exception as e:
        print(f"✗ Error checking consistency: {e}")
    
    print("\n=== Diagnosis Complete ===")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())