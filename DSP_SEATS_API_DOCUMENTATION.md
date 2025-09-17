# DSP Seats API Documentation

The DSP Seats API provides access to Amazon DSP advertiser seat information, allowing users to view their seat allocations across advertising exchanges for deal creation and spend tracking.

## Endpoints

### GET /api/v1/accounts/dsp/{advertiser_id}/seats

Retrieve seat information for a DSP advertiser.

#### Parameters

- **Path Parameters:**
  - `advertiser_id` (string, required): The DSP advertiser ID

- **Query Parameters:**
  - `exchange_ids` (array[string], optional): Filter by specific exchange IDs
  - `max_results` (integer, optional): Maximum number of results (1-200, default: 200)
  - `next_token` (string, optional): Pagination token for retrieving next page
  - `profile_id` (string, optional): Optional profile ID filter

#### Request Example

```bash
curl -X GET \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats?exchange_ids=1,2&max_results=50" \
  -H "Authorization: Bearer your_clerk_token" \
  -H "Content-Type: application/json"
```

#### Response Example

```json
{
  "advertiserSeats": [
    {
      "advertiserId": "DSP_ADV_123",
      "currentSeats": [
        {
          "exchangeId": "1",
          "exchangeName": "Google Ad Manager",
          "dealCreationId": "DEAL_001",
          "spendTrackingId": "SPEND_001"
        },
        {
          "exchangeId": "2",
          "exchangeName": "Microsoft Advertising Exchange",
          "dealCreationId": "DEAL_002",
          "spendTrackingId": "SPEND_002"
        }
      ]
    }
  ],
  "nextToken": "eyJhZGRlZCI6MTU5...",
  "timestamp": "2025-09-16T15:30:00Z",
  "cached": false
}
```

#### Error Responses

**404 Not Found** - Advertiser not found
```json
{
  "error": "Not Found",
  "detail": "DSP advertiser DSP_ADV_999 not found for user",
  "timestamp": "2025-09-16T15:30:00Z"
}
```

**401 Unauthorized** - Authentication required
```json
{
  "error": "Unauthorized",
  "detail": "Authentication required",
  "timestamp": "2025-09-16T15:30:00Z"
}
```

**429 Too Many Requests** - Rate limit exceeded
```json
{
  "error": "Too Many Requests",
  "detail": "Rate limit exceeded. Retry after 60 seconds.",
  "timestamp": "2025-09-16T15:30:00Z"
}
```

### POST /api/v1/accounts/dsp/{advertiser_id}/seats/refresh

Force refresh of DSP seats data from Amazon API.

#### Parameters

- **Path Parameters:**
  - `advertiser_id` (string, required): The DSP advertiser ID

- **Request Body:**
```json
{
  "force": true,
  "include_sync_log": true
}
```

#### Request Example

```bash
curl -X POST \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats/refresh" \
  -H "Authorization: Bearer your_clerk_token" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "include_sync_log": true
  }'
```

#### Response Example

```json
{
  "success": true,
  "seats_updated": 5,
  "last_sync": "2025-09-16T15:30:00Z",
  "sync_log_id": "log_456789",
  "message": "DSP seats refreshed successfully"
}
```

#### Error Responses

**409 Conflict** - Sync already in progress
```json
{
  "error": "Conflict",
  "detail": "Sync already in progress for this advertiser",
  "timestamp": "2025-09-16T15:30:00Z"
}
```

### GET /api/v1/accounts/dsp/{advertiser_id}/seats/sync-history

Retrieve synchronization history for DSP seats.

#### Parameters

- **Path Parameters:**
  - `advertiser_id` (string, required): The DSP advertiser ID

- **Query Parameters:**
  - `limit` (integer, optional): Number of records to return (default: 20, max: 100)
  - `offset` (integer, optional): Number of records to skip (default: 0)
  - `status_filter` (string, optional): Filter by status ('success', 'failed', 'partial')

#### Request Example

```bash
curl -X GET \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats/sync-history?limit=10&status_filter=success" \
  -H "Authorization: Bearer your_clerk_token"
```

#### Response Example

```json
{
  "sync_history": [
    {
      "id": "log_001",
      "sync_status": "success",
      "seats_retrieved": 5,
      "exchanges_count": 3,
      "error_message": null,
      "created_at": "2025-09-16T15:30:00Z"
    },
    {
      "id": "log_002",
      "sync_status": "failed",
      "seats_retrieved": 0,
      "exchanges_count": 0,
      "error_message": "Rate limit exceeded",
      "created_at": "2025-09-16T14:30:00Z"
    }
  ],
  "total_count": 25,
  "limit": 10,
  "offset": 0
}
```

## Data Models

### DSPSeatInfo

```typescript
interface DSPSeatInfo {
  exchangeId: string;           // Exchange identifier
  exchangeName: string;         // Human-readable exchange name
  dealCreationId: string | null; // Deal creation identifier (nullable)
  spendTrackingId: string;      // Spend tracking identifier
}
```

### DSPSeatsResponse

```typescript
interface DSPSeatsResponse {
  advertiserSeats: Array<{
    advertiserId: string;
    currentSeats: DSPSeatInfo[];
  }>;
  nextToken?: string;           // Pagination token
  timestamp: string;            // ISO 8601 timestamp
  cached: boolean;              // Whether data was served from cache
}
```

### DSPSeatsRefreshResponse

```typescript
interface DSPSeatsRefreshResponse {
  success: boolean;
  seats_updated: number;
  last_sync: string;            // ISO 8601 timestamp
  sync_log_id: string;
  message: string;
}
```

### DSPSyncHistoryEntry

```typescript
interface DSPSyncHistoryEntry {
  id: string;
  sync_status: 'success' | 'failed' | 'partial';
  seats_retrieved: number;
  exchanges_count: number;
  error_message: string | null;
  created_at: string;           // ISO 8601 timestamp
}
```

## Rate Limiting

The DSP Seats API implements exponential backoff rate limiting:

- **Default Rate Limit:** 2 requests per second
- **Retry Behavior:** Automatic exponential backoff on 429 responses
- **Max Retries:** 3 attempts with increasing delays (1s, 2s, 4s)
- **Rate Limit Headers:**
  - `Retry-After`: Seconds to wait before retrying (on 429 responses)

## Authentication

All DSP Seats API endpoints require Clerk authentication:

```bash
Authorization: Bearer your_clerk_token
```

The API validates the Clerk token and associates requests with the authenticated user's account.

## Caching

- **Frontend Caching:** 5-minute TTL for seat data
- **Database Caching:** Seat information stored in `metadata.seats_metadata` JSON field
- **Cache Invalidation:** Automatic on manual refresh or sync operations

## Error Handling

The API implements comprehensive error handling:

1. **Authentication Errors (401):** Invalid or missing Clerk token
2. **Authorization Errors (403):** User doesn't have access to advertiser
3. **Not Found Errors (404):** Advertiser not found for user
4. **Rate Limit Errors (429):** Too many requests, includes Retry-After header
5. **Validation Errors (422):** Invalid request parameters
6. **Server Errors (500):** Internal server errors with structured logging

## Examples

### Getting All Seats for an Advertiser

```bash
curl -X GET \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats" \
  -H "Authorization: Bearer your_clerk_token"
```

### Filtering by Specific Exchanges

```bash
curl -X GET \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats?exchange_ids=1,3,5" \
  -H "Authorization: Bearer your_clerk_token"
```

### Pagination Example

```bash
# First page
curl -X GET \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats?max_results=10" \
  -H "Authorization: Bearer your_clerk_token"

# Next page using returned nextToken
curl -X GET \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats?max_results=10&next_token=eyJhZGRlZCI6MTU5..." \
  -H "Authorization: Bearer your_clerk_token"
```

### Force Refresh with Sync Logging

```bash
curl -X POST \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats/refresh" \
  -H "Authorization: Bearer your_clerk_token" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "include_sync_log": true
  }'
```

### Getting Sync History with Filtering

```bash
curl -X GET \
  "https://api.example.com/api/v1/accounts/dsp/DSP_ADV_123/seats/sync-history?status_filter=failed&limit=5" \
  -H "Authorization: Bearer your_clerk_token"
```