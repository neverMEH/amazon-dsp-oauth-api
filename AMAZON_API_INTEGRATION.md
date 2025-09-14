# Amazon API Integration Documentation

## Overview

This document describes how the application integrates with Amazon's Advertising API to retrieve and manage account information. The system implements OAuth 2.0 authentication, retrieves account lists from Amazon, and stores them in a PostgreSQL database using Supabase.

## Architecture Flow

```
┌─────────┐     ┌──────────┐     ┌────────────┐     ┌──────────┐
│  User   │────▶│ Frontend │────▶│  Backend   │────▶│  Amazon  │
│         │     │  (React) │     │  (FastAPI) │     │   API    │
└─────────┘     └──────────┘     └────────────┘     └──────────┘
                      │                 │
                      │                 ▼
                      │          ┌────────────┐
                      └─────────▶│  Supabase  │
                                 │ PostgreSQL │
                                 └────────────┘
```

## Authentication Flow

### 1. OAuth 2.0 Implementation

The system uses Amazon's OAuth 2.0 flow for authentication:

1. **Authorization Request** (`amazon_oauth_service.py:43-74`)
   - Generates OAuth URL with required scopes
   - Creates CSRF protection state token
   - Required scopes:
     - `advertising::campaign_management`
     - `advertising::account_management`
     - `advertising::dsp_campaigns`
     - `advertising::reporting`

2. **Token Exchange** (`amazon_oauth_service.py:100-188`)
   - Exchanges authorization code for access/refresh tokens
   - Tokens are encrypted using Fernet encryption
   - Stored in `oauth_tokens` table

3. **Token Refresh** (`amazon_oauth_service.py:190-264`)
   - Automatically refreshes expired tokens
   - Updates token in database with new expiration

## Account Retrieval Process

### 1. API Endpoints

The application provides two main endpoints for retrieving Amazon accounts:

#### `/api/v1/accounts/amazon-ads-accounts` (`accounts.py:175-312`)
- **Amazon API**: POST `https://advertising-api.amazon.com/adsAccounts/list`
- **Method**: POST (not GET as incorrectly stated in code comments)
- **Content-Type**: `application/vnd.listaccountsresource.v1+json`
- **Purpose**: Retrieves full account list using Account Management API v1
- **Request Body**:
  ```json
  {
    "maxResults": 100,
    "nextToken": "string" // for pagination
  }
  ```
- **Response**: Detailed account information including:
  - Account ID, name, type (ADVERTISER/AGENCY)
  - Status (ACTIVE/SUSPENDED/TERMINATED)
  - Marketplace information
  - Linked profiles
- **Pagination**: Supports pagination via nextToken

#### `/api/v1/accounts/amazon-profiles` (`accounts.py:315-443`)
- **Amazon API**: GET `https://advertising-api.amazon.com/v2/profiles`
- **Method**: GET
- **Purpose**: Retrieves advertising profiles (legacy endpoint)
- **Response**: Profile information for backwards compatibility
- **Note**: Currently lacks pagination implementation

### 2. Service Layer

#### `AmazonAccountService` (`account_service.py`)

Handles direct communication with Amazon's API:

1. **`list_ads_accounts()`** (lines 154-280)
   - Implements pagination for large account lists
   - Handles rate limiting (429 responses)
   - Returns comprehensive account data

2. **`list_profiles()`** (lines 23-89)
   - Legacy profile endpoint support
   - Returns basic profile information

3. **`list_dsp_accounts()`** (lines 282-352)
   - Retrieves DSP-specific accounts
   - Requires profile ID scope

### 3. Data Flow

1. **User Authentication Check**
   - Verify user has valid Clerk authentication
   - Get user's database UUID from context

2. **Token Validation**
   - Retrieve encrypted tokens from database
   - Decrypt using `TokenService`
   - Check expiration and refresh if needed

3. **API Call to Amazon**
   - Add required headers (Authorization, ClientId)
   - Handle pagination for large result sets
   - Process rate limiting with retry logic

4. **Data Processing & Storage**
   - Transform Amazon's response to internal schema
   - Check for existing accounts in database
   - Create new or update existing records

## Database Storage Structure

### Tables

#### 1. `users` Table
```sql
- id: UUID (Primary Key)
- clerk_user_id: VARCHAR(255) - Clerk authentication ID
- email: VARCHAR(255)
- first_name, last_name: VARCHAR(100)
- profile_image_url: TEXT
- created_at, updated_at: TIMESTAMP
- last_login_at: TIMESTAMP
```

#### 2. `user_accounts` Table
```sql
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key → users)
- account_name: VARCHAR(255)
- amazon_account_id: VARCHAR(255)
- marketplace_id: VARCHAR(50)
- account_type: VARCHAR(50) - 'advertising', 'vendor', 'seller'
- is_default: BOOLEAN
- status: VARCHAR(50) - 'active', 'inactive', 'suspended', 'pending'
- connected_at: TIMESTAMP
- last_synced_at: TIMESTAMP
- metadata: JSONB - Stores additional account data
```

#### 3. `oauth_tokens` Table
```sql
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key → users)
- encrypted_access_token: TEXT - Fernet encrypted
- encrypted_refresh_token: TEXT - Fernet encrypted
- token_type: VARCHAR(50)
- expires_at: TIMESTAMP
- scope: TEXT
- refresh_count: INTEGER
- last_refresh: TIMESTAMP
```

### Data Relationships
```
users (1) ──────── (n) user_accounts
  │
  └──────── (1) oauth_tokens
```

## Storage Process

### 1. Account Creation/Update Logic (`accounts.py:236-279`)

When accounts are retrieved from Amazon:

1. **Check Existence**
   ```python
   existing = supabase.table("user_accounts").select("*")
       .eq("user_id", user_id)
       .eq("amazon_account_id", account.get("accountId"))
       .execute()
   ```

2. **Create New Account**
   - Generate new UUID
   - Map Amazon fields to database schema
   - Store metadata in JSONB field:
     - country_code, currency_code, timezone
     - marketplace_name
     - created_date, last_updated_date
     - linked_profiles array

3. **Update Existing Account**
   - Update last_synced_at timestamp
   - Merge new metadata with existing
   - Preserve historical data

### 2. Token Storage (`token_service.py`)

Tokens are encrypted before storage:
1. Generate Fernet key from environment variable
2. Encrypt access and refresh tokens
3. Store encrypted tokens in database
4. Decrypt only when needed for API calls

## Account Model (`amazon_account.py`)

The `AmazonAccount` class provides:
- Data validation and type safety
- Marketplace ID to name mapping (89 lines)
- Conversion methods for database operations
- Active status checking
- Default account management

## Error Handling

### Rate Limiting
- Detects 429 status codes
- Extracts Retry-After header
- Returns appropriate retry information to client

### Token Expiration
- Automatic refresh when token expires
- Falls back to re-authentication if refresh fails
- Updates database with new tokens

### Network Errors
- Timeout handling (30 second default)
- Connection error recovery
- Detailed error logging with context

## Security Considerations

1. **Token Encryption**
   - All tokens encrypted at rest using Fernet
   - Encryption key stored in environment variables
   - Tokens never logged or exposed

2. **CSRF Protection**
   - State tokens for OAuth flow
   - Validated on callback
   - Expires after 10 minutes

3. **Row Level Security**
   - PostgreSQL RLS policies
   - Users can only access their own data
   - Enforced at database level

4. **Authentication Middleware**
   - Clerk JWT validation
   - User context injection
   - Database user synchronization

## API Integration Points

### Amazon Advertising API Endpoints Used:
1. **Account Management API v1**
   - `POST /adsAccounts/list` - Primary account listing
   - Content-Type: `application/vnd.listaccountsresource.v1+json`
   - Supports pagination with nextToken

2. **Profiles API v2**
   - `GET /v2/profiles` - Legacy profile support
   - `GET /v2/profiles/{profileId}` - Individual profile details
   - Content-Type: `application/json`

3. **DSP API**
   - `GET /dsp/accounts` - DSP account listing
   - Requires profile scope in headers

### Required Headers:
- `Authorization: Bearer {access_token}`
- `Amazon-Advertising-API-ClientId: {client_id}`
- `Amazon-Advertising-API-Scope: {profile_id}` (for profile-specific calls)
- `Content-Type: application/vnd.listaccountsresource.v1+json` (for Account Management API)
- `Content-Type: application/json` (for other endpoints)
- `Accept: application/json`

## Batch Operations Support

The system supports batch operations (`accounts.py:862-1023`):
- **sync**: Refresh account data from Amazon
- **disconnect**: Mark multiple accounts as disconnected
- **update**: Update account metadata in bulk

## Health Monitoring

Account health endpoint (`accounts.py:658-745`) provides:
- Token validity status
- Last sync timestamps
- Account status (healthy/degraded/error)
- Re-authorization requirements

## Currently Missing Features

Based on Amazon's API documentation, the following features are not yet implemented:

### 1. Account Registration (`RegisterAdsAccount`)
- **Endpoint**: `POST /adsAccounts/register`
- **Purpose**: Register/link new advertising accounts
- **Use Case**: Onboarding new advertisers or linking existing accounts

### 2. Advanced DSP Features
- Campaign management endpoints
- Audience targeting APIs
- Creative management
- Real-time bidding configurations

### 3. Reporting API
- **Endpoints**: Various `/reports` endpoints
- **Purpose**: Generate and retrieve advertising performance reports
- **Features**: Custom metrics, scheduled reports, data exports

### 4. Profiles API Pagination
- The current implementation of `/v2/profiles` doesn't handle pagination
- May cause issues with accounts having many profiles

## Known Issues to Address

1. **Documentation Inconsistency**: Code comments incorrectly state GET for Account Management API
2. **Rate Limiting**: Could be enhanced with exponential backoff
3. **Token Refresh**: Consider implementing proactive refresh before expiration

## Summary

The integration follows a robust pattern:
1. **Secure Authentication** - OAuth 2.0 with encrypted token storage
2. **Comprehensive Data Retrieval** - Multiple API endpoints for complete account information
3. **Efficient Storage** - PostgreSQL with JSONB for flexible metadata
4. **Error Resilience** - Automatic token refresh, rate limit handling
5. **Security First** - Encryption at rest, RLS policies, CSRF protection

This architecture ensures reliable synchronization between Amazon's Advertising API and the application's database while maintaining security and performance standards.