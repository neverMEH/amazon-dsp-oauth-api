# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-15-accounts-restructure-multi-type/spec.md

> Created: 2025-09-15
> Version: 1.0.0

## Technical Requirements

### Frontend Requirements

- **Tab Navigation Component**: Implement shadcn/ui Tabs component with three subpages (Sponsored Ads as default, DSP, AMC) with count badges
- **Sponsored Ads Table**: Display columns for Profile ID, Entity ID, Marketplaces (array), Last Managed Date, Account Name, Status
- **DSP Table**: Display columns for Entity ID, Profile ID, Marketplace, Account Name, Status, Advertiser Type
- **AMC Table**: Display AMC instances with embedded associated account info (DSP and SP profile/entity IDs)
- **Navigation Flow**: Dashboard → Accounts (auto-loads Sponsored Ads) → Tab selection for DSP/AMC
- **Loading States**: Progressive loading with Skeleton components, Sponsored Ads loads by default, lazy-load DSP/AMC on tab selection
- **Data Fetching**: Use TanStack Query for caching and background refetching with separate query keys per account type

### Backend Requirements

- **API Endpoints Enhancement**:
  - `/api/v1/accounts/sponsored-ads` - Return Sponsored Ads accounts with profile ID, entity ID, marketplaces, last_managed_at
  - `/api/v1/accounts/dsp` - Return DSP accounts with entity ID, profile ID, marketplace data
  - `/api/v1/accounts/amc` - Return AMC instances with embedded associated DSP and SP account details
  - Add `last_managed_at` tracking to user_accounts table for management selection history

- **Service Layer Updates**:
  - Update `amazon_ads_api_service.py` to handle account type filtering
  - Create `dsp_service.py` for DSP-specific API calls to `/dsp/advertisers`
  - Create `amc_service.py` for AMC API calls to `/amc/instances`
  - Implement `account_relationship_service.py` for relationship discovery

### API Integration Requirements

- **Amazon Ads API Calls**:
  - Use `POST /adsAccounts/list` for Sponsored Ads accounts
  - Use `GET /dsp/advertisers` for DSP accounts (handle 403 gracefully)
  - Use `GET /amc/instances` for AMC instances (handle 403 gracefully)
  - Parse `advertisers` array in AMC response to build relationships

- **Error Handling**:
  - Treat 403 responses as normal for users without DSP/AMC access
  - Return empty arrays rather than errors for permission issues
  - Log access attempts for monitoring and analytics

### Performance Requirements

- Initial page load under 2 seconds for Sponsored Ads accounts
- Lazy loading for DSP/AMC tabs to reduce initial load time
- Cache account data for 5 minutes using TanStack Query
- Implement pagination for accounts exceeding 100 items
- Use database indexes on account_type and user_id columns

### UI/UX Specifications

- Full-width responsive layout maintaining existing design patterns
- Clear navigation path: Dashboard → Accounts → Sponsored Ads (default)
- Tab-based subpage navigation with active state indicators
- Sortable columns for all identifier fields (Profile ID, Entity ID, etc.)
- Date formatting for "Last Managed" column with relative time display
- AMC page shows associated accounts inline within each instance row
- Maintain purple theme color scheme across all new components

## Approach

### Implementation Strategy

1. **Phase 1: Backend API Updates**
   - Modify existing account endpoints to include account type filtering
   - Implement new DSP and AMC service classes with proper error handling
   - Add relationship discovery logic using existing account data

2. **Phase 2: Frontend Component Development**
   - Create new tab-based layout component using shadcn/ui Tabs
   - Develop account type-specific table components with shared base component
   - Implement progressive loading and caching strategies

3. **Phase 3: Integration and Testing**
   - Connect frontend components to new backend endpoints
   - Test permission handling for users without DSP/AMC access
   - Validate relationship mapping and badge display

### Data Flow Architecture

```
User Request → Tab Component → TanStack Query → API Endpoint → Service Layer → Amazon API
                    ↓                                    ↓
            Cache Management ← Response Processing ← Account Relationships
```

### Account Type Determination

- **Sponsored Ads**: Use existing `POST /adsAccounts/list` endpoint
- **DSP**: Call `GET /dsp/advertisers` and map to advertiser accounts
- **AMC**: Call `GET /amc/instances` and extract advertiser relationships

### Relationship Mapping

- Use `alternateIds` from Sponsored Ads accounts to link with DSP advertiser profiles
- Map AMC instances to advertisers using the `advertisers` array in response
- Store relationships in memory for session duration, implement caching

## External Dependencies

### Amazon Advertising API Requirements

- **Account Management API v1**: `POST /adsAccounts/list`
  - Content-Type: `application/vnd.listaccountsresource.v1+json`
  - Returns Sponsored Ads accounts with alternateIds for relationship mapping

- **DSP API**: `GET /dsp/advertisers`
  - Requires DSP access permissions
  - Returns advertiser accounts available for DSP campaigns

- **AMC API**: `GET /amc/instances`
  - Requires AMC access permissions
  - Returns AMC instances with associated advertiser relationships

### Frontend Dependencies

- **shadcn/ui Components**: Tabs, Badge, Tooltip, Card, Skeleton
- **TanStack Query**: Data fetching, caching, and state management
- **framer-motion**: Animation library for tab transitions and hover effects
- **Lucide React**: Icons for empty states and UI elements

### Database Schema Updates

```sql
-- Add account_type column to user_accounts table
ALTER TABLE user_accounts
ADD COLUMN account_type VARCHAR(20) DEFAULT 'sponsored_ads'
CHECK (account_type IN ('sponsored_ads', 'dsp', 'amc'));

-- Add index for performance
CREATE INDEX idx_user_accounts_type_user ON user_accounts(account_type, user_id);

-- Add relationship tracking table
CREATE TABLE account_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_account_id UUID REFERENCES user_accounts(id),
    child_account_id UUID REFERENCES user_accounts(id),
    relationship_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(parent_account_id, child_account_id, relationship_type)
);
```

### Environment Configuration

No additional environment variables required. Will use existing:
- `AMAZON_CLIENT_ID` and `AMAZON_CLIENT_SECRET` for API authentication
- `FERNET_KEY` for token encryption
- Existing database and authentication setup