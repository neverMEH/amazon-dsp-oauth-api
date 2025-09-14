# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/fix-amazon-accounts-listing/spec.md

> Created: 2025-09-14
> Status: Ready for Implementation

## Tasks

### 1. Amazon Ads API v3.0 Account Management Integration

**Goal:** Implement proper Amazon Advertising API v3.0 Account Management endpoint integration with correct request/response handling

1.1 **Write comprehensive tests for Amazon Account Management API integration**
   - Test POST /adsAccounts/list endpoint with correct headers
   - Test v3.0 response format parsing (adsAccounts field)
   - Test alternateIds array handling with countryCode/entityId/profileId mapping
   - Test pagination with nextToken and maxResults parameters
   - Test error handling for partially created accounts
   - Mock Amazon API responses for different account statuses

1.2 **Update AmazonAdsApiService to use correct v3.0 Account Management endpoint**
   - Change from GET /v2/profiles to POST /adsAccounts/list
   - Update request headers to use application/vnd.listaccountsresource.v1+json
   - Implement proper request body structure for pagination
   - Handle v3.0 response format with adsAccounts field (not accounts)

1.3 **Implement alternateIds processing and country-specific profile mapping**
   - Parse alternateIds array from API response
   - Map countryCode to profileId for each account
   - Store profile mappings in user_accounts.metadata JSONB field
   - Handle multiple country profiles per account

1.4 **Add proper error handling for account statuses**
   - Handle CREATED, DISABLED, PARTIALLY_CREATED, PENDING statuses
   - Process errors object for partially created accounts
   - Implement retry logic for temporary failures
   - Log detailed error information for debugging

1.5 **Implement pagination support for account listing**
   - Handle nextToken for paginated responses
   - Set appropriate maxResults parameter (default 100)
   - Implement recursive fetching for all pages
   - Add pagination state management

1.6 **Verify all Amazon API integration tests pass**
   - Run pytest tests/test_amazon_ads_api_v3.py -v
   - Validate API response format compliance
   - Confirm error handling scenarios work correctly

### 2. Database Schema and Data Storage Enhancement

**Goal:** Properly store Amazon account data in Supabase with correct field mappings and metadata handling

2.1 **Write tests for enhanced user_accounts table operations**
   - Test amazon_account_id mapping to adsAccountId from API
   - Test metadata JSONB storage for alternateIds and countryCodes
   - Test account status enum handling
   - Test bulk account insertion and updates
   - Test account linking to users

2.2 **Update user_accounts model to handle v3.0 API data structure**
   - Map amazon_account_id to adsAccountId from API response
   - Store alternateIds array in metadata JSONB field
   - Store countryCodes array in metadata field
   - Add account status validation for v3.0 statuses

2.3 **Implement account data synchronization service**
   - Create AccountSyncService for batch account operations
   - Handle account creation, updates, and status changes
   - Implement conflict resolution for existing accounts
   - Add last_synced_at timestamp tracking

2.4 **Add database migration for enhanced account storage**
   - Create migration to update user_accounts table structure
   - Add indexes for amazon_account_id and status fields
   - Add constraints for required fields
   - Update existing data to new format if needed

2.5 **Implement account metadata query utilities**
   - Add methods to query accounts by country code
   - Add methods to get profile IDs for specific countries
   - Add account status filtering capabilities
   - Implement efficient JSONB queries for metadata

2.6 **Verify all database operation tests pass**
   - Run pytest tests/test_models.py -v
   - Test account CRUD operations
   - Validate metadata storage and retrieval
   - Confirm migration applies successfully

### 3. Token Management and Error Handling Improvements

**Goal:** Enhance token refresh system and implement comprehensive error handling for API failures

3.1 **Write tests for enhanced token refresh and error handling**
   - Test proactive token refresh before expiration
   - Test exponential backoff retry logic
   - Test rate limiting compliance
   - Test token refresh failure scenarios
   - Test audit logging for all token operations

3.2 **Implement proactive token refresh scheduler**
   - Update TokenRefreshScheduler to refresh tokens 10 minutes before expiration
   - Add configurable refresh buffer time in application_config
   - Implement background task scheduling
   - Add health checks for scheduler service

3.3 **Enhance retry logic with exponential backoff**
   - Implement ExponentialBackoffRateLimiter for API calls
   - Add configurable retry delays and max attempts
   - Handle rate limiting with Retry-After header
   - Log retry attempts in auth_audit_log

3.4 **Add comprehensive error categorization and handling**
   - Categorize API errors (authentication, rate limit, server, client)
   - Implement specific handling for each error type
   - Add user-friendly error messages
   - Store detailed error context in audit log

3.5 **Implement circuit breaker pattern for API resilience**
   - Add circuit breaker to prevent cascading failures
   - Configure failure thresholds and recovery timeouts
   - Implement fallback responses for degraded service
   - Add monitoring and alerting for circuit breaker state

3.6 **Verify all token management tests pass**
   - Run pytest tests/test_auth.py -v
   - Test token refresh scenarios
   - Validate error handling paths
   - Confirm audit logging works correctly

### 4. Frontend Account Display and Management

**Goal:** Create React components to display Amazon advertising accounts with proper error handling and loading states

4.1 **Write tests for account display components**
   - Test AccountList component rendering
   - Test account status display and filtering
   - Test pagination controls
   - Test error state handling
   - Test loading state management

4.2 **Create AccountList component with v3.0 data structure**
   - Display account name, ID, and status
   - Show country codes and alternate profiles
   - Implement account status badges
   - Add account selection functionality
   - Handle empty states gracefully

4.3 **Implement account filtering and search capabilities**
   - Add search by account name or ID
   - Filter by account status (active, disabled, etc.)
   - Filter by country code
   - Add sort options (name, status, date)
   - Persist filter state in URL parameters

4.4 **Add account management actions**
   - Implement account refresh/sync button
   - Add account connection status indicator
   - Show last sync timestamp
   - Add manual account re-authentication
   - Implement bulk account operations

4.5 **Create responsive account card design**
   - Use shadcn/ui components for consistent styling
   - Implement mobile-responsive layout
   - Add loading skeletons for better UX
   - Show account metadata in expandable sections
   - Add tooltips for status explanations

4.6 **Verify all frontend component tests pass**
   - Run npm test for account-related components
   - Test component rendering with mock data
   - Validate responsive behavior
   - Confirm accessibility compliance

### 5. API Endpoint Updates and Integration Testing

**Goal:** Update API endpoints to serve v3.0 account data and ensure end-to-end functionality

5.1 **Write integration tests for updated API endpoints**
   - Test GET /api/v1/accounts/amazon-ads-accounts with v3.0 format
   - Test account filtering and pagination
   - Test error responses and status codes
   - Test authentication and authorization
   - Test rate limiting behavior

5.2 **Update accounts API endpoint to return v3.0 format**
   - Modify response schema to match v3.0 adsAccounts format
   - Include alternateIds and countryCodes in response
   - Add pagination support with nextToken
   - Handle account status filtering
   - Add proper error responses

5.3 **Implement account sync endpoint**
   - Create POST /api/v1/accounts/sync endpoint
   - Trigger manual account synchronization
   - Return sync status and progress
   - Handle concurrent sync requests
   - Add rate limiting for sync operations

5.4 **Add account management endpoints**
   - Implement GET /api/v1/accounts/{id}/profiles for country profiles
   - Add PUT /api/v1/accounts/{id}/settings for account preferences
   - Create DELETE /api/v1/accounts/{id}/disconnect for unlinking
   - Add GET /api/v1/accounts/{id}/status for real-time status
   - Implement proper authorization for account access

5.5 **Update API documentation and schemas**
   - Update OpenAPI/Swagger documentation
   - Add v3.0 response schema definitions
   - Document new account management endpoints
   - Add error response documentation
   - Update Pydantic schemas for validation

5.6 **Verify all API integration tests pass**
   - Run pytest tests/test_api/ -v
   - Test complete account listing flow
   - Validate API response formats
   - Confirm error handling works end-to-end
   - Test authentication and authorization flows