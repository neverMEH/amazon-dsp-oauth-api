# Amazon Advertising API OAuth Authentication Troubleshooting Guide

## Issue: "Authentication succeeded but no tokens found" Error

### Root Cause Analysis

Based on the debugging performed, the issue is **NOT** with the database or token storage. The tokens are properly stored and retrievable. The issue appears to be one of the following:

1. **Frontend-Backend Communication Issue**: The frontend might be calling the wrong endpoint or with incorrect headers
2. **Timing Issue**: The frontend might be checking for tokens before the OAuth callback has completed
3. **Multiple Active Tokens**: The `.single()` method in Supabase fails when there are multiple active tokens

### Verified Working Components

✅ **Database Connection**: Supabase is connected and responding correctly
✅ **Token Storage**: Tokens are properly encrypted and stored in the database
✅ **Token Retrieval**: The `get_active_token()` and `get_decrypted_tokens()` methods work correctly
✅ **Token Validity**: The current token (ID: 67c60e3f-2347-49b1-8aef-d1ec856d4a8a) is valid until 2025-09-13 20:01:07 UTC

### Solutions

## Solution 1: Fix Potential Multiple Active Tokens Issue

The Supabase `.single()` method expects exactly one result. If there are multiple active tokens, it will fail silently. Update the `get_active_token()` method:

```python
# In backend/app/services/token_service.py, line 147-166

async def get_active_token(self) -> Optional[Dict]:
    """
    Get the active token record
    
    Returns:
        Active token record or None
    """
    try:
        # First, check if there are multiple active tokens
        result = self.db.table("oauth_tokens").select("*").eq(
            "is_active", True
        ).execute()
        
        if not result.data:
            return None
        
        if len(result.data) > 1:
            logger.warning(f"Multiple active tokens found ({len(result.data)}), using most recent")
            # Sort by created_at and return the most recent
            sorted_tokens = sorted(result.data, key=lambda x: x['created_at'], reverse=True)
            return sorted_tokens[0]
        
        return result.data[0]
        
    except Exception as e:
        logger.debug("No active token found", error=str(e))
        return None
```

## Solution 2: Add Better Error Handling and Logging

Update the auth endpoints to provide more detailed error information:

```python
# In backend/app/api/v1/auth.py, line 378-389

# Get decrypted tokens
tokens = await token_service.get_decrypted_tokens()

if not tokens:
    # Add more detailed logging
    logger.error("No tokens found when expected", 
                 endpoint="/tokens",
                 active_token_check=await token_service.get_active_token() is not None)
    
    # Check if there are any tokens at all
    all_tokens = self.db.table("oauth_tokens").select("id, is_active, created_at").execute()
    logger.error("Token state", 
                 total_tokens=len(all_tokens.data) if all_tokens.data else 0,
                 active_tokens=[t for t in (all_tokens.data or []) if t.get('is_active')])
    
    raise HTTPException(
        status_code=404,
        detail={"error": {
            "code": "NO_TOKENS_FOUND",
            "message": "No active tokens found. Please complete the OAuth flow first.",
            "details": {
                "tokens_in_db": len(all_tokens.data) if all_tokens.data else 0,
                "active_tokens": sum(1 for t in (all_tokens.data or []) if t.get('is_active'))
            }
        }}
    )
```

## Solution 3: Ensure Proper OAuth Flow Completion

The issue might occur if the frontend checks for tokens before the callback has finished processing. Add a delay or polling mechanism:

```javascript
// Frontend code example
async function checkAuthStatus(retries = 5, delay = 1000) {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch('/api/v1/auth/status');
            const data = await response.json();
            
            if (response.ok && data.authenticated) {
                return data;
            }
        } catch (error) {
            console.log(`Auth check attempt ${i + 1} failed:`, error);
        }
        
        if (i < retries - 1) {
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    throw new Error('Authentication check failed after multiple attempts');
}
```

## Solution 4: Clean Up Database State

Run this script to ensure only one active token exists:

```python
#!/usr/bin/env python3
import asyncio
from supabase import create_client
from app.config import settings

async def cleanup_tokens():
    client = create_client(settings.supabase_url, settings.supabase_key)
    
    # Get all active tokens
    result = client.table("oauth_tokens").select("*").eq("is_active", True).execute()
    
    if result.data and len(result.data) > 1:
        # Sort by created_at, keep the newest
        sorted_tokens = sorted(result.data, key=lambda x: x['created_at'], reverse=True)
        
        # Keep the first (newest) token
        keep_token = sorted_tokens[0]
        print(f"Keeping token: {keep_token['id']} (created: {keep_token['created_at']})")
        
        # Deactivate all others
        for token in sorted_tokens[1:]:
            print(f"Deactivating token: {token['id']} (created: {token['created_at']})")
            client.table("oauth_tokens").update({"is_active": False}).eq("id", token['id']).execute()
        
        print("Cleanup complete!")
    else:
        print("No cleanup needed - found", len(result.data) if result.data else 0, "active tokens")

if __name__ == "__main__":
    asyncio.run(cleanup_tokens())
```

## Testing the Fix

1. **Run the cleanup script** to ensure only one active token:
   ```bash
   python3 cleanup_tokens.py
   ```

2. **Test the API directly** using curl:
   ```bash
   # Check auth status
   curl -X GET "http://localhost:8000/api/v1/auth/status" -H "accept: application/json"
   
   # Get tokens (requires admin key)
   curl -X GET "http://localhost:8000/api/v1/auth/tokens" \
        -H "accept: application/json" \
        -H "X-Admin-Key: dev_admin_key"
   ```

3. **Monitor the logs** for any errors:
   ```bash
   # Start the backend with detailed logging
   cd backend
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
   ```

## Amazon Advertising API Specific Considerations

### Required Headers for API Calls

When using the tokens to call Amazon Advertising API endpoints, ensure you include all required headers:

```python
headers = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
    "Amazon-Advertising-API-Scope": profile_id,  # Your advertising profile ID
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

### Token Expiration and Refresh

- Access tokens expire after 1 hour (3600 seconds)
- The backend automatically refreshes tokens when they're within 5 minutes (300 seconds) of expiring
- Refresh tokens are valid for much longer but should be rotated regularly

### Common Amazon Ads API Authentication Errors

1. **401 Unauthorized**: Token expired or invalid
2. **403 Forbidden**: Missing required scopes or profile access
3. **400 Bad Request**: Malformed request or missing headers

## Debug Checklist

- [ ] Verify only one active token exists in the database
- [ ] Check that the token hasn't expired
- [ ] Ensure the frontend is waiting for OAuth callback to complete
- [ ] Verify the backend server is running and accessible
- [ ] Check that environment variables are properly set
- [ ] Confirm the encryption key (FERNET_KEY) hasn't changed
- [ ] Review backend logs for any error messages
- [ ] Test the endpoints directly with curl to isolate frontend issues

## Need Further Help?

If the issue persists after trying these solutions:

1. Run the `debug_tokens.py` script and share the output
2. Check the backend logs for any error messages
3. Verify the Supabase connection and credentials
4. Ensure the frontend is calling the correct API endpoints

The current implementation is working correctly at the service level, so the issue is likely in the API layer or frontend-backend communication.