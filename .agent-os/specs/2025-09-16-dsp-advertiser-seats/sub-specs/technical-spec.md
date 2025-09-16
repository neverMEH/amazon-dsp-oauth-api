# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-16-dsp-advertiser-seats/spec.md

> Created: 2025-09-16
> Version: 1.0.0

## Technical Requirements

### API Integration Requirements

- **Endpoint Implementation**: POST /dsp/v1/seats/advertisers/current/list
- **Authentication Headers**:
  - Authorization: Bearer token with advertising::dsp_campaigns scope
  - Amazon-Ads-AccountId: DSP Advertiser ID (REQUIRED)
  - Amazon-Advertising-API-ClientId: Client ID
  - Amazon-Advertising-API-Scope: Profile ID (optional for filtering)
- **Request Payload Structure**:
  - exchangeIdFilter: Array of exchange IDs (optional)
  - maxResults: Integer (1-200, default 200)
  - nextToken: String for pagination
- **Response Handling**:
  - Parse advertiserSeats array containing advertiserId and currentSeats
  - Handle pagination with nextToken
  - Process seat information including exchangeId, exchangeName, dealCreationId, spendTrackingId

### Backend Service Implementation

- **New Service Method**: `list_advertiser_seats()` in dsp_amc_service.py
- **Error Handling**:
  - 401: Token expired - trigger refresh
  - 403: Insufficient permissions - return empty result with error message
  - 429: Rate limiting - implement exponential backoff
  - 400: Invalid advertiser ID - specific error class
- **Rate Limiting**: Use existing ExponentialBackoffRateLimiter with "dsp_seats" key
- **Logging**: Structured logging with advertiser_id, seat_count, pagination status

### Database Schema Updates

- **user_accounts Table Modification**:
  - Add seats_metadata JSONB column for DSP accounts
  - Store exchange information, last sync time, total seats count
- **Metadata Structure**:
  ```json
  {
    "seats": {
      "exchanges": [],
      "last_seats_sync": "ISO 8601 timestamp",
      "total_seats": 0
    }
  }
  ```
- **Automatic Updates**: Update metadata on each successful API call

### API Endpoint Specification

- **Route**: GET /api/v1/accounts/dsp/{advertiser_id}/seats
- **Query Parameters**:
  - exchange_ids: Optional list of exchange IDs
  - max_results: Integer (1-200)
  - next_token: Pagination token
  - profile_id: Optional profile ID
- **Authentication**: Clerk user authentication required
- **Validation**: Verify user owns the DSP advertiser account
- **Response Enhancement**: Add timestamp and cached flag to API response

### Frontend Requirements

- **New DSP Tab Component**:
  - Location: src/components/account/DSPSeatsTab.tsx
  - Display advertiser seats in a data table format
  - Show exchange name, seat IDs, and sync status
- **Filtering UI**:
  - Multi-select dropdown for exchange filtering
  - Clear filters button
  - Results count display
- **Pagination Controls**:
  - Next/Previous buttons
  - Page size selector (10, 25, 50, 100, 200)
  - Current page indicator
- **Visual Indicators**:
  - Last sync timestamp
  - Loading states during API calls
  - Empty state for no seats
  - Error states with retry options

### Performance Criteria

- **API Response Time**: Target < 2 seconds for initial load
- **Caching Strategy**:
  - Cache seat data for 5 minutes
  - Show cached indicator in UI
  - Manual refresh button to bypass cache
- **Pagination Performance**: Load maximum 200 seats per request
- **Frontend Rendering**: Virtual scrolling for large datasets (>100 seats)

### Security Requirements

- **Token Security**: Use existing Fernet encryption for stored tokens
- **Access Control**: Verify user ownership of advertiser ID before data access
- **Audit Logging**: Log all seat data access in auth_audit_log table
- **Rate Limiting**: Implement per-user rate limiting for seat queries

### Testing Requirements

- **Unit Tests**:
  - Test seat API service method
  - Mock Amazon API responses
  - Test error scenarios
- **Integration Tests**:
  - Full API endpoint testing
  - Database update verification
  - Token refresh flow
- **Frontend Tests**:
  - Component rendering tests
  - Filter functionality
  - Pagination behavior

## Approach

### Implementation Strategy

1. **Backend Development First**: Implement DSP seats API service and endpoint
2. **Database Schema Migration**: Add seats_metadata column to user_accounts table
3. **Frontend Integration**: Create DSP tab component with seat visualization
4. **Testing & Validation**: Comprehensive testing across all layers
5. **Performance Optimization**: Implement caching and pagination optimizations

### Integration Points

- **Existing DSP Service**: Extend current dsp_amc_service.py with new seat methods
- **Account Management**: Integrate with existing account selection and filtering
- **Token Management**: Leverage existing token refresh and encryption services
- **UI Components**: Reuse existing table components and design patterns

## External Dependencies

### Amazon Advertising API
- DSP Seats Management API v1
- Requires advertising::dsp_campaigns scope
- Rate limits apply (documented in Amazon API specs)

### Database
- PostgreSQL JSONB support for metadata storage
- Migration scripts for schema updates

### Frontend Libraries
- React Table for data grid functionality
- React Hook Form for filter management
- Tanstack Query for API state management