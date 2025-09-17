# Amazon Advertising API Endpoints Reference

## Table of Contents
- [Authentication](#authentication)
- [Profiles API](#profiles-api)
- [Account Management API](#account-management-api)
- [DSP Advertisers API](#dsp-advertisers-api)
- [DSP Seats API](#dsp-seats-api)
- [Campaigns API](#campaigns-api)
- [Reporting API](#reporting-api)
- [AMC API](#amc-api)

---

## Authentication

### OAuth 2.0 Flow

#### Authorization Endpoint
```
GET https://www.amazon.com/ap/oa
```

**Parameters:**
- `client_id`: Your application's client ID
- `scope`: Space-separated list of requested scopes
- `response_type`: Set to "code"
- `redirect_uri`: Your registered redirect URI
- `state`: CSRF protection token

#### Token Endpoint
```
POST https://api.amazon.com/auth/o2/token
```

**Body (application/x-www-form-urlencoded):**
- `grant_type`: "authorization_code" for initial token, "refresh_token" for refresh
- `code`: Authorization code (for initial token)
- `refresh_token`: Refresh token (for token refresh)
- `client_id`: Your application's client ID
- `client_secret`: Your application's client secret

### Required Scopes

| Scope | Description |
|-------|-------------|
| `advertising::campaign_management` | Manage Sponsored Ads campaigns |
| `advertising::account_management` | Access account information |
| `advertising::dsp_campaigns` | Manage DSP campaigns |
| `advertising::reporting` | Access reporting data |
| `advertising::amc:read` | Read AMC data |

### Required Headers for API Calls

| Header | Description |
|--------|-------------|
| `Authorization` | Bearer {access_token} |
| `Amazon-Advertising-API-ClientId` | Your client ID |
| `Amazon-Advertising-API-Scope` | Profile ID (for profile-specific calls) |
| `Content-Type` | Usually application/json |
| `Accept` | Usually application/vnd.{resource}.v{version}+json |

---

## Profiles API

### List Profiles
```http
GET https://advertising-api.amazon.com/v2/profiles
```

**Headers:**
- `Authorization`: Bearer {access_token}
- `Amazon-Advertising-API-ClientId`: {client_id}
- `Content-Type`: application/json

**Response:**
```json
[
  {
    "profileId": 123456789,
    "countryCode": "US",
    "currencyCode": "USD",
    "timezone": "America/Los_Angeles",
    "marketplaceStringId": "ATVPDKIKX0DER",
    "entityId": "ENTITY123",
    "type": "seller",
    "accountInfo": {
      "marketplaceStringId": "ATVPDKIKX0DER",
      "id": "A1234567890",
      "type": "seller",
      "name": "Account Name",
      "validPaymentMethod": true
    }
  }
]
```

### Get Profile by ID
```http
GET https://advertising-api.amazon.com/v2/profiles/{profileId}
```

---

## Account Management API

### List All Account Types (v3.0)
```http
POST https://advertising-api.amazon.com/adsAccounts/list
```

**Headers:**
- `Content-Type`: application/vnd.listaccountsresource.v1+json
- `Accept`: application/vnd.listaccountsresource.v1+json

**Body:**
```json
{
  "maxResults": 100,
  "nextToken": null
}
```

**Response:**
```json
{
  "adsAccounts": [
    {
      "adsAccountId": "amzn1.ads-account.g.abc123",
      "accountName": "My Account",
      "status": "CREATED",
      "alternateIds": [
        {
          "countryCode": "US",
          "entityId": "ENTITY123",
          "profileId": 123456789
        }
      ],
      "countryCodes": ["US", "CA"],
      "errors": {}
    }
  ],
  "nextToken": "token_string"
}
```

### Register Account
```http
POST https://advertising-api.amazon.com/adsAccounts/register
```

**Body:**
```json
{
  "countryCode": "US",
  "adsAccountId": "amzn1.ads-account.g.abc123"
}
```

---

## DSP Advertisers API

### List DSP Advertisers
```http
GET https://advertising-api.amazon.com/dsp/advertisers
```

**Headers:**
- `Amazon-Advertising-API-Scope`: {profileId}

**Query Parameters:**
- `startIndex`: Starting index (default: 0)
- `count`: Number of results (max: 100, default: 100)
- `advertiserIdFilter`: Comma-separated advertiser IDs

**Response:**
```json
{
  "totalResults": 150,
  "response": [
    {
      "advertiserId": "4728736040201",
      "name": "Advertiser Name",
      "currency": "USD",
      "url": "www.example.com",
      "country": "US",
      "timezone": "America/New_York"
    }
  ]
}
```

### Get DSP Advertiser by ID
```http
GET https://advertising-api.amazon.com/dsp/advertisers/{advertiserId}
```

**Response:**
```json
{
  "advertiserId": "4728736040201",
  "name": "Advertiser Name",
  "currency": "USD",
  "url": "www.example.com",
  "country": "US",
  "timezone": "America/New_York"
}
```

---

## DSP Seats API

### List Current Advertiser Seats
```http
POST https://advertising-api.amazon.com/dsp/v1/seats/advertisers/current/list
```

**Headers:**
- `Amazon-Advertising-API-Scope`: {profileId}

**Body:**
```json
{
  "advertiserIds": ["123456789"],
  "exchangeIds": ["EXCHANGE_ID"],
  "maxResults": 200,
  "nextToken": null
}
```

**Response:**
```json
{
  "advertiserSeats": [
    {
      "advertiserId": "123456789",
      "currentSeats": [
        {
          "exchangeId": "EXCHANGE_ID",
          "exchangeName": "Exchange Name",
          "dealCreationId": "DEAL_123",
          "spendTrackingId": "SPEND_456"
        }
      ]
    }
  ],
  "nextToken": null
}
```

**Exchange IDs:**
| Exchange | ID |
|----------|-----|
| Google Ad Exchange | `GOOGLE_ADX` |
| Amazon Publisher Services | `APS` |
| OpenX | `OPENX` |
| PubMatic | `PUBMATIC` |
| Rubicon | `RUBICON` |

---

## Campaigns API

### Sponsored Products Campaigns

#### List Campaigns
```http
GET https://advertising-api.amazon.com/v2/sp/campaigns
```

**Headers:**
- `Amazon-Advertising-API-Scope`: {profileId}

**Query Parameters:**
- `startIndex`: Starting index
- `count`: Number of results
- `stateFilter`: enabled, paused, archived
- `campaignIdFilter`: Comma-separated campaign IDs

**Response:**
```json
[
  {
    "campaignId": 123456789,
    "name": "Campaign Name",
    "campaignType": "sponsoredProducts",
    "targetingType": "manual",
    "state": "enabled",
    "dailyBudget": 100.00,
    "startDate": "20240101",
    "premiumBidAdjustment": true,
    "bidding": {
      "strategy": "legacyForSales",
      "adjustments": []
    }
  }
]
```

### DSP Campaigns

#### List DSP Campaigns
```http
GET https://advertising-api.amazon.com/dsp/campaigns
```

**Headers:**
- `Amazon-Advertising-API-Scope`: {profileId}

**Query Parameters:**
- `advertiserId`: DSP advertiser ID (required)
- `startIndex`: Starting index
- `count`: Number of results

---

## Reporting API

### Create Report Request
```http
POST https://advertising-api.amazon.com/v2/reports
```

**Headers:**
- `Amazon-Advertising-API-Scope`: {profileId}
- `Content-Type`: application/json

**Body (Sponsored Products Example):**
```json
{
  "reportDate": "20240101",
  "metrics": [
    "campaignName",
    "impressions",
    "clicks",
    "cost",
    "attributedSales14d"
  ],
  "reportType": "campaigns"
}
```

**Response:**
```json
{
  "reportId": "amzn1.clicksAPI.report.abc123",
  "recordType": "campaigns",
  "status": "IN_PROGRESS",
  "statusDetails": "Report is being generated"
}
```

### Get Report Status
```http
GET https://advertising-api.amazon.com/v2/reports/{reportId}
```

**Response:**
```json
{
  "reportId": "amzn1.clicksAPI.report.abc123",
  "status": "SUCCESS",
  "statusDetails": "Report has been successfully generated",
  "location": "https://advertising-api-report.s3.amazonaws.com/report.json.gz",
  "fileSize": 12345
}
```

### Download Report
```http
GET {location_url_from_status}
```

**Note:** The location URL is pre-signed and expires after a certain period.

---

## AMC API

### List AMC Instances
```http
GET https://advertising-api.amazon.com/amc/instances
```

**Headers:**
- `Authorization`: Bearer {access_token}
- `Amazon-Advertising-API-ClientId`: {client_id}

**Response:**
```json
{
  "instances": [
    {
      "instanceId": "amzn1.amc.instance.abc123",
      "marketplaceId": "ATVPDKIKX0DER",
      "accountId": "A1234567890",
      "status": "ACTIVE",
      "dataUploadAccountId": "amzn1.application.abc123"
    }
  ]
}
```

---

## Error Responses

### Standard Error Format
```json
{
  "code": "400",
  "details": "Invalid request parameters",
  "requestId": "abc123-def456-789",
  "errors": [
    {
      "errorType": "INVALID_PARAMETER",
      "field": "advertiserId",
      "message": "AdvertiserId must be a valid numeric id"
    }
  ]
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |
| 502 | Bad Gateway |
| 503 | Service Unavailable |

---

## Rate Limiting

The Amazon Advertising API implements rate limiting to ensure fair usage:

- **Default limits**: 100 requests per second per profile
- **Burst capacity**: Up to 200 requests
- **Recovery**: 10 requests per second

### Rate Limit Headers
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets
- `Retry-After`: Seconds to wait before retrying (on 429 responses)

---

## Best Practices

1. **Token Management**
   - Refresh tokens before expiration (60-minute lifetime)
   - Store tokens securely (encrypted)
   - Implement automatic retry with fresh token on 401

2. **Error Handling**
   - Implement exponential backoff for rate limiting
   - Log request IDs for troubleshooting
   - Handle partial success in batch operations

3. **Pagination**
   - Always check for `nextToken` in responses
   - Use appropriate `maxResults` to balance performance
   - Maximum results per request varies by endpoint (usually 100-200)

4. **Profile Selection**
   - Cache profile list to reduce API calls
   - Verify profile has correct permissions for operation
   - DSP operations require agency-type profiles

5. **Reporting**
   - Reports are generated asynchronously
   - Poll status endpoint with exponential backoff
   - Download reports promptly (URLs expire)

---

## Testing Endpoints

### Sandbox Environment
Amazon provides a sandbox environment for testing:
- Base URL: `https://advertising-api-test.amazon.com`
- Use same authentication flow
- Limited to test data

### Health Check
```http
GET https://advertising-api.amazon.com/v2/profiles
```

A successful response with profile data indicates:
- Valid authentication
- Correct client configuration
- API accessibility

---

## SDK and Libraries

### Official SDKs
- Python: `amazon-advertising-api-python`
- Java: `amazon-advertising-api-java`
- PHP: `amazon-advertising-api-php`

### Authentication Libraries
- Python: `amazon-sp-api`
- Node.js: `amazon-advertising-api-sdk`

---

## Changelog

### Version 3.0 (Current)
- New Account Management API with unified response format
- DSP Seats API for advertiser seat management
- Enhanced AMC integration

### Version 2.0
- Profiles API
- Sponsored Products, Brands, Display
- Basic reporting

### Version 1.0 (Deprecated)
- Legacy endpoints
- Being phased out

---

## Resources

- [Official Documentation](https://advertising.amazon.com/API/docs/en-us/)
- [API Reference](https://advertising.amazon.com/API/docs/en-us/reference)
- [Migration Guides](https://advertising.amazon.com/API/docs/en-us/guides/migration)
- [Support](https://advertising.amazon.com/support)