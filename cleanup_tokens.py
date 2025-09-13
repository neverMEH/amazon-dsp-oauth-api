#!/usr/bin/env python3
"""
Clean up multiple active tokens in the database
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment variables
load_dotenv()

from supabase import create_client
from app.config import settings

async def cleanup_tokens():
    """Clean up multiple active tokens, keeping only the most recent"""
    print("Token Cleanup Utility\n" + "="*50)
    
    client = create_client(settings.supabase_url, settings.supabase_key)
    
    # Get all tokens
    print("Fetching all tokens from database...")
    all_result = client.table("oauth_tokens").select("*").execute()
    
    if all_result.data:
        print(f"Total tokens in database: {len(all_result.data)}")
        
        # Group by active status
        active_tokens = [t for t in all_result.data if t.get('is_active')]
        inactive_tokens = [t for t in all_result.data if not t.get('is_active')]
        
        print(f"  Active tokens: {len(active_tokens)}")
        print(f"  Inactive tokens: {len(inactive_tokens)}")
    else:
        print("No tokens found in database")
        return
    
    # Check for multiple active tokens
    if len(active_tokens) > 1:
        print(f"\n⚠ Found {len(active_tokens)} active tokens - cleaning up...")
        
        # Sort by created_at descending (newest first)
        sorted_tokens = sorted(active_tokens, key=lambda x: x['created_at'], reverse=True)
        
        # Keep the newest token
        keep_token = sorted_tokens[0]
        expires_at = datetime.fromisoformat(keep_token['expires_at'].replace('Z', '+00:00'))
        is_valid = expires_at > datetime.now(timezone.utc)
        
        print(f"\nKeeping token:")
        print(f"  ID: {keep_token['id']}")
        print(f"  Created: {keep_token['created_at']}")
        print(f"  Expires: {keep_token['expires_at']}")
        print(f"  Valid: {is_valid}")
        
        # Deactivate all older tokens
        print(f"\nDeactivating {len(sorted_tokens) - 1} older tokens:")
        for token in sorted_tokens[1:]:
            print(f"  - Deactivating token {token['id']} (created: {token['created_at']})")
            result = client.table("oauth_tokens").update(
                {"is_active": False}
            ).eq("id", token['id']).execute()
            
            if result.data:
                print(f"    ✓ Successfully deactivated")
            else:
                print(f"    ✗ Failed to deactivate")
        
        print("\n✓ Cleanup complete!")
        
    elif len(active_tokens) == 1:
        token = active_tokens[0]
        expires_at = datetime.fromisoformat(token['expires_at'].replace('Z', '+00:00'))
        is_valid = expires_at > datetime.now(timezone.utc)
        
        print("\n✓ Exactly one active token found (no cleanup needed)")
        print(f"  ID: {token['id']}")
        print(f"  Created: {token['created_at']}")
        print(f"  Expires: {token['expires_at']}")
        print(f"  Valid: {is_valid}")
        
    else:
        print("\n⚠ No active tokens found in database")
        print("  You may need to complete the OAuth flow again")
    
    # Optional: Clean up very old inactive tokens
    print("\nChecking for old inactive tokens...")
    old_threshold = datetime.now(timezone.utc) - timedelta(days=7)
    old_tokens = [
        t for t in inactive_tokens 
        if datetime.fromisoformat(t['created_at'].replace('Z', '+00:00')) < old_threshold
    ]
    
    if old_tokens:
        print(f"Found {len(old_tokens)} tokens older than 7 days")
        response = input("Do you want to delete these old tokens? (y/n): ")
        
        if response.lower() == 'y':
            for token in old_tokens:
                print(f"  - Deleting token {token['id']} (created: {token['created_at']})")
                client.table("oauth_tokens").delete().eq("id", token['id']).execute()
            print(f"✓ Deleted {len(old_tokens)} old tokens")
    else:
        print("No old tokens to clean up")

if __name__ == "__main__":
    asyncio.run(cleanup_tokens())