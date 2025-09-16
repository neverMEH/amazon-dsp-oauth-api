# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-16-dsp-advertiser-seats/spec.md

> Created: 2025-09-16
> Version: 1.0.0

## Endpoints

### GET /api/v1/accounts/dsp/{advertiser_id}/seats

**Purpose:** Retrieve current seat allocations for a DSP advertiser across advertising exchanges

**Authentication:** Required - Clerk user authentication via Bearer token

**Parameters:**
- **Path Parameters:**
  - `advertiser_id` (string, required): DSP Advertiser ID (numeric string pattern: ^[0-9]+$)

- **Query Parameters:**
  - `exchange_ids` (array[string], optional): Filter results by specific exchange IDs
  - `max_results` (integer, optional): Maximum results per page (1-200, default: 200)
  - `next_token` (string, optional): Pagination token from previous response
  - `profile_id` (string, optional): Additional profile ID for filtering

**Request Headers:**
```
Authorization: Bearer {clerk_token}
Content-Type: application/json
```

**Response:** 200 OK
```json
{
  "advertiserSeats": [
    {
      "advertiserId": "123456789",
      "currentSeats": [
        {
          "exchangeId": "1",
          "exchangeName": "Google Ad Manager",
          "dealCreationId": "DEAL-ABC-123",
          "spendTrackingId": "TRACK-XYZ-789"
        },
        {
          "exchangeId": "2",
          "exchangeName": "Amazon Publisher Services",
          "dealCreationId": null,
          "spendTrackingId": "APS-TRACK-456"
        }
      ]
    }
  ],
  "nextToken": "eyJsYXN0S2V5IjoiMTIzIn0=",
  "timestamp": "2025-09-16T10:30:00Z",
  "cached": false,
  "syncStatus": "success"
}
```

**Errors:**
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: User doesn't own the specified DSP advertiser account
- `404 Not Found`: Advertiser ID not found or not a DSP account
- `429 Too Many Requests`: Rate limit exceeded (includes Retry-After header)
- `500 Internal Server Error`: Amazon API error or service failure

### POST /api/v1/accounts/dsp/{advertiser_id}/seats/refresh

**Purpose:** Force refresh of seat data for a DSP advertiser, bypassing cache

**Authentication:** Required - Clerk user authentication via Bearer token

**Parameters:**
- **Path Parameters:**
  - `advertiser_id` (string, required): DSP Advertiser ID

**Request Headers:**
```
Authorization: Bearer {clerk_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "force": true,
  "include_sync_log": false
}
```

**Response:** 200 OK
```json
{
  "success": true,
  "seats_updated": 5,
  "last_sync": "2025-09-16T10:30:00Z",
  "sync_log_id": "uuid-here"
}
```

**Errors:**
- `401 Unauthorized`: Token refresh failed
- `403 Forbidden`: Insufficient permissions for DSP API
- `409 Conflict`: Sync already in progress
- `503 Service Unavailable`: Amazon API temporarily unavailable

### GET /api/v1/accounts/dsp/{advertiser_id}/seats/sync-history

**Purpose:** Retrieve synchronization history for DSP seats data

**Authentication:** Required - Clerk user authentication via Bearer token

**Parameters:**
- **Path Parameters:**
  - `advertiser_id` (string, required): DSP Advertiser ID

- **Query Parameters:**
  - `limit` (integer, optional): Number of records (1-100, default: 10)
  - `offset` (integer, optional): Pagination offset (default: 0)
  - `status_filter` (string, optional): Filter by sync status (success|failed|partial)

**Response:** 200 OK
```json
{
  "sync_history": [
    {
      "id": "sync-log-uuid",
      "sync_status": "success",
      "seats_retrieved": 5,
      "exchanges_count": 2,
      "error_message": null,
      "created_at": "2025-09-16T10:30:00Z"
    }
  ],
  "total_count": 25,
  "limit": 10,
  "offset": 0
}
```

## Controllers

### DSPSeatsController

**Location:** `app/api/v1/accounts.py`

**Actions:**
1. `get_dsp_advertiser_seats()`: Main handler for retrieving seats
2. `refresh_dsp_seats()`: Force refresh handler
3. `get_sync_history()`: Retrieve sync log entries

**Business Logic:**
- Verify user ownership of DSP advertiser account
- Check and refresh tokens if needed (5-minute buffer before expiry)
- Apply rate limiting per user and endpoint
- Update database with retrieved seat information
- Log all operations in audit trail

**Error Handling:**
- Token expiry: Automatic refresh attempt, fail gracefully if refresh fails
- Rate limiting: Return 429 with Retry-After header
- Invalid advertiser: Return 404 with descriptive message
- Amazon API errors: Log details and return generic error to user

### Integration with Amazon DSP API

**Service Method:** `dsp_amc_service.list_advertiser_seats()`

**Amazon API Call:**
- **Endpoint:** POST https://advertising-api.amazon.com/dsp/v1/seats/advertisers/current/list
- **Required Headers:**
  - `Authorization`: Bearer token with DSP scope
  - `Amazon-Ads-AccountId`: Advertiser ID (REQUIRED)
  - `Amazon-Advertising-API-ClientId`: OAuth client ID
  - `Amazon-Advertising-API-Scope`: Profile ID (optional)

**Rate Limiting:**
- Default: 2 requests per second per advertiser
- Burst: 10 requests
- Exponential backoff on 429 responses

## Purpose

### Endpoint Rationale

**GET /api/v1/accounts/dsp/{advertiser_id}/seats**
- Primary endpoint for UI to display seat information
- Includes caching to reduce API calls
- Supports pagination for large seat lists
- Exchange filtering for focused views

**POST /api/v1/accounts/dsp/{advertiser_id}/seats/refresh**
- Allows users to manually trigger data updates
- Bypasses cache for immediate freshness
- Useful after making changes in Amazon DSP console

**GET /api/v1/accounts/dsp/{advertiser_id}/seats/sync-history**
- Provides transparency into data synchronization
- Helps troubleshoot sync issues
- Audit trail for compliance requirements

### Integration with Features

**Accounts Dashboard:**
- DSP tab displays seat information retrieved from these endpoints
- Filtering UI uses exchange_ids parameter
- Pagination controls use next_token
- Sync status indicator uses timestamp and cached fields

**Background Sync:**
- Token refresh scheduler can trigger seat updates
- Stale data detection based on last_sync timestamp
- Automatic retry on transient failures

**Error Recovery:**
- User-friendly error messages with actionable steps
- Automatic token refresh reduces authentication friction
- Rate limit handling prevents API abuse