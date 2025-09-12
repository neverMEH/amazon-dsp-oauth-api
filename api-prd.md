# Amazon Advertising API OAuth Process Guide

## Overview

This guide explains the complete OAuth 2.0 authentication process for integrating with Amazon Advertising and AMC APIs. The implementation includes secure token storage, automatic refresh, and proper API client configuration.

## Prerequisites

### 1. Amazon Developer Console Setup

Before implementing OAuth, you need to:

1. Create an app in the Amazon Developer Console (Advertising API section)
2. Configure your redirect URIs for both local and production environments
3. Enable the required scope: `advertising::campaign_management`
4. Note your Client ID and Client Secret

### 2. Environment Configuration

Required environment variables:

```bash
# Amazon OAuth credentials
AMAZON_CLIENT_ID=amzn1.application-oa2-client.xxxxx
AMAZON_CLIENT_SECRET=your-secret-key
AMAZON_OAUTH_REDIRECT_URI=http://localhost:8001/api/auth/amazon/callback
AMAZON_SCOPE=advertising::campaign_management

# Encryption key for token storage (generate once, keep stable)
FERNET_KEY=your-generated-fernet-key

# Application settings
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
```

To generate a Fernet encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## OAuth Flow Architecture

The OAuth implementation consists of five main components:

1. **OAuth Endpoints** - Handle login initiation and callback
2. **Token Service** - Manages token encryption, storage, and validation
3. **Token Refresh Service** - Background service for automatic token renewal
4. **AMC API Client** - Handles authenticated API requests
5. **Database Layer** - Stores encrypted tokens

## Step-by-Step OAuth Process

### Step 1: Initiate Login

The OAuth flow begins when a user accesses the login endpoint:

**Endpoint:** `GET /api/auth/amazon/login`

**Process:**
1. Generate a CSRF state token for security
2. Build the Amazon authorization URL with required parameters:
   - `client_id`: Your Amazon app's client ID
   - `scope`: The permissions requested (e.g., `advertising::campaign_management`)
   - `response_type`: Set to `code` for authorization code flow
   - `redirect_uri`: Must match exactly what's configured in Amazon Developer Console
   - `state`: CSRF token for security

**Response:**
```json
{
  "auth_url": "https://www.amazon.com/ap/oa?client_id=...",
  "state": "generated-csrf-token"
}
```

The frontend redirects the user to the `auth_url` where they authenticate with Amazon.

### Step 2: Handle Callback

After successful authentication, Amazon redirects back to your callback URL:

**Endpoint:** `GET /api/auth/amazon/callback?code=AUTH_CODE&state=CSRF_TOKEN`

**Process:**
1. Verify the CSRF state token matches
2. Exchange the authorization code for tokens:
   ```json
   POST https://api.amazon.com/auth/o2/token
   {
     "grant_type": "authorization_code",
     "code": "AUTH_CODE",
     "client_id": "YOUR_CLIENT_ID",
     "client_secret": "YOUR_CLIENT_SECRET",
     "redirect_uri": "YOUR_REDIRECT_URI"
   }
   ```
3. Amazon returns access and refresh tokens:
   ```json
   {
     "access_token": "Atza|...",
     "refresh_token": "Atzr|...",
     "token_type": "bearer",
     "expires_in": 3600
   }
   ```

### Step 3: Token Storage

Tokens are encrypted before storage for security:

**Encryption Process:**
- Uses Fernet symmetric encryption
- Each token is individually encrypted
- Stores additional metadata:
  - `expires_at`: Calculated expiration timestamp
  - `updated_at`: Last update timestamp
  - `token_type`: Usually "bearer"

**Storage Structure:**
```json
{
  "access_token": "encrypted_access_token",
  "refresh_token": "encrypted_refresh_token",
  "token_type": "bearer",
  "expires_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T11:00:00"
}
```

### Step 4: Token Validation and Refresh

**Automatic Refresh Logic:**

When requesting a valid token:
1. Decrypt and check the current access token
2. If expiring within 5 minutes, initiate refresh
3. Use refresh token to get new access token:
   ```json
   POST https://api.amazon.com/auth/o2/token
   {
     "grant_type": "refresh_token",
     "refresh_token": "CURRENT_REFRESH_TOKEN",
     "client_id": "YOUR_CLIENT_ID",
     "client_secret": "YOUR_CLIENT_SECRET"
   }
   ```
4. Store new encrypted tokens
5. Return valid access token

**Background Refresh Service:**
- Runs every 10 minutes
- Refreshes tokens 15 minutes before expiry
- Tracks all users with active tokens
- Prevents token expiration during active sessions

### Step 5: Making Authenticated API Calls

Use the valid access token to make AMC API requests:

**Required Headers:**
```http
Amazon-Advertising-API-ClientId: YOUR_CLIENT_ID
Authorization: Bearer ACCESS_TOKEN
Amazon-Advertising-API-MarketplaceId: MARKETPLACE_ID
Amazon-Advertising-API-AdvertiserId: ENTITY_ID
Content-Type: application/json
```

**Example Usage:**
```python
async def make_amc_request(user_id: str, instance_id: str, entity_id: str):
    # Get valid token (auto-refreshes if needed)
    access_token = await token_service.get_valid_token(user_id)
    
    # Make API request with proper headers
    headers = {
        'Amazon-Advertising-API-ClientId': client_id,
        'Authorization': f'Bearer {access_token}',
        'Amazon-Advertising-API-MarketplaceId': 'ATVPDKIKX0DER',  # US marketplace
        'Amazon-Advertising-API-AdvertiserId': entity_id,
        'Content-Type': 'application/json'
    }
    
    response = await make_request(url, headers=headers, json=payload)
    return response
```

## Security Considerations

### Token Encryption
- All tokens are encrypted at rest using Fernet encryption
- Encryption key must remain stable across deployments
- Never commit encryption keys to version control

### CSRF Protection
- State parameter prevents CSRF attacks during OAuth flow
- State is validated before accepting callback

### Token Refresh Strategy
- Proactive refresh (15 minutes before expiry)
- Automatic retry on refresh failure
- Background service ensures tokens stay fresh

## Common Failure Modes

### Authentication Errors
- **401 Unauthorized**: Token expired or invalid
  - Solution: Ensure `get_valid_token()` is called
  
- **403 Forbidden**: Missing required headers or insufficient permissions
  - Solution: Verify all headers are included, check account access

### Configuration Issues
- **Redirect URI Mismatch**: Callback URL doesn't match Amazon configuration
  - Solution: Ensure exact match including protocol, port, and path
  
- **Encryption Errors**: Changed or missing FERNET_KEY
  - Solution: Use stable encryption key across all environments

### Token Refresh Problems
- **Refresh Token Expired**: Refresh tokens can expire after extended inactivity
  - Solution: User must re-authenticate through full OAuth flow

## Implementation Checklist

- [ ] Register app in Amazon Developer Console
- [ ] Configure redirect URIs for all environments
- [ ] Generate and securely store FERNET_KEY
- [ ] Implement OAuth login endpoint
- [ ] Implement OAuth callback handler
- [ ] Set up encrypted token storage
- [ ] Implement token refresh logic
- [ ] Configure background refresh service
- [ ] Add proper error handling
- [ ] Test full OAuth flow end-to-end
- [ ] Verify automatic token refresh
- [ ] Implement logout/token revocation

## Additional Resources

- [Amazon Advertising API Documentation](https://advertising.amazon.com/API/docs)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [Fernet Encryption Specification](https://github.com/fernet/spec)