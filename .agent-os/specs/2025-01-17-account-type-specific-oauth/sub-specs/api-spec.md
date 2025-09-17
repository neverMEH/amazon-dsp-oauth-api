# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-01-17-account-type-specific-oauth/spec.md

## Backend API Endpoints (Our Application)

### POST /api/v1/accounts/sponsored-ads/add

**Purpose:** Add Sponsored Ads accounts using existing OAuth tokens or initiate OAuth if needed
**Parameters:** None (uses session for user context)

**Flow:**
1. Check if user has valid OAuth tokens in `oauth_tokens` table
2. If no tokens, return OAuth URL for authentication
3. If tokens exist, fetch accounts from Amazon API and store them

**Response (No Existing Tokens):**
```json
{
  "requires_auth": true,
  "auth_url": "https://www.amazon.com/ap/oa?client_id=...",
  "state": "unique_state_token"
}
```

**Response (With Existing Tokens):**
```json
{
  "requires_auth": false,
  "accounts_added": 5,
  "accounts": [
    {
      "id": "uuid",
      "account_name": "Account Name",
      "amazon_account_id": "ENTITY1234567890",
      "account_type": "advertising",
      "status": "active",
      "connected_at": "2025-01-17T10:00:00Z",
      "metadata": {
        "alternateIds": [
          {
            "countryCode": "US",
            "entityId": "ENTITY1234567890",
            "profileId": 123456789
          }
        ],
        "countryCodes": ["US", "CA", "MX"]
      }
    }
  ]
}
```

**Amazon API Call Made (when tokens exist):**
- Endpoint: `POST https://advertising-api.amazon.com/adsAccounts/list`
- Uses stored access token from `oauth_tokens` table

**Errors:**
- 401: Unauthorized (no valid session)
- 403: Token expired (triggers token refresh)
- 500: Failed to fetch accounts from Amazon

### POST /api/v1/accounts/dsp/add

**Purpose:** Add DSP advertisers using existing OAuth tokens or initiate OAuth if needed
**Parameters:** None (uses session for user context)

**Flow:**
1. Check if user has valid OAuth tokens with DSP scope
2. If no tokens or missing DSP scope, return OAuth URL
3. If valid tokens exist, fetch advertisers from Amazon API and store them

**Response (No Tokens or Missing Scope):**
```json
{
  "requires_auth": true,
  "auth_url": "https://www.amazon.com/ap/oa?client_id=...",
  "state": "unique_state_token",
  "reason": "missing_dsp_scope"
}
```

**Response (With Valid Tokens):**
```json
{
  "requires_auth": false,
  "advertisers_added": 3,
  "advertisers": [
    {
      "id": "uuid",
      "account_name": "DSP Advertiser Name",
      "amazon_account_id": "AD123456789",
      "account_type": "dsp",
      "status": "active",
      "connected_at": "2025-01-17T10:00:00Z",
      "metadata": {
        "countryCode": "US",
        "currencyCode": "USD",
        "timeZone": "America/Los_Angeles",
        "type": "AMAZON_ATTRIBUTION"
      }
    }
  ]
}
```

**Amazon API Call Made (when tokens exist):**
- Endpoint: `GET https://advertising-api.amazon.com/dsp/advertisers`
- Uses stored access token with profile scope

**Errors:**
- 401: Unauthorized (no valid session)
- 403: Token expired or missing scope
- 500: Failed to fetch advertisers

### DELETE /api/v1/accounts/{account_id}

**Purpose:** Permanently delete an account from the local database
**Parameters:**
- `account_id` (path): UUID of the account to delete
**Response:**
```json
{
  "success": true,
  "message": "Account successfully deleted"
}
```
**Errors:**
- 404: Account not found
- 403: Forbidden (account belongs to different user)
- 500: Database deletion failed

## Amazon API Integration Details

### Amazon API Endpoints Called

#### For Sponsored Ads Accounts
**Endpoint:** `POST https://advertising-api.amazon.com/adsAccounts/list`
**Headers:**
```
Authorization: Bearer {access_token}
Amazon-Advertising-API-ClientId: {client_id}
Content-Type: application/vnd.listaccountsresource.v1+json
Accept: application/vnd.listaccountsresource.v1+json
```
**Request Body:**
```json
{
  "maxResults": 100,
  "nextToken": null
}
```

#### For DSP Advertisers
**Endpoint:** `GET https://advertising-api.amazon.com/dsp/advertisers`
**Headers:**
```
Authorization: Bearer {access_token}
Amazon-Advertising-API-ClientId: {client_id}
Amazon-Advertising-API-Scope: {profile_id}
Content-Type: application/json
```

## OAuth Scopes

### Sponsored Ads OAuth
Required scopes:
- `advertising::campaign_management`
- `advertising::account_management`

### DSP OAuth
Required scopes:
- `advertising::campaign_management`
- `advertising::dsp_campaigns`
- `advertising::account_management`

## OAuth Authorization URL
```
https://www.amazon.com/ap/oa?
  client_id={client_id}&
  scope={scopes}&
  response_type=code&
  redirect_uri={redirect_uri}&
  state={csrf_token}
```

## State Management

OAuth state tokens are stored in `oauth_states` table with:
- 10-minute expiration
- User ID association
- Flow type identifier (sponsored-ads or dsp)
- Single-use validation

## Rate Limiting

All OAuth endpoints are rate-limited:
- 5 requests per minute per user
- 20 requests per hour per user
- Returns 429 status with Retry-After header when exceeded