# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-12-oauth-foundation-infrastructure/spec.md

## Base Configuration

- **Base URL**: `https://your-app.up.railway.app/api/v1`
- **Authentication**: OAuth 2.0 with Amazon DSP Campaign Insights
- **Content-Type**: `application/json`
- **API Version**: v1

## Endpoints

### GET /health

**Purpose:** Health check endpoint for Railway monitoring and service availability verification
**Parameters:** None
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-12T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "token_refresh": "running",
    "last_refresh": "2025-09-12T10:25:00Z"
  }
}
```
**Errors:**
- `503 Service Unavailable`: Database connection failed or critical service down

### GET /auth/amazon/login

**Purpose:** Initiate OAuth 2.0 authorization flow with Amazon Advertising API
**Parameters:**
- `redirect_uri` (optional): Override default redirect URI for development
- `force_refresh` (optional): Force new authentication even if valid token exists

**Response:**
```json
{
  "auth_url": "https://www.amazon.com/ap/oa?client_id=amzn1.application-oa2-client.xxx&scope=advertising::campaign_management&response_type=code&redirect_uri=https://your-app.up.railway.app/api/v1/auth/amazon/callback&state=abc123xyz",
  "state": "abc123xyz",
  "expires_in": 600
}
```
**Errors:**
- `500 Internal Server Error`: Failed to generate state token or build auth URL
- `409 Conflict`: Active token already exists (when force_refresh is false)

### GET /auth/amazon/callback

**Purpose:** Handle OAuth callback from Amazon with authorization code
**Parameters:**
- `code` (required): Authorization code from Amazon
- `state` (required): CSRF state token for validation
- `error` (optional): Error code if authorization failed
- `error_description` (optional): Human-readable error description

**Response:**
```json
{
  "status": "success",
  "message": "Authentication successful",
  "token_info": {
    "expires_at": "2025-09-12T11:30:00Z",
    "scope": "advertising::campaign_management",
    "token_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```
**Errors:**
- `400 Bad Request`: Missing required parameters or invalid state token
- `401 Unauthorized`: Invalid authorization code or Amazon API rejection
- `408 Request Timeout`: State token expired
- `500 Internal Server Error`: Token storage or encryption failure

### GET /auth/status

**Purpose:** Check current authentication status and token validity
**Parameters:** None

**Response:**
```json
{
  "authenticated": true,
  "token_valid": true,
  "expires_at": "2025-09-12T11:30:00Z",
  "refresh_count": 5,
  "last_refresh": "2025-09-12T10:25:00Z",
  "scope": "advertising::campaign_management"
}
```
**Errors:**
- `404 Not Found`: No active token found

### POST /auth/refresh

**Purpose:** Manually trigger token refresh (primarily for testing)
**Parameters:** None
**Headers:**
- `X-Admin-Key`: Admin key for manual refresh authorization

**Response:**
```json
{
  "status": "success",
  "message": "Token refreshed successfully",
  "new_expiry": "2025-09-12T12:30:00Z",
  "refresh_count": 6
}
```
**Errors:**
- `401 Unauthorized`: Missing or invalid admin key
- `404 Not Found`: No active token to refresh
- `422 Unprocessable Entity`: Token not eligible for refresh (too early)
- `503 Service Unavailable`: Amazon API unavailable or refresh failed

### DELETE /auth/revoke

**Purpose:** Revoke current tokens and clear authentication
**Parameters:** None
**Headers:**
- `X-Admin-Key`: Admin key for revocation authorization

**Response:**
```json
{
  "status": "success",
  "message": "Tokens revoked successfully",
  "revoked_at": "2025-09-12T10:30:00Z"
}
```
**Errors:**
- `401 Unauthorized`: Missing or invalid admin key
- `404 Not Found`: No active token to revoke

### GET /auth/audit

**Purpose:** Retrieve authentication audit logs for debugging
**Parameters:**
- `limit` (optional, default: 50): Number of audit entries to return
- `offset` (optional, default: 0): Pagination offset
- `event_type` (optional): Filter by event type (login, refresh, error, revoke)
- `status` (optional): Filter by status (success, failure)

**Response:**
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "events": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "refresh",
      "event_status": "success",
      "created_at": "2025-09-12T10:25:00Z",
      "metadata": {
        "refresh_count": 5,
        "token_id": "660e8400-e29b-41d4-a716-446655440000"
      }
    }
  ]
}
```
**Errors:**
- `400 Bad Request`: Invalid query parameters

## Controllers

### AuthController
**Location:** `app/api/v1/auth.py`

**Actions:**
- `initiate_login()`: Generate OAuth authorization URL with state token
- `handle_callback()`: Process OAuth callback and store tokens
- `get_auth_status()`: Return current authentication status
- `manual_refresh()`: Trigger manual token refresh
- `revoke_tokens()`: Revoke and clear all tokens
- `get_audit_logs()`: Retrieve audit log entries

**Business Logic:**
- State tokens expire after 10 minutes for security
- Only one active token set allowed (single-user system)
- Automatic audit logging for all authentication events
- Token encryption/decryption handled transparently

### HealthController
**Location:** `app/api/v1/health.py`

**Actions:**
- `health_check()`: Return service health status
- `check_database()`: Verify Supabase connection
- `check_refresh_service()`: Verify background service status

**Business Logic:**
- Health check includes all critical service statuses
- Database check uses lightweight query
- Returns degraded status if non-critical services fail

## Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "INVALID_STATE_TOKEN",
    "message": "The state token is invalid or has expired",
    "details": {
      "provided_state": "xyz789",
      "timestamp": "2025-09-12T10:30:00Z"
    }
  }
}
```

### Error Codes
- `INVALID_STATE_TOKEN`: CSRF state validation failed
- `TOKEN_EXCHANGE_FAILED`: Amazon API rejected authorization code
- `ENCRYPTION_ERROR`: Token encryption/decryption failed
- `DATABASE_ERROR`: Supabase operation failed
- `REFRESH_FAILED`: Token refresh attempt failed
- `RATE_LIMITED`: Amazon API rate limit exceeded
- `SERVICE_UNAVAILABLE`: Critical service is down

## Rate Limiting

### Internal Rate Limits
- OAuth login: 10 requests per hour
- Manual refresh: 5 requests per hour
- Audit log queries: 100 requests per hour

### Amazon API Rate Limits
- Handled automatically with exponential backoff
- Maximum 5 retry attempts
- Backoff formula: `2^attempt * 1000ms`

## Integration Points

### Amazon OAuth Endpoints
- **Authorization**: `https://www.amazon.com/ap/oa`
- **Token Exchange**: `https://api.amazon.com/auth/o2/token`
- **Token Refresh**: `https://api.amazon.com/auth/o2/token`

### Supabase Integration
- Connection pooling handled by Supabase client
- Automatic reconnection on connection loss
- Transaction support for token storage operations

### Background Service Integration
- Refresh service status available via health endpoint
- Manual refresh triggers same logic as automatic refresh
- Audit events logged for all background operations