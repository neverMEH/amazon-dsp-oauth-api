# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Amazon DSP OAuth API - A FastAPI backend with Next.js frontend for managing Amazon Advertising API authentication and campaign insights. Uses Clerk for user authentication, Supabase for database, and implements automatic token refresh with comprehensive error handling.

## Commands

### Backend Development
```bash
# Run backend server
cd backend
uvicorn app.main:app --reload --port 8000

# Run tests
cd backend
pytest tests/ -v
pytest tests/test_auth.py -v  # Run specific test file
pytest tests/test_amazon_ads_api_v3.py -v  # Test API v3.0 implementation

# Apply database migrations
cd backend
python run_migrations.py
python apply_migration.py  # Apply pending migrations

# Lint and format
cd backend
black .
mypy app/
```

### Frontend Development
```bash
# Run frontend dev server
cd frontend
npm run dev

# Build frontend
cd frontend
npm run build

# Lint frontend
cd frontend
npm run lint
```

### Database Operations
```bash
# Debug tokens
python debug_tokens.py

# Clean up tokens
python cleanup_tokens.py

# Test authentication
python test_auth_status.py
```

## Architecture

### Backend Structure
- **app/api/v1/** - API endpoints (auth, health, users, webhooks, accounts, settings)
- **app/core/** - Core utilities (exceptions, rate limiting, security)
- **app/db/** - Database connection and session management
- **app/models/** - SQLAlchemy models (User, Account, OAuthToken, etc.)
- **app/schemas/** - Pydantic schemas for request/response validation
- **app/services/** - Business logic (amazon_ads_api, clerk_service, refresh_service, token_refresh_scheduler)
- **app/middleware/** - Error handling and request processing

### Frontend Structure
- **src/components/** - Reusable React components using shadcn/ui
  - **account/AccountTable.tsx** - Table view with sortable columns, status indicators, and inline actions
  - **account/AccountManagementPage.tsx** - Main accounts page (table-only view as of latest update)
- **src/pages/** - Page components (Dashboard, Settings, Accounts)
- **src/services/** - API client services
- **src/stores/** - Zustand state management
- **src/hooks/** - Custom React hooks
- **src/types/** - TypeScript type definitions

### Recent UI Updates (2025)
- **Full-width responsive layouts** - All main screens (Dashboard, Accounts, Settings) now use full viewport width
- **Enhanced table view** - Professional data table with sorting, visual status indicators, and tooltips
- **Removed grid/tile view** - Accounts page now uses table-only view for consistency and simplicity
- **Animated status cards** - Gradient backgrounds with hover effects using framer-motion
- **Improved information hierarchy** - Better use of colors, icons, and spacing throughout

### Key Services

#### Token Refresh System
- Automatic background refresh before expiration (5-minute buffer)
- Exponential backoff retry logic with configurable delays
- Comprehensive audit logging in `auth_audit_log` table
- Rate limiting protection (2 requests per second default)
- Token refresh scheduler checks every 60 seconds (configurable)

#### Amazon Ads API Integration (v3.0)
- OAuth 2.0 flow with required scopes:
  - `advertising::campaign_management`
  - `advertising::account_management`
  - `advertising::dsp_campaigns`
  - `advertising::reporting`
- Encrypted token storage using Fernet encryption
- **Account Management API v1** (`POST /adsAccounts/list`)
  - Returns API v3.0 response format with `adsAccounts` field (not `accounts`)
  - Includes `alternateIds` array with country-specific profile mappings
  - Each alternateId contains: `countryCode`, `entityId`, `profileId`
  - Handles account statuses: CREATED, DISABLED, PARTIALLY_CREATED, PENDING
  - Supports pagination with `nextToken` and `maxResults` (100 default)
  - Returns errors object for partially created accounts
- **DSP Campaign Insights API** (`/dsp/campaigns`)
  - Requires advertiser_id parameter
  - Returns campaign performance metrics
- **Legacy Profiles API v2** (`GET /v2/profiles`)
  - Backwards compatibility endpoint
  - Missing pagination implementation (known issue)
- Automatic token refresh with retry logic

#### Clerk Authentication
- User management with multi-tenancy support
- Webhook handling for user sync
- Account linking between Clerk and Amazon accounts

## Database Schema

### Core Tables

#### users
- `id`: UUID (Primary Key)
- `clerk_user_id`: VARCHAR(255) - Clerk authentication ID
- `email`: VARCHAR(255)
- `first_name`, `last_name`: VARCHAR(100)
- `profile_image_url`: TEXT
- `created_at`, `updated_at`: TIMESTAMP WITH TIME ZONE
- `last_login_at`: TIMESTAMP

#### user_accounts
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key → users)
- `account_name`: VARCHAR(255)
- `amazon_account_id`: VARCHAR(255) - Maps to `adsAccountId` from API
- `marketplace_id`: VARCHAR(50)
- `account_type`: VARCHAR(50) - 'advertising', 'vendor', 'seller'
- `is_default`: BOOLEAN
- `status`: VARCHAR(50) - 'active', 'inactive', 'suspended', 'pending'
- `connected_at`: TIMESTAMP
- `last_synced_at`: TIMESTAMP
- `metadata`: JSONB - Stores countryCodes, alternateIds, errors from API

#### oauth_tokens
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key → users)
- `encrypted_access_token`: TEXT - Fernet encrypted
- `encrypted_refresh_token`: TEXT - Fernet encrypted
- `token_type`: VARCHAR(50) - 'Bearer'
- `expires_at`: TIMESTAMP WITH TIME ZONE
- `scope`: TEXT
- `refresh_count`: INTEGER
- `last_refresh`: TIMESTAMP

#### Other Tables
- **oauth_states** - CSRF protection for OAuth flow (10-minute expiry)
- **auth_audit_log** - Authentication event tracking with IP and user agent
- **application_config** - Dynamic configuration (refresh intervals, retry settings)
- **rate_limit_buckets** - API rate limiting per endpoint

## API Endpoints

### Authentication
- `GET /api/v1/auth/amazon/login` - Initiate OAuth
- `GET /api/v1/auth/amazon/callback` - OAuth callback
- `GET /api/v1/auth/status` - Check auth status
- `POST /api/v1/auth/refresh` - Manual token refresh

### Amazon Ads API
- `GET /api/v1/accounts/amazon-ads-accounts` - List advertising accounts (v3.0 format)
- `GET /api/v1/accounts/amazon-profiles` - Legacy profiles endpoint
- `GET /api/v1/accounts/{id}/campaigns` - Get DSP campaigns
- `POST /api/v1/accounts/{id}/batch` - Batch account operations

### User Management
- `GET /api/v1/users/me` - Current user profile
- `POST /api/v1/webhooks/clerk` - Clerk webhook handler

## Environment Variables

Required in `.env`:
- `AMAZON_CLIENT_ID` - Amazon OAuth client ID
- `AMAZON_CLIENT_SECRET` - Amazon OAuth client secret
- `FERNET_KEY` - Encryption key for tokens
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service key
- `CLERK_SECRET_KEY` - Clerk authentication
- `CLERK_WEBHOOK_SECRET` - Webhook verification

## Amazon Advertising API Details

### API v3.0 Response Format

The Account Management API returns responses in v3.0 format:
```json
{
  "adsAccounts": [
    {
      "adsAccountId": "string",
      "accountName": "string",
      "status": "CREATED|DISABLED|PARTIALLY_CREATED|PENDING",
      "alternateIds": [
        {
          "countryCode": "US",
          "entityId": "string",
          "profileId": number
        }
      ],
      "countryCodes": ["US", "CA", "MX"],
      "errors": {}
    }
  ],
  "nextToken": "string"
}
```

### API Endpoints and Headers

#### Account Management API v1
- **Endpoint**: `POST /adsAccounts/list`
- **Content-Type**: `application/vnd.listaccountsresource.v1+json`
- **Accept**: `application/vnd.listaccountsresource.v1+json`
- **Note**: Returns v3.0 response format despite being v1 endpoint

#### Profiles API v2 (Legacy)
- **Endpoint**: `GET /v2/profiles`
- **Content-Type**: `application/json`
- **Issue**: Currently lacks pagination implementation

#### DSP API
- **Endpoint**: `GET /dsp/accounts`, `/dsp/campaigns`
- **Requires**: Profile ID in scope header

#### Required Headers
- `Authorization: Bearer {access_token}`
- `Amazon-Advertising-API-ClientId: {client_id}`
- `Amazon-Advertising-API-Scope: {profile_id}` (for profile-specific calls)

## Testing Strategy

- Unit tests for services and utilities
- Integration tests for API endpoints
- Amazon API v3.0 response format validation
- Mock Amazon API responses for testing
- Test token refresh scenarios
- Verify rate limiting behavior

## Common Tasks

### Adding New API Endpoint
1. Create schema in `app/schemas/`
2. Add endpoint in `app/api/v1/`
3. Implement service logic in `app/services/`
4. Add tests in `backend/tests/`
5. Update frontend API client in `src/services/`

### Debugging Authentication Issues
1. Check `auth_audit_log` table for error details
2. Review `backend/app/services/amazon_oauth_service.py` for OAuth flow
3. Verify token encryption/decryption in `app/services/encryption_service.py`
4. Check rate limiting in `app/core/rate_limiter.py`

### Database Migrations
1. Create migration file in `backend/migrations/`
2. Run `python run_migrations.py` to apply
3. Test rollback scenarios
4. Update models in `app/models/`

## Known Issues & Planned Improvements

### Current Issues
1. **Documentation Inconsistency**: Some code comments incorrectly state GET for Account Management API (should be POST)
2. **Profiles API Pagination**: `/v2/profiles` endpoint lacks pagination implementation
3. **Rate Limiting**: Could be enhanced with exponential backoff (implementation in `app/core/rate_limiter.py`)

### Missing Features (Per AMAZON_API_IMPLEMENTATION_PLAN.md)
1. **Account Registration**: `POST /adsAccounts/register` endpoint not implemented
2. **Reporting API**: Full reporting service with report generation/download
3. **Advanced DSP Features**: Campaign management, audience targeting, creative management
4. **Proactive Token Refresh**: Currently reactive, should refresh before expiration

### Planned Services
- **TokenRefreshScheduler** (`app/services/token_refresh_scheduler.py`) - Proactive refresh with 10-minute buffer
- **AmazonReportingService** - Handle report creation, status checking, and downloads
- **DSPCampaignService** - Full DSP campaign management

## Important Considerations

- Always encrypt sensitive data (tokens, secrets) using Fernet encryption
- Implement proper error handling with structured logging (structlog)
- Use rate limiting for external API calls (ExponentialBackoffRateLimiter)
- Maintain audit trail for security events in `auth_audit_log` table
- Test token refresh edge cases thoroughly
- Follow Amazon Ads API v3.0 specifications (see AMAZON_API_INTEGRATION.md and AMAZON_API_IMPLEMENTATION_PLAN.md)
- Ensure Clerk webhook signatures are verified
- Account Management API uses POST method, not GET
- Response includes `adsAccounts` field (v3.0), not `accounts`
- Handle rate limiting with Retry-After header
- Implement CSRF protection with state tokens (10-minute expiry)