# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-14-amazon-accounts-api-fix/spec.md

## Technical Requirements

### API Integration Fixes

- Fix the Account Management API endpoint implementation in `backend/app/api/v1/accounts.py` (line 184) to correctly document POST method instead of GET
- Implement proper content-type header `application/vnd.listaccountsresource.v1+json` for Account Management API v1 calls
- Add full pagination support to the Profiles API endpoint (`/api/v1/accounts/amazon-profiles`) which currently lacks pagination
- Ensure all API calls include proper error handling for 429 rate limit responses with Retry-After header parsing

### Rate Limiting Implementation

- Create `backend/app/core/rate_limiter.py` with ExponentialBackoffRateLimiter class
- Implement exponential backoff algorithm with base delay of 1 second and maximum delay of 60 seconds
- Support configurable maximum retry attempts (default: 5)
- Include jitter to prevent thundering herd problem
- Respect Retry-After headers from Amazon API responses

### Token Management System

- Implement proactive token refresh in `backend/app/services/token_refresh_scheduler.py`
- Use APScheduler to check tokens every 5 minutes
- Refresh tokens 10 minutes before expiration
- Store refresh history and count in database
- Log all refresh attempts with success/failure status

### Dashboard Visualization Components

- Create account cards component showing account name, status, type, and marketplace
- Implement filtering system for account status (active, inactive, suspended, pending)
- Add sorting capabilities by name, last sync date, and status
- Create batch operations interface for sync, disconnect, and update actions
- Display synchronization health metrics with color-coded indicators

### Data Storage Optimization

- Ensure proper indexing on `user_accounts` table for amazon_account_id and user_id
- Optimize JSONB metadata queries with GIN indexes
- Implement database connection pooling for concurrent operations
- Add database-level constraints for data integrity

### Performance Criteria

- Account synchronization must complete within 30 seconds for up to 100 accounts
- Token refresh must occur with 99% success rate
- Dashboard must load account list within 2 seconds
- API rate limit errors should be reduced by 90% compared to current implementation

## External Dependencies

**apscheduler** - For proactive token refresh scheduling
**Justification:** Required for background task scheduling to refresh tokens before expiration

**httpx** - Already in use, but ensure retry capabilities are properly configured
**Justification:** Existing dependency that needs proper configuration for retry logic