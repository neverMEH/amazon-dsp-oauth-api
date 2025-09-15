# DSP and AMC Integration Guide

## Overview

This document describes the integration of Amazon DSP (Demand-Side Platform) and AMC (Amazon Marketing Cloud) accounts into the existing account management system.

## Account Types Comparison

### 1. Regular Advertising Accounts
- **Purpose**: Manage Sponsored Products, Sponsored Brands, and Sponsored Display campaigns
- **API Endpoint**: `POST /adsAccounts/list`
- **Primary Identifier**: `adsAccountId`
- **Required Scope**: `advertising::account_management`
- **Typical Use**: Self-service advertising campaigns

### 2. DSP Advertisers
- **Purpose**: Programmatic display advertising across Amazon properties and third-party exchanges
- **API Endpoint**: `GET /dsp/advertisers`
- **Primary Identifier**: `advertiserId`
- **Required Scope**: `advertising::dsp_campaigns`
- **Typical Use**: Advanced programmatic campaigns, audience targeting, retargeting

### 3. AMC Instances
- **Purpose**: Advanced analytics and data insights using Amazon's clean room environment
- **API Endpoint**: `GET /amc/instances`
- **Primary Identifier**: `instanceId`
- **Required Scope**: `advertising::amc:read`
- **Typical Use**: Cross-channel attribution, custom analytics, audience insights

## API Implementation

### New Service: `dsp_amc_service.py`

Located at `/backend/app/services/dsp_amc_service.py`, this service provides:

1. **`list_dsp_advertisers()`** - Retrieves all DSP advertisers
2. **`list_amc_instances()`** - Retrieves all AMC instances
3. **`list_all_account_types()`** - Parallel fetching of all account types

### New API Endpoint

**Endpoint**: `GET /api/v1/accounts/all-account-types`

**Query Parameters**:
- `include_advertising` (bool): Include regular advertising accounts
- `include_dsp` (bool): Include DSP advertisers
- `include_amc` (bool): Include AMC instances

**Response Format**:
```json
{
  "accounts": [
    {
      "id": "database_uuid",
      "name": "Account Name",
      "type": "advertising|dsp|amc",
      "platform_id": "amazon_account_id",
      "status": "active|suspended|provisioning",
      "metadata": {
        // Original API response data
      }
    }
  ],
  "summary": {
    "total": 10,
    "advertising": 5,
    "dsp": 3,
    "amc": 2
  }
}
```

## Database Storage

All account types are stored in the existing `user_accounts` table with differentiation through the `account_type` field:

- `advertising` - Regular advertising accounts
- `dsp` - DSP advertisers
- `amc` - AMC instances

The `metadata` JSONB field stores type-specific data:

### Advertising Account Metadata
```json
{
  "alternate_ids": [...],
  "country_codes": ["US", "CA"],
  "profile_id": 12345,
  "errors": {}
}
```

### DSP Advertiser Metadata
```json
{
  "advertiser_type": "AGENCY|ADVERTISER",
  "country_code": "US",
  "currency": "USD",
  "timezone": "America/Los_Angeles",
  "created_date": "2023-01-01T00:00:00Z"
}
```

### AMC Instance Metadata
```json
{
  "instance_type": "STANDARD|PREMIUM",
  "region": "us-east-1",
  "data_retention_days": 400,
  "linked_advertisers": [...],
  "created_date": "2023-01-01T00:00:00Z"
}
```

## Authentication Requirements

### Updated OAuth Scopes

The OAuth service now requests these scopes:
```python
scopes = [
    "advertising::campaign_management",
    "advertising::account_management",
    "advertising::dsp_campaigns",
    "advertising::reporting",
    "advertising::amc:read"  # New scope for AMC
]
```

**Important**: Users will need to re-authenticate after this change to grant the additional AMC scope.

## Error Handling

### DSP Access Errors
- **403 Forbidden**: User doesn't have DSP access (normal for many accounts)
- Returns empty array instead of error

### AMC Access Errors
- **403 Forbidden**: User doesn't have AMC provisioning (requires special setup)
- Returns empty array instead of error

### Rate Limiting
- All endpoints implement exponential backoff
- Respect `Retry-After` headers
- Default 60-second retry on 429 errors

## Frontend Integration

### Recommended UI Updates

1. **Account Type Indicators**
   - Add badges or icons to differentiate account types
   - Use different colors: Blue (Advertising), Purple (DSP), Green (AMC)

2. **Filtering Options**
   - Add account type filter dropdown
   - Allow multi-select for type filtering

3. **Account Details**
   - Show type-specific information
   - DSP: Show advertiser type, timezone
   - AMC: Show instance type, data retention, linked advertisers

### Example Frontend Code

```typescript
// Fetch all account types
const response = await fetch('/api/v1/accounts/all-account-types', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const data = await response.json();

// Filter by type
const dspAccounts = data.accounts.filter(acc => acc.type === 'dsp');
const amcInstances = data.accounts.filter(acc => acc.type === 'amc');

// Display with type-specific rendering
accounts.forEach(account => {
  switch(account.type) {
    case 'dsp':
      renderDSPAccount(account);
      break;
    case 'amc':
      renderAMCInstance(account);
      break;
    default:
      renderAdvertisingAccount(account);
  }
});
```

## Testing

### Manual Testing Steps

1. **Test Authentication**
   ```bash
   # Check if AMC scope is included
   curl -X GET "http://localhost:8000/api/v1/auth/status"
   ```

2. **Test Account Retrieval**
   ```bash
   # Fetch all account types
   curl -X GET "http://localhost:8000/api/v1/accounts/all-account-types" \
     -H "Authorization: Bearer YOUR_TOKEN"

   # Fetch only DSP accounts
   curl -X GET "http://localhost:8000/api/v1/accounts/all-account-types?include_advertising=false&include_amc=false" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Verify Database Storage**
   ```sql
   -- Check account types in database
   SELECT account_type, COUNT(*)
   FROM user_accounts
   GROUP BY account_type;

   -- View DSP accounts
   SELECT * FROM user_accounts
   WHERE account_type = 'dsp';
   ```

### Common Test Scenarios

1. **No DSP/AMC Access**: Most users won't have DSP or AMC access
   - Should return empty arrays for these types
   - Should not throw errors

2. **Mixed Access**: Some users may have DSP but not AMC
   - Should return available account types only

3. **Full Access**: Enterprise users with all account types
   - Should see all three account types

## Migration Considerations

### For Existing Users

1. **Re-authentication Required**: Users must re-auth to grant AMC scope
2. **Backward Compatibility**: Existing endpoints continue to work
3. **Data Migration**: Not needed - new account types stored in same table

### Database Considerations

No schema changes required. The existing `user_accounts` table handles all account types through:
- `account_type` field for differentiation
- `metadata` JSONB field for type-specific data

## Performance Optimizations

### Parallel Fetching
The service fetches all account types in parallel using `asyncio.gather()`:
```python
results = await asyncio.gather(
    account_service.list_ads_accounts(token),
    dsp_amc_service.list_dsp_advertisers(token),
    dsp_amc_service.list_amc_instances(token),
    return_exceptions=True
)
```

### Caching Strategy
Consider implementing:
1. **Short-term cache** (5 minutes) for account lists
2. **Account type indicators** in session storage
3. **Lazy loading** for account details

## Security Considerations

1. **Scope Validation**: Verify user has required scopes before API calls
2. **Error Masking**: Don't expose detailed API errors to frontend
3. **Audit Logging**: Log all account access for compliance
4. **Token Refresh**: Ensure tokens are refreshed before DSP/AMC calls

## Troubleshooting

### Common Issues

1. **"No AMC access" for all users**
   - AMC requires special provisioning from Amazon
   - Contact Amazon Ads support for AMC enablement

2. **DSP advertisers not showing**
   - Verify `advertising::dsp_campaigns` scope is granted
   - Check if user's account has DSP entity access

3. **Rate limiting on parallel requests**
   - Implement request queuing
   - Add delays between account type fetches

### Debug Endpoints

```python
# Add to accounts.py for debugging
@router.get("/debug/account-types")
async def debug_account_types(current_user: Dict = Depends(RequireAuth)):
    """Debug endpoint to check account type access"""
    # Implementation for checking individual API access
```

## Future Enhancements

1. **Webhook Support**: Real-time updates for account status changes
2. **Bulk Operations**: Batch operations across account types
3. **Advanced Filtering**: Filter by region, status, creation date
4. **Account Linking**: Link DSP advertisers to AMC instances
5. **Permissions Matrix**: Show user's access level per account type