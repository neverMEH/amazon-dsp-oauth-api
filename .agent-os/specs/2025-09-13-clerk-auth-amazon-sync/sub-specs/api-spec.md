# API Specification: Clerk Authentication & Amazon Account Sync

## Overview
This specification defines the API endpoints for integrating Clerk authentication with Amazon Advertising API account synchronization. All endpoints follow RESTful principles and Amazon Advertising API patterns.

## Base Configuration

### Base URL
```
Production: https://api.yourdomain.com/v1
Staging: https://staging-api.yourdomain.com/v1
Development: http://localhost:8000/v1
```

### Authentication
- **Clerk JWT**: Bearer token in Authorization header for user endpoints
- **Amazon LWA**: OAuth 2.0 tokens for Amazon API interactions
- **Webhook Secret**: HMAC-SHA256 signature validation for Clerk webhooks

### Common Headers
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer {token}
X-Request-ID: {uuid}
X-API-Version: 1.0
```

## 1. Authentication Endpoints (Clerk Webhook)

### 1.1 Webhook Handler
Processes Clerk webhook events for user lifecycle management.

**Endpoint**: `POST /webhooks/clerk`

**Headers**:
```http
Content-Type: application/json
svix-id: {webhook_message_id}
svix-timestamp: {unix_timestamp}
svix-signature: {hmac_signature}
```

**Request Body**:
```json
{
  "data": {
    "id": "user_2NNEqL2nRZRRVlZkRJCH5z2XyZGM",
    "email_addresses": [
      {
        "email_address": "user@example.com",
        "id": "email_2NNEqL2nRZRRVlZkRJCH5z2XyZGM",
        "verification": {
          "status": "verified"
        }
      }
    ],
    "first_name": "John",
    "last_name": "Doe",
    "profile_image_url": "https://img.clerk.com/user.jpg",
    "created_at": 1654012591514,
    "updated_at": 1654012591514
  },
  "object": "event",
  "type": "user.created" | "user.updated" | "user.deleted"
}
```

**Response**:
```json
{
  "status": "processed",
  "user_id": "user_2NNEqL2nRZRRVlZkRJCH5z2XyZGM",
  "action": "created",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid webhook payload
- `401 Unauthorized`: Invalid webhook signature
- `409 Conflict`: User already exists
- `500 Internal Server Error`: Processing failure

### 1.2 Verify Session
Validates current user session with Clerk.

**Endpoint**: `GET /auth/verify`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
```

**Response**:
```json
{
  "valid": true,
  "user": {
    "clerk_id": "user_2NNEqL2nRZRRVlZkRJCH5z2XyZGM",
    "email": "user@example.com",
    "amazon_accounts": [
      {
        "profile_id": "ENTITY12345",
        "marketplace_id": "ATVPDKIKX0DER",
        "status": "active"
      }
    ]
  },
  "expires_at": "2024-01-15T12:00:00Z"
}
```

## 2. User Account Management Endpoints

### 2.1 Get User Profile
Retrieves complete user profile with Amazon account connections.

**Endpoint**: `GET /users/profile`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
```

**Response**:
```json
{
  "user": {
    "id": "usr_2NNEqL2nRZRRVlZkRJCH5z2XyZGM",
    "clerk_id": "user_2NNEqL2nRZRRVlZkRJCH5z2XyZGM",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "amazon_connections": [
      {
        "connection_id": "conn_abc123",
        "profile_id": "ENTITY12345",
        "profile_type": "seller",
        "marketplace_id": "ATVPDKIKX0DER",
        "marketplace_name": "US",
        "advertiser_name": "Example Store",
        "connected_at": "2024-01-15T11:00:00Z",
        "last_sync": "2024-01-15T11:30:00Z",
        "status": "active",
        "permissions": [
          "campaign:read",
          "campaign:write",
          "report:read"
        ]
      }
    ],
    "preferences": {
      "default_marketplace": "ATVPDKIKX0DER",
      "notification_settings": {
        "email": true,
        "webhook": false
      }
    }
  }
}
```

### 2.2 Update User Preferences
Updates user preferences and settings.

**Endpoint**: `PATCH /users/profile`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "preferences": {
    "default_marketplace": "ATVPDKIKX0DER",
    "notification_settings": {
      "email": true,
      "webhook": true
    },
    "auto_sync": true,
    "sync_frequency": "daily"
  }
}
```

**Response**:
```json
{
  "message": "Preferences updated successfully",
  "updated_fields": ["default_marketplace", "notification_settings", "auto_sync", "sync_frequency"],
  "user_id": "usr_2NNEqL2nRZRRVlZkRJCH5z2XyZGM"
}
```

### 2.3 List User Amazon Accounts
Retrieves all connected Amazon accounts for a user.

**Endpoint**: `GET /users/amazon-accounts`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
```

**Query Parameters**:
- `status`: Filter by status (active, inactive, expired)
- `marketplace_id`: Filter by marketplace
- `include_metrics`: Include performance metrics (true/false)

**Response**:
```json
{
  "accounts": [
    {
      "connection_id": "conn_abc123",
      "profile_id": "ENTITY12345",
      "profile_type": "seller",
      "marketplace": {
        "id": "ATVPDKIKX0DER",
        "name": "United States",
        "currency": "USD",
        "country_code": "US"
      },
      "advertiser": {
        "name": "Example Store",
        "id": "ADV123456",
        "type": "seller"
      },
      "connection": {
        "status": "active",
        "connected_at": "2024-01-15T11:00:00Z",
        "last_refreshed": "2024-01-15T14:00:00Z",
        "expires_at": "2024-02-14T11:00:00Z"
      },
      "permissions": {
        "scopes": [
          "advertising::campaign:read",
          "advertising::campaign:write",
          "advertising::report:read"
        ],
        "api_access": true,
        "sandbox_access": false
      },
      "metrics": {
        "campaigns_count": 15,
        "last_activity": "2024-01-15T13:45:00Z",
        "api_calls_today": 125
      }
    }
  ],
  "pagination": {
    "total": 2,
    "page": 1,
    "limit": 10
  }
}
```

## 3. Amazon OAuth Flow Endpoints

### 3.1 Initiate OAuth Flow
Generates Amazon LWA authorization URL for account connection.

**Endpoint**: `POST /amazon/oauth/authorize`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "redirect_uri": "https://app.yourdomain.com/amazon/callback",
  "marketplace_id": "ATVPDKIKX0DER",
  "state": {
    "user_id": "usr_2NNEqL2nRZRRVlZkRJCH5z2XyZGM",
    "session_id": "sess_abc123",
    "origin": "dashboard"
  },
  "scope": "advertising::campaign:edit advertising::report:read",
  "response_type": "code"
}
```

**Response**:
```json
{
  "authorization_url": "https://www.amazon.com/ap/oa?client_id=amzn1.application-oa2-client.xxxxx&scope=advertising::campaign:edit+advertising::report:read&response_type=code&redirect_uri=https://app.yourdomain.com/amazon/callback&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "state_token": "state_tkn_abc123",
  "expires_at": "2024-01-15T11:30:00Z"
}
```

### 3.2 OAuth Callback Handler
Processes OAuth callback from Amazon LWA.

**Endpoint**: `POST /amazon/oauth/callback`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "code": "ANDMxqpDqPkfWVNpNZBQ",
  "state": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "scope": "advertising::campaign:edit advertising::report:read",
  "redirect_uri": "https://app.yourdomain.com/amazon/callback"
}
```

**Response**:
```json
{
  "success": true,
  "connection": {
    "connection_id": "conn_new456",
    "profile_id": "ENTITY67890",
    "marketplace_id": "ATVPDKIKX0DER",
    "advertiser_name": "New Store",
    "status": "active",
    "connected_at": "2024-01-15T11:15:00Z"
  },
  "tokens": {
    "expires_in": 3600,
    "token_type": "bearer"
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid authorization code
- `401 Unauthorized`: State mismatch or expired
- `403 Forbidden`: User not authorized for this marketplace
- `409 Conflict`: Account already connected

### 3.3 Refresh Amazon Token
Refreshes expired Amazon LWA access token.

**Endpoint**: `POST /amazon/oauth/refresh`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "connection_id": "conn_abc123"
}
```

**Response**:
```json
{
  "success": true,
  "connection_id": "conn_abc123",
  "refreshed_at": "2024-01-15T14:00:00Z",
  "expires_at": "2024-01-15T15:00:00Z",
  "token_status": "active"
}
```

### 3.4 Revoke Amazon Connection
Disconnects an Amazon account from user profile.

**Endpoint**: `DELETE /amazon/oauth/revoke/{connection_id}`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
```

**Response**:
```json
{
  "success": true,
  "message": "Amazon account disconnected successfully",
  "connection_id": "conn_abc123",
  "revoked_at": "2024-01-15T15:30:00Z"
}
```

## 4. Account Synchronization Endpoints

### 4.1 Trigger Manual Sync
Initiates manual synchronization of Amazon account data.

**Endpoint**: `POST /sync/trigger`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "connection_id": "conn_abc123",
  "sync_type": "full" | "incremental",
  "resources": [
    "profiles",
    "campaigns",
    "ad_groups",
    "keywords",
    "reports"
  ],
  "date_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-15"
  }
}
```

**Response**:
```json
{
  "sync_job": {
    "job_id": "sync_job_xyz789",
    "status": "queued",
    "connection_id": "conn_abc123",
    "sync_type": "full",
    "resources": ["profiles", "campaigns"],
    "created_at": "2024-01-15T11:30:00Z",
    "estimated_completion": "2024-01-15T11:35:00Z"
  }
}
```

### 4.2 Get Sync Status
Retrieves status of ongoing or completed sync operations.

**Endpoint**: `GET /sync/status/{job_id}`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
```

**Response**:
```json
{
  "job": {
    "job_id": "sync_job_xyz789",
    "status": "in_progress",
    "connection_id": "conn_abc123",
    "progress": {
      "percentage": 65,
      "current_step": "Syncing campaigns",
      "steps_completed": 3,
      "total_steps": 5
    },
    "resources_synced": {
      "profiles": {
        "status": "completed",
        "count": 1,
        "duration_ms": 450
      },
      "campaigns": {
        "status": "in_progress",
        "count": 45,
        "processed": 30
      },
      "ad_groups": {
        "status": "pending"
      }
    },
    "started_at": "2024-01-15T11:30:15Z",
    "updated_at": "2024-01-15T11:32:45Z"
  }
}
```

### 4.3 Get Sync History
Retrieves history of sync operations for a connection.

**Endpoint**: `GET /sync/history`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
```

**Query Parameters**:
- `connection_id`: Filter by connection (required)
- `status`: Filter by status (completed, failed, in_progress)
- `start_date`: Filter by date range start
- `end_date`: Filter by date range end
- `limit`: Results per page (default: 20, max: 100)
- `offset`: Pagination offset

**Response**:
```json
{
  "sync_history": [
    {
      "job_id": "sync_job_xyz789",
      "connection_id": "conn_abc123",
      "sync_type": "incremental",
      "status": "completed",
      "started_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T10:02:30Z",
      "duration_seconds": 150,
      "summary": {
        "profiles": { "synced": 1, "errors": 0 },
        "campaigns": { "synced": 125, "errors": 2 },
        "ad_groups": { "synced": 450, "errors": 0 },
        "keywords": { "synced": 3200, "errors": 5 }
      },
      "errors": [
        {
          "resource": "campaigns",
          "error_code": "RATE_LIMIT",
          "message": "API rate limit exceeded, retrying",
          "timestamp": "2024-01-15T10:01:45Z"
        }
      ]
    }
  ],
  "pagination": {
    "total": 45,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### 4.4 Configure Auto-Sync
Configures automatic synchronization settings for a connection.

**Endpoint**: `PUT /sync/auto-config`

**Headers**:
```http
Authorization: Bearer {clerk_session_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "connection_id": "conn_abc123",
  "enabled": true,
  "schedule": {
    "frequency": "daily" | "hourly" | "weekly",
    "time": "03:00",
    "timezone": "America/New_York",
    "days_of_week": [1, 3, 5]
  },
  "sync_config": {
    "resources": ["campaigns", "ad_groups", "keywords"],
    "incremental": true,
    "lookback_days": 7,
    "retry_on_failure": true,
    "max_retries": 3
  },
  "notifications": {
    "on_success": false,
    "on_failure": true,
    "webhook_url": "https://app.yourdomain.com/webhooks/sync"
  }
}
```

**Response**:
```json
{
  "config": {
    "config_id": "cfg_auto123",
    "connection_id": "conn_abc123",
    "enabled": true,
    "next_run": "2024-01-16T03:00:00Z",
    "created_at": "2024-01-15T11:45:00Z",
    "updated_at": "2024-01-15T11:45:00Z"
  }
}
```

## Error Handling

### Standard Error Response Format
All error responses follow this structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "marketplace_id",
      "reason": "Invalid marketplace identifier"
    },
    "request_id": "req_abc123xyz",
    "timestamp": "2024-01-15T11:30:00Z"
  }
}
```

### Error Codes
| Code | HTTP Status | Description |
|------|------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or expired authentication token |
| `FORBIDDEN` | 403 | User lacks required permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate) |
| `RATE_LIMIT` | 429 | API rate limit exceeded |
| `AMAZON_API_ERROR` | 502 | Amazon API request failed |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Rate Limiting
All endpoints implement rate limiting following Amazon Advertising API patterns:

**Response Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
Retry-After: 60
```

## Webhook Events

### Outbound Webhooks
The system can send webhooks for the following events:

```json
{
  "event_id": "evt_abc123",
  "event_type": "sync.completed",
  "timestamp": "2024-01-15T11:35:00Z",
  "data": {
    "connection_id": "conn_abc123",
    "job_id": "sync_job_xyz789",
    "status": "completed",
    "summary": {
      "duration_seconds": 150,
      "resources_synced": 4,
      "total_records": 3776,
      "errors": 7
    }
  },
  "signature": "sha256=xxxxx"
}
```

**Event Types**:
- `user.connected`: New Amazon account connected
- `user.disconnected`: Amazon account disconnected
- `sync.started`: Sync operation started
- `sync.completed`: Sync operation completed
- `sync.failed`: Sync operation failed
- `token.refreshed`: Amazon token refreshed
- `token.expired`: Amazon token expired

## Security Considerations

1. **Authentication**: All user endpoints require valid Clerk JWT tokens
2. **Authorization**: Users can only access their own connected accounts
3. **Data Encryption**: All sensitive data encrypted at rest using AES-256
4. **Token Storage**: Amazon refresh tokens stored encrypted in database
5. **Audit Logging**: All API calls logged with user ID and action
6. **CORS**: Configured for specific allowed origins only
7. **Input Validation**: All inputs validated against JSON schemas
8. **SQL Injection**: Parameterized queries for all database operations
9. **XSS Protection**: Content-Security-Policy headers on all responses
10. **Rate Limiting**: Per-user and per-IP rate limiting implemented

## Amazon Advertising API Integration

### Required Scopes
```
advertising::campaign:edit
advertising::report:read
advertising::account:read
```

### Profile Types
- `seller`: Seller Central accounts
- `vendor`: Vendor Central accounts
- `agency`: Agency accounts

### Marketplace IDs
| Marketplace | ID | Country |
|------------|----|---------| 
| US | ATVPDKIKX0DER | United States |
| CA | A2EUQ1WTGCTBG2 | Canada |
| MX | A1AM78C64UM0Y8 | Mexico |
| BR | A2Q3Y263D00KWC | Brazil |
| UK | A1F83G8C2ARO7P | United Kingdom |
| DE | A1PA6795UKMFR9 | Germany |
| FR | A13V1IB3VIYZZH | France |
| IT | APJ6JRA9NG5V4 | Italy |
| ES | A1RKKUPIHCS9HS | Spain |
| JP | A1VC38T7YXB528 | Japan |
| AU | A39IBJ37TRP1C6 | Australia |

## Version History

- **v1.0.0** (2025-01-13): Initial specification
  - Clerk webhook integration
  - Amazon OAuth flow
  - Basic sync operations
  - User management endpoints