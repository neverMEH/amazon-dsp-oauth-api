# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-15-accounts-restructure-multi-type/spec.md

> Created: 2025-09-15
> Version: 1.0.0

## Endpoints

### GET /api/v1/accounts/sponsored-ads

**Purpose:** Fetch Sponsored Ads accounts with profile/entity IDs and management history
**Parameters:**
- `limit` (query, optional): Number of results per page (default: 100)
- `offset` (query, optional): Pagination offset
- `sort_by` (query, optional): Field to sort by (account_name, last_managed_at, created_at)
- `sort_order` (query, optional): asc or desc

**Response:**
```json
{
  "accounts": [
    {
      "id": "uuid",
      "account_name": "string",
      "profile_id": "123456789",
      "entity_id": "ENTITY123ABC",
      "marketplaces": ["US", "CA", "MX"],
      "last_managed_at": "2025-09-14T15:30:00Z",
      "status": "active",
      "account_type": "advertising",
      "metadata": {
        "alternateIds": [...],
        "countryCodes": [...]
      },
      "last_synced_at": "2025-09-15T10:00:00Z"
    }
  ],
  "total": 15,
  "has_more": false
}
```

**Errors:**
- 401: Unauthorized
- 500: Internal server error

### GET /api/v1/accounts/dsp

**Purpose:** Fetch DSP accounts with entity/profile IDs and marketplace data
**Parameters:**
- `limit` (query, optional): Number of results per page (default: 100)
- `offset` (query, optional): Pagination offset

**Response:**
```json
{
  "accounts": [
    {
      "id": "uuid",
      "account_name": "string",
      "entity_id": "DSP_ENTITY_456",
      "profile_id": "987654321",
      "marketplace": "US",
      "account_type": "dsp",
      "advertiser_type": "brand",
      "metadata": {
        "seats": 5,
        "line_items_count": 23,
        "access_level": "admin"
      },
      "last_synced_at": "2025-09-15T10:00:00Z"
    }
  ],
  "total": 3,
  "has_more": false,
  "access_denied": false
}
```

**Errors:**
- 401: Unauthorized
- 403: No DSP access (returns empty array with access_denied: true)
- 500: Internal server error

### GET /api/v1/accounts/amc

**Purpose:** Fetch AMC instances with embedded associated DSP and SP account information
**Parameters:**
- `include_associated_details` (query, optional): Include full associated account details (default: true)

**Response:**
```json
{
  "instances": [
    {
      "id": "uuid",
      "instance_name": "string",
      "instance_id": "AMC_INSTANCE_789",
      "account_type": "amc",
      "data_set_id": "dataset_xyz",
      "status": "active",
      "associated_accounts": {
        "sponsored_ads": [
          {
            "account_name": "SP Account 1",
            "profile_id": "123456789",
            "entity_id": "ENTITY123ABC"
          }
        ],
        "dsp": [
          {
            "account_name": "DSP Account 1",
            "profile_id": "987654321",
            "entity_id": "DSP_ENTITY_456"
          }
        ]
      },
      "metadata": {
        "region": "us-east-1",
        "storage_used_gb": 125.5,
        "query_credits": 1000
      },
      "last_synced_at": "2025-09-15T10:00:00Z"
    }
  ],
  "total": 1,
  "access_denied": false
}
```

**Errors:**
- 401: Unauthorized
- 403: No AMC access (returns empty array with access_denied: true)
- 500: Internal server error

### GET /api/v1/accounts/relationships/{account_id}

**Purpose:** Get all relationships for a specific account
**Parameters:**
- `account_id` (path, required): UUID of the account

**Response:**
```json
{
  "account_id": "uuid",
  "relationships": {
    "parents": [
      {
        "account_id": "uuid",
        "account_name": "string",
        "account_type": "advertising",
        "relationship_type": "sponsored_to_dsp"
      }
    ],
    "children": [
      {
        "account_id": "uuid",
        "account_name": "string",
        "account_type": "amc",
        "relationship_type": "dsp_to_amc"
      }
    ]
  }
}
```

**Errors:**
- 401: Unauthorized
- 404: Account not found
- 500: Internal server error

### POST /api/v1/accounts/{account_id}/set-managed

**Purpose:** Update the last_managed_at timestamp when an account is selected for management
**Parameters:**
- `account_id` (path, required): UUID of the account being managed

**Response:**
```json
{
  "success": true,
  "account_id": "uuid",
  "last_managed_at": "2025-09-15T10:00:00Z"
}
```

**Errors:**
- 401: Unauthorized
- 404: Account not found
- 500: Internal server error

### POST /api/v1/accounts/sync

**Purpose:** Trigger synchronization of all account types from Amazon APIs
**Parameters:**
- Request body:
```json
{
  "account_types": ["advertising", "dsp", "amc"],
  "force_refresh": false
}
```

**Response:**
```json
{
  "sync_id": "uuid",
  "status": "in_progress",
  "account_types": ["advertising", "dsp", "amc"],
  "started_at": "2025-09-15T10:00:00Z"
}
```

**Errors:**
- 401: Unauthorized
- 429: Rate limited
- 500: Internal server error

### GET /api/v1/accounts/sync/{sync_id}

**Purpose:** Check status of account synchronization
**Parameters:**
- `sync_id` (path, required): UUID of the sync operation

**Response:**
```json
{
  "sync_id": "uuid",
  "status": "completed",
  "results": {
    "advertising": {
      "status": "success",
      "accounts_synced": 15,
      "errors": []
    },
    "dsp": {
      "status": "success",
      "accounts_synced": 3,
      "errors": []
    },
    "amc": {
      "status": "no_access",
      "accounts_synced": 0,
      "errors": ["User does not have AMC access"]
    }
  },
  "completed_at": "2025-09-15T10:05:00Z"
}
```

**Errors:**
- 401: Unauthorized
- 404: Sync ID not found
- 500: Internal server error

## Controllers

### AccountController

**Actions:**
- `get_sponsored_ads_accounts()`: Fetch filtered Sponsored Ads accounts
- `get_dsp_accounts()`: Fetch DSP advertiser accounts with error handling
- `get_amc_instances()`: Fetch AMC instances with linked accounts
- `get_account_relationships()`: Query account relationships from database
- `sync_accounts()`: Orchestrate multi-type account synchronization
- `get_sync_status()`: Check synchronization progress

**Business Logic:**
- Filter accounts by type at database level for performance
- Handle 403 responses gracefully for missing permissions
- Build relationship graph from AMC advertiser arrays
- Cache account data with 5-minute TTL
- Implement rate limiting for Amazon API calls

**Error Handling:**
- Log all 403 responses for permission tracking
- Return empty arrays with access_denied flags
- Provide detailed error messages for debugging
- Implement exponential backoff for retries

## Integration Points

- **Amazon Ads API**: Direct integration for account fetching
- **Database**: Store and query account relationships
- **Cache Layer**: Redis for account data caching
- **Background Jobs**: Celery for async synchronization
- **Frontend**: RESTful API consumed by Next.js application