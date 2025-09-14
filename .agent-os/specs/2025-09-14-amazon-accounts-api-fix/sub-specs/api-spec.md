# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-14-amazon-accounts-api-fix/spec.md

## Endpoints

### POST /api/v1/accounts/amazon-ads-accounts

**Purpose:** Retrieve and synchronize Amazon advertising accounts with pagination support

**Parameters:**
- Query Parameters:
  - `force_refresh` (boolean, optional): Force fresh data from Amazon API
  - `page_size` (integer, optional): Number of accounts per page (default: 100, max: 500)
  - `next_token` (string, optional): Pagination token for next page

**Request Headers:**
- `Authorization: Bearer {clerk_token}`
- `Content-Type: application/json`

**Response:**
```json
{
  "success": true,
  "data": {
    "accounts": [
      {
        "id": "uuid",
        "account_name": "string",
        "amazon_account_id": "string",
        "marketplace_id": "string",
        "marketplace_name": "string",
        "account_type": "ADVERTISER|AGENCY",
        "status": "ACTIVE|SUSPENDED|TERMINATED",
        "is_default": false,
        "connected_at": "2025-01-14T10:00:00Z",
        "last_synced_at": "2025-01-14T10:00:00Z",
        "metadata": {
          "country_code": "US",
          "currency_code": "USD",
          "timezone": "America/Los_Angeles",
          "linked_profiles": []
        }
      }
    ],
    "pagination": {
      "total_count": 150,
      "page_size": 100,
      "has_more": true,
      "next_token": "eyJuZXh0IjoiMTAwIn0="
    },
    "sync_status": {
      "last_sync": "2025-01-14T10:00:00Z",
      "sync_duration_ms": 2500,
      "accounts_synced": 100,
      "accounts_failed": 0
    }
  }
}
```

**Errors:**
- `401 Unauthorized`: Invalid or expired authentication
- `403 Forbidden`: User lacks permissions
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server or Amazon API error

### GET /api/v1/accounts/amazon-profiles

**Purpose:** Retrieve Amazon advertising profiles with pagination support

**Parameters:**
- Query Parameters:
  - `account_id` (string, optional): Filter by specific account ID
  - `page_size` (integer, optional): Number of profiles per page (default: 50, max: 200)
  - `next_token` (string, optional): Pagination token for next page

**Response:**
```json
{
  "success": true,
  "data": {
    "profiles": [
      {
        "profile_id": "string",
        "profile_name": "string",
        "account_id": "string",
        "marketplace_id": "string",
        "profile_type": "vendor|seller",
        "status": "active|inactive"
      }
    ],
    "pagination": {
      "total_count": 25,
      "page_size": 50,
      "has_more": false,
      "next_token": null
    }
  }
}
```

### POST /api/v1/accounts/batch

**Purpose:** Perform batch operations on multiple accounts

**Parameters:**
- Request Body:
```json
{
  "operation": "sync|disconnect|update",
  "account_ids": ["uuid1", "uuid2"],
  "options": {
    "force_refresh": true,
    "update_metadata": {}
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "operation": "sync",
    "total_accounts": 2,
    "successful": 2,
    "failed": 0,
    "results": [
      {
        "account_id": "uuid1",
        "status": "success",
        "message": "Account synchronized successfully"
      }
    ]
  }
}
```

### GET /api/v1/accounts/health

**Purpose:** Check health status of account connections and token validity

**Response:**
```json
{
  "success": true,
  "data": {
    "overall_status": "healthy|degraded|error",
    "token_status": {
      "is_valid": true,
      "expires_at": "2025-01-14T12:00:00Z",
      "refresh_scheduled": true,
      "last_refresh": "2025-01-14T10:00:00Z"
    },
    "account_stats": {
      "total_accounts": 150,
      "active_accounts": 145,
      "suspended_accounts": 3,
      "pending_sync": 2
    },
    "sync_health": {
      "last_successful_sync": "2025-01-14T10:00:00Z",
      "failed_sync_count": 0,
      "next_scheduled_sync": "2025-01-14T11:00:00Z"
    },
    "rate_limit_status": {
      "requests_remaining": 950,
      "reset_time": "2025-01-14T11:00:00Z",
      "current_retry_after": null
    }
  }
}
```

### POST /api/v1/accounts/refresh-token

**Purpose:** Manually trigger token refresh

**Response:**
```json
{
  "success": true,
  "data": {
    "token_refreshed": true,
    "new_expiry": "2025-01-14T13:00:00Z",
    "refresh_count": 5
  }
}
```

**Errors:**
- `400 Bad Request`: Token cannot be refreshed (invalid refresh token)
- `401 Unauthorized`: User not authenticated

## Controllers

### AccountController

**Actions:**
- `list_amazon_accounts()`: Retrieve and paginate Amazon accounts
- `sync_accounts()`: Force synchronization with Amazon API
- `batch_operation()`: Handle batch account operations
- `check_health()`: Monitor account and token health

**Business Logic:**
- Automatic token refresh when expired
- Rate limit handling with exponential backoff
- Pagination token generation and validation
- Account deduplication during sync

**Error Handling:**
- Catch and log Amazon API errors
- Retry failed requests with backoff
- Return user-friendly error messages
- Track error patterns for monitoring

### TokenController

**Actions:**
- `refresh_token()`: Manually refresh access token
- `validate_token()`: Check token validity
- `schedule_refresh()`: Set up proactive refresh

**Business Logic:**
- Encrypt tokens before storage
- Decrypt only when needed for API calls
- Track refresh history and failures
- Alert on repeated refresh failures

## Integration Points

### Amazon Advertising API
- **Account Management API v1**: Primary account data source
- **Profiles API v2**: Legacy profile support
- **Rate Limits**: 2 requests/second for most endpoints

### Supabase Database
- Store account data with encryption
- Maintain sync history
- Track rate limit metrics

### Frontend Dashboard
- Real-time WebSocket updates for sync status
- Optimistic UI updates for better UX
- Error boundary for graceful failure handling

## Rate Limiting Strategy

1. **Client-side throttling**: Maximum 1 request per second
2. **Server-side queue**: Buffer requests during high load
3. **Exponential backoff**: Start at 1s, max 60s delay
4. **Retry-After header**: Respect Amazon's rate limit guidance
5. **Circuit breaker**: Stop requests after 5 consecutive failures