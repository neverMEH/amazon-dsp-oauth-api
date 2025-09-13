#!/usr/bin/env python3
"""
Debug script to check token storage and retrieval
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

import asyncio
from supabase import create_client, Client
from datetime import datetime, timezone

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY in environment")
    print("Make sure you have a .env file with these values")
    sys.exit(1)

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_tokens():
    """Check for tokens in the database"""
    print("\n🔍 Checking for tokens in database...")
    print("-" * 50)
    
    try:
        # Check oauth_tokens table
        result = supabase.table("oauth_tokens").select("*").execute()
        
        if not result.data:
            print("❌ No tokens found in oauth_tokens table")
            return False
        
        print(f"✅ Found {len(result.data)} token record(s)")
        
        for i, token in enumerate(result.data, 1):
            print(f"\nToken #{i}:")
            print(f"  ID: {token.get('id')}")
            print(f"  Active: {token.get('is_active')}")
            print(f"  Expires at: {token.get('expires_at')}")
            print(f"  Refresh count: {token.get('refresh_count', 0)}")
            print(f"  Created at: {token.get('created_at')}")
            
            # Check if token is expired
            if token.get('expires_at'):
                expires_at = datetime.fromisoformat(
                    token['expires_at'].replace('Z', '+00:00')
                )
                is_valid = expires_at > datetime.now(timezone.utc)
                print(f"  Valid: {'✅ Yes' if is_valid else '❌ No (expired)'}")
            
        # Check for active tokens
        active_result = supabase.table("oauth_tokens").select("*").eq("is_active", True).execute()
        
        if active_result.data:
            print(f"\n✅ Found {len(active_result.data)} ACTIVE token(s)")
        else:
            print("\n⚠️  No ACTIVE tokens found (all tokens are deactivated)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking tokens: {e}")
        return False

def check_auth_logs():
    """Check authentication audit logs"""
    print("\n📋 Checking authentication audit logs...")
    print("-" * 50)
    
    try:
        # Get recent auth events
        result = supabase.table("auth_audit_log").select("*").order(
            "created_at", desc=True
        ).limit(10).execute()
        
        if not result.data:
            print("❌ No authentication events found")
            return
        
        print(f"✅ Found {len(result.data)} recent authentication event(s)")
        
        for event in result.data:
            print(f"\n  {event.get('created_at', 'Unknown time')}:")
            print(f"    Type: {event.get('event_type')}")
            print(f"    Status: {event.get('event_status')}")
            if event.get('error_message'):
                print(f"    Error: {event.get('error_message')}")
                
    except Exception as e:
        print(f"❌ Error checking auth logs: {e}")

def check_oauth_states():
    """Check OAuth state tokens"""
    print("\n🔐 Checking OAuth state tokens...")
    print("-" * 50)
    
    try:
        # Get recent state tokens
        result = supabase.table("oauth_states").select("*").order(
            "created_at", desc=True
        ).limit(5).execute()
        
        if not result.data:
            print("❌ No OAuth state tokens found")
            return
        
        print(f"✅ Found {len(result.data)} recent state token(s)")
        
        for state in result.data:
            print(f"\n  State token (first 10 chars): {state.get('state_token', '')[:10]}...")
            print(f"    Used: {'Yes' if state.get('used') else 'No'}")
            print(f"    Created: {state.get('created_at')}")
            print(f"    Expires: {state.get('expires_at')}")
                
    except Exception as e:
        print(f"❌ Error checking state tokens: {e}")

def main():
    """Run all checks"""
    print("=" * 50)
    print("🔍 Amazon DSP OAuth Token Debugger")
    print("=" * 50)
    
    print(f"\n📦 Using Supabase URL: {SUPABASE_URL}")
    
    # Check tokens
    has_tokens = check_tokens()
    
    # Check auth logs
    check_auth_logs()
    
    # Check OAuth states
    check_oauth_states()
    
    print("\n" + "=" * 50)
    
    if has_tokens:
        print("\n✅ Tokens exist in database")
        print("\nTo retrieve tokens, use:")
        print("  curl -X GET 'http://localhost:8000/api/v1/auth/tokens' \\")
        print("    -H 'X-Admin-Key: your-admin-key'")
    else:
        print("\n❌ No tokens found")
        print("\nTo authenticate:")
        print("  1. Go to http://localhost:8000/api/v1/auth/amazon/login")
        print("  2. Complete the Amazon OAuth flow")
        print("  3. After callback, tokens should be stored")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()