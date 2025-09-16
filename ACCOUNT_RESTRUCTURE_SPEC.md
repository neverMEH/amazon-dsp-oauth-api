# Account Restructure Specification

## Overview
This specification outlines the restructuring of the accounts page to properly segregate account types (Sponsored Ads, DSP, AMC) and define the relationships between them.

## 1. Amazon Advertising API Endpoints

### 1.1 Sponsored Ads Accounts (Main Page)

**Endpoint**: `POST https://advertising-api.amazon.com/adsAccounts/list`
- **Method**: POST
- **Content-Type**: `application/vnd.listaccountsresource.v1+json`
- **Accept**: `application/vnd.listaccountsresource.v1+json`
- **Required Headers**:
  - `Authorization: Bearer {access_token}`
  - `Amazon-Advertising-API-ClientId: {client_id}`
- **Request Body**:
  ```json
  {
    "maxResults": 100,
    "nextToken": "string" // Optional for pagination
  }
  ```
- **Response Format**:
  ```json
  {
    "adsAccounts": [
      {
        "adsAccountId": "ENTITY123456",
        "accountName": "My Brand Store",
        "status": "CREATED", // CREATED|DISABLED|PARTIALLY_CREATED|PENDING
        "alternateIds": [
          {
            "countryCode": "US",
            "entityId": "ENTITY_US_123",
            "profileId": 123456789
          }
        ],
        "countryCodes": ["US", "CA", "MX"],
        "errors": {} // Country-specific errors if any
      }
    ],
    "nextToken": "string"
  }
  ```

**Key Points**:
- This returns ONLY Sponsored Products/Brands/Display accounts
- Each account can have multiple country profiles via `alternateIds`
- The `adsAccountId` is the global identifier
- Filter in frontend to show only these accounts on main page

### 1.2 DSP Accounts (DSP Subpage)

**Endpoint**: `GET https://advertising-api.amazon.com/dsp/advertisers`
- **Method**: GET
- **Required Headers**:
  - `Authorization: Bearer {access_token}`
  - `Amazon-Advertising-API-ClientId: {client_id}`
  - `Amazon-Advertising-API-Scope: {profile_id}` (Optional for filtering)
- **Response Format**:
  ```json
  {
    "advertisers": [
      {
        "advertiserId": "DSP123456",
        "advertiserName": "My DSP Entity",
        "advertiserType": "ADVERTISER", // ADVERTISER|AGENCY
        "advertiserStatus": "ACTIVE", // ACTIVE|SUSPENDED|INACTIVE
        "countryCode": "US",
        "currency": "USD",
        "timeZone": "America/Los_Angeles",
        "createdDate": "2024-01-01T00:00:00Z"
      }
    ]
  }
  ```

**Key Points**:
- DSP advertisers are separate entities from Sponsored Ads accounts
- Each DSP advertiser has its own ID and management structure
- Users may have zero or more DSP advertisers
- 403 response indicates user lacks DSP permissions (normal for many users)

### 1.3 AMC Instances (AMC Subpage)

**Endpoint**: `GET https://advertising-api.amazon.com/amc/instances`
- **Method**: GET
- **Required Headers**:
  - `Authorization: Bearer {access_token}`
  - `Amazon-Advertising-API-ClientId: {client_id}`
- **Required Scope**: `advertising::amc:read`
- **Response Format**:
  ```json
  {
    "instances": [
      {
        "instanceId": "AMC123456",
        "instanceName": "My AMC Instance",
        "instanceType": "STANDARD", // STANDARD|PREMIUM
        "status": "ACTIVE", // ACTIVE|PROVISIONING|SUSPENDED
        "region": "us-east-1",
        "createdDate": "2024-01-01T00:00:00Z",
        "dataRetentionDays": 400,
        "advertisers": [
          {
            "advertiserId": "DSP123456",
            "advertiserName": "My DSP Entity"
          },
          {
            "advertiserId": "ENTITY123456",
            "advertiserName": "My Brand Store"
          }
        ]
      }
    ]
  }
  ```

**Key Points**:
- AMC instances are linked to advertisers (both DSP and Sponsored Ads)
- The `advertisers` array shows which accounts have data flowing into the AMC
- AMC requires special provisioning (403 indicates no access)
- AMC instances aggregate data from multiple advertiser sources

### 1.4 Fetching AMC Instances by Account Association

To get AMC instances associated with specific accounts:

1. **First, get all AMC instances** using the endpoint above
2. **Filter locally** based on the `advertisers` array:
   - For Sponsored Ads: Match `advertiserId` with `adsAccountId`
   - For DSP: Match `advertiserId` with DSP `advertiserId`
3. **Alternative approach** - Query AMC data availability:
   ```
   GET /amc/instances/{instanceId}/advertisers
   ```
   This returns detailed advertiser associations for a specific AMC instance

## 2. Supabase Database Schema

### 2.1 Enhanced user_accounts Table

The existing `user_accounts` table needs modifications to properly support all account types:

```sql
-- Modify account_type constraint to include all types
ALTER TABLE user_accounts
    DROP CONSTRAINT IF EXISTS user_accounts_account_type_check;

ALTER TABLE user_accounts
    ADD CONSTRAINT user_accounts_account_type_check
    CHECK (account_type IN ('advertising', 'dsp', 'amc', 'vendor', 'seller'));

-- Add column for parent account relationships
ALTER TABLE user_accounts
    ADD COLUMN IF NOT EXISTS parent_account_id UUID REFERENCES user_accounts(id),
    ADD COLUMN IF NOT EXISTS account_subtype VARCHAR(50);

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_user_accounts_account_type
    ON user_accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_user_accounts_parent_account
    ON user_accounts(parent_account_id);
```

### 2.2 New account_relationships Table

Create a table to manage many-to-many relationships between accounts:

```sql
CREATE TABLE IF NOT EXISTS account_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    target_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL CHECK (
        relationship_type IN ('sponsors_dsp', 'feeds_amc', 'dsp_feeds_amc')
    ),
    established_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(source_account_id, target_account_id, relationship_type)
);

-- Add indexes
CREATE INDEX idx_account_rel_source ON account_relationships(source_account_id);
CREATE INDEX idx_account_rel_target ON account_relationships(target_account_id);
CREATE INDEX idx_account_rel_type ON account_relationships(relationship_type);
```

### 2.3 Enhanced Metadata Structure

For each account type, store specific metadata:

**Sponsored Ads Account (advertising)**:
```json
{
  "alternate_ids": [
    {
      "countryCode": "US",
      "entityId": "ENTITY_US_123",
      "profileId": 123456789
    }
  ],
  "country_codes": ["US", "CA", "MX"],
  "api_status": "CREATED",
  "errors": {},
  "campaign_types": ["SP", "SB", "SD"] // Sponsored Products/Brands/Display
}
```

**DSP Account (dsp)**:
```json
{
  "advertiser_type": "ADVERTISER",
  "country_code": "US",
  "currency": "USD",
  "timezone": "America/Los_Angeles",
  "created_date": "2024-01-01T00:00:00Z",
  "seat_id": "DSP_SEAT_123", // DSP seat identifier
  "linked_sponsored_accounts": ["ENTITY123456"] // adsAccountIds
}
```

**AMC Instance (amc)**:
```json
{
  "instance_type": "STANDARD",
  "region": "us-east-1",
  "data_retention_days": 400,
  "created_date": "2024-01-01T00:00:00Z",
  "linked_advertisers": [
    {
      "advertiserId": "DSP123456",
      "advertiserName": "My DSP Entity",
      "advertiserType": "dsp"
    },
    {
      "advertiserId": "ENTITY123456",
      "advertiserName": "My Brand Store",
      "advertiserType": "sponsored"
    }
  ],
  "data_sources": ["sponsored_ads", "dsp", "retail"] // Data flowing into AMC
}
```

### 2.4 Database Functions

Create helper functions for querying relationships:

```sql
-- Function to get all AMC instances for a sponsored ads account
CREATE OR REPLACE FUNCTION get_amc_instances_for_account(
    p_user_id UUID,
    p_account_id VARCHAR(255)
) RETURNS TABLE (
    instance_id UUID,
    instance_name VARCHAR(255),
    amazon_instance_id VARCHAR(255),
    status VARCHAR(50),
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ua.id,
        ua.account_name,
        ua.amazon_account_id,
        ua.status,
        ua.metadata
    FROM user_accounts ua
    WHERE
        ua.user_id = p_user_id
        AND ua.account_type = 'amc'
        AND ua.metadata->'linked_advertisers' @>
            jsonb_build_array(jsonb_build_object('advertiserId', p_account_id));
END;
$$ LANGUAGE plpgsql;

-- Function to get account hierarchy
CREATE OR REPLACE FUNCTION get_account_hierarchy(
    p_user_id UUID
) RETURNS TABLE (
    account_id UUID,
    account_name VARCHAR(255),
    account_type VARCHAR(50),
    parent_id UUID,
    level INTEGER
) AS $$
WITH RECURSIVE account_tree AS (
    -- Base case: top-level accounts
    SELECT
        id,
        account_name,
        account_type,
        parent_account_id,
        0 as level
    FROM user_accounts
    WHERE
        user_id = p_user_id
        AND parent_account_id IS NULL

    UNION ALL

    -- Recursive case: child accounts
    SELECT
        ua.id,
        ua.account_name,
        ua.account_type,
        ua.parent_account_id,
        at.level + 1
    FROM user_accounts ua
    INNER JOIN account_tree at ON ua.parent_account_id = at.id
    WHERE ua.user_id = p_user_id
)
SELECT * FROM account_tree
ORDER BY level, account_type, account_name;
$$ LANGUAGE plpgsql;
```

## 3. API Integration Strategy

### 3.1 Account Type Filtering

Implement filtering at the API level:

```python
# backend/app/api/v1/accounts.py

@router.get("/sponsored-ads-accounts")
async def list_sponsored_ads_accounts(
    current_user: Dict = Depends(RequireAuth),
    include_profiles: bool = Query(True)
):
    """List only Sponsored Ads accounts (Products, Brands, Display)"""
    # Fetch from /adsAccounts/list endpoint
    # Filter out DSP and AMC accounts
    # Return only advertising type accounts

@router.get("/dsp-accounts")
async def list_dsp_accounts(
    current_user: Dict = Depends(RequireAuth)
):
    """List only DSP advertiser accounts"""
    # Fetch from /dsp/advertisers endpoint
    # Return DSP entities only

@router.get("/amc-instances")
async def list_amc_instances(
    current_user: Dict = Depends(RequireAuth),
    linked_account_id: Optional[str] = Query(None)
):
    """List AMC instances, optionally filtered by linked account"""
    # Fetch from /amc/instances endpoint
    # Filter by linked_account_id if provided
```

### 3.2 Cross-Account Relationship Discovery

Implement a service to discover and maintain relationships:

```python
# backend/app/services/account_relationship_service.py

class AccountRelationshipService:
    async def discover_relationships(self, user_id: str, access_token: str):
        """Discover all account relationships for a user"""

        # 1. Get all account types
        sponsored = await self.get_sponsored_accounts(access_token)
        dsp = await self.get_dsp_accounts(access_token)
        amc = await self.get_amc_instances(access_token)

        # 2. Build relationship map
        relationships = []

        # Map AMC to source accounts
        for instance in amc:
            for advertiser in instance.get('advertisers', []):
                # Check if advertiser is DSP or Sponsored
                if advertiser['advertiserId'] in [d['advertiserId'] for d in dsp]:
                    rel_type = 'dsp_feeds_amc'
                else:
                    rel_type = 'feeds_amc'

                relationships.append({
                    'source': advertiser['advertiserId'],
                    'target': instance['instanceId'],
                    'type': rel_type
                })

        # 3. Store relationships in database
        await self.store_relationships(user_id, relationships)

        return relationships
```

### 3.3 Data Synchronization

Implement incremental sync to keep data fresh:

```python
class AccountSyncService:
    async def sync_accounts(self, user_id: str, account_type: str = None):
        """Sync accounts with Amazon API"""

        if account_type == 'advertising' or account_type is None:
            await self.sync_sponsored_accounts(user_id)

        if account_type == 'dsp' or account_type is None:
            await self.sync_dsp_accounts(user_id)

        if account_type == 'amc' or account_type is None:
            await self.sync_amc_instances(user_id)

        # After syncing all accounts, update relationships
        if account_type is None:
            await self.update_account_relationships(user_id)

    async def update_account_relationships(self, user_id: str):
        """Update relationships based on latest data"""
        # Query AMC instances and their linked advertisers
        # Update account_relationships table
        # Mark stale relationships as inactive
```

## 4. Frontend Implementation

### 4.1 Page Structure

```typescript
// Main Accounts Page - Shows only Sponsored Ads
/accounts
  - Filter: account_type = 'advertising'
  - Display: Table with SP/SB/SD accounts
  - Actions: View campaigns, View reports, Settings

// DSP Subpage
/accounts/dsp
  - Filter: account_type = 'dsp'
  - Display: DSP advertisers with seat info
  - Actions: View DSP campaigns, Audience management

// AMC Subpage
/accounts/amc
  - Filter: account_type = 'amc'
  - Display: AMC instances with linked accounts
  - Show which Sponsored/DSP accounts feed data
  - Actions: View queries, Data explorer
```

### 4.2 Account Filtering Logic

```typescript
// services/accountService.ts

export const AccountService = {
  async getSponsoredAdsAccounts(): Promise<Account[]> {
    const response = await api.get('/accounts/sponsored-ads-accounts');
    return response.data.accounts;
  },

  async getDSPAccounts(): Promise<DSPAccount[]> {
    const response = await api.get('/accounts/dsp-accounts');
    return response.data.advertisers;
  },

  async getAMCInstances(linkedAccountId?: string): Promise<AMCInstance[]> {
    const params = linkedAccountId ? { linked_account_id: linkedAccountId } : {};
    const response = await api.get('/accounts/amc-instances', { params });
    return response.data.instances;
  },

  async getAccountRelationships(accountId: string): Promise<Relationship[]> {
    const response = await api.get(`/accounts/${accountId}/relationships`);
    return response.data.relationships;
  }
};
```

## 5. Migration Plan

### Phase 1: Database Schema Updates
1. Add new columns to user_accounts table
2. Create account_relationships table
3. Deploy database functions
4. Backfill account_type for existing records

### Phase 2: API Updates
1. Implement new filtered endpoints
2. Add relationship discovery service
3. Update sync logic to handle all account types
4. Add relationship management endpoints

### Phase 3: Frontend Updates
1. Create DSP subpage component
2. Create AMC subpage component
3. Update main accounts page to filter Sponsored Ads only
4. Add navigation between account type pages
5. Implement relationship visualization

### Phase 4: Data Migration
1. Run full account sync for all users
2. Discover and store all relationships
3. Validate data integrity
4. Enable new UI for users

## 6. Error Handling

### API Errors
- **403 Forbidden**: User lacks permissions (normal for DSP/AMC)
  - Store this in metadata as `access_level`
  - Show appropriate messaging in UI

- **404 Not Found**: Account doesn't exist
  - Remove from local database
  - Log for audit trail

- **429 Rate Limited**: Too many requests
  - Implement exponential backoff
  - Queue for retry

### Data Consistency
- Validate relationships periodically
- Remove orphaned relationships
- Handle account deletions cascading to relationships
- Maintain audit log of relationship changes

## 7. Performance Considerations

### Database Optimization
- Use materialized views for complex relationship queries
- Implement caching for frequently accessed relationships
- Batch relationship updates to reduce database load

### API Optimization
- Parallelize API calls where possible
- Cache account data with TTL
- Implement incremental sync to reduce full refreshes
- Use pagination for large account lists

## 8. Security Considerations

- Ensure RLS policies cover new tables
- Validate account ownership before showing relationships
- Audit all relationship modifications
- Encrypt sensitive account metadata
- Implement rate limiting per user

## Summary

This restructuring provides:
1. **Clear separation** of account types (Sponsored Ads, DSP, AMC)
2. **Proper relationship mapping** between accounts
3. **Efficient data storage** with optimized queries
4. **Scalable architecture** for future account types
5. **User-friendly navigation** with dedicated subpages

The implementation maintains backward compatibility while providing a foundation for advanced features like cross-account reporting and unified campaign management.