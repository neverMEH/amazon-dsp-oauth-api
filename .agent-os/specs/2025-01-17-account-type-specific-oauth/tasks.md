# Spec Tasks

## Reference Documents
- **Main Spec**: @.agent-os/specs/2025-01-17-account-type-specific-oauth/spec.md
- **Technical Spec**: @.agent-os/specs/2025-01-17-account-type-specific-oauth/sub-specs/technical-spec.md
- **API Spec**: @.agent-os/specs/2025-01-17-account-type-specific-oauth/sub-specs/api-spec.md

## Implementation Context
This implementation replaces the "Sync from Amazon" functionality with account-type-specific OAuth flows. Users will connect accounts via "Add Sponsored Ads" and "Add DSP Advertiser" buttons, with accounts persisting locally until deleted.

## Tasks

- [x] 1. Update OAuth Service for Expanded Scopes
  - [x] 1.1 Write tests for expanded OAuth scopes in amazon_oauth_service
  - [x] 1.2 Update amazon_oauth_service.py to include DSP scope per @technical-spec (advertising::dsp_campaigns)
  - [x] 1.3 Ensure OAuth flow handles all three required scopes per @api-spec OAuth Scopes section
  - [x] 1.4 Test token storage with expanded scope information in oauth_tokens table
  - [x] 1.5 Verify all OAuth tests pass

- [x] 2. Implement Backend API Endpoints for Account Addition
  - [x] 2.1 Write tests for POST /api/v1/accounts/sponsored-ads/add endpoint per @api-spec
  - [x] 2.2 Write tests for POST /api/v1/accounts/dsp/add endpoint per @api-spec
  - [x] 2.3 Create add_sponsored_ads endpoint that checks tokens and calls Amazon API per @api-spec (POST /adsAccounts/list)
  - [x] 2.4 Create add_dsp_advertisers endpoint that checks tokens and calls Amazon API per @api-spec (GET /dsp/advertisers)
  - [x] 2.5 Implement token validation and OAuth redirect logic per @technical-spec OAuth Token Reuse Strategy
  - [x] 2.6 Add proper error handling for token expiry and missing scopes per @api-spec Errors section
  - [x] 2.7 Verify all API endpoint tests pass

- [x] 3. Update Account Service for Account-Type-Specific Fetching
  - [x] 3.1 Write tests for fetch_and_store_sponsored_ads method per @technical-spec Service Layer Changes
  - [x] 3.2 Write tests for fetch_and_store_dsp_advertisers method per @technical-spec Service Layer Changes
  - [x] 3.3 Implement fetch_and_store_sponsored_ads using Amazon API v3.0 per @api-spec Amazon API Integration Details
  - [x] 3.4 Implement fetch_and_store_dsp_advertisers using DSP API with profile scope header per @api-spec
  - [x] 3.5 Remove all sync-related methods from account_service per @spec Spec Scope item 5
  - [x] 3.6 Update database storage to properly set account_type field ('advertising' for Sponsored Ads, 'dsp' for DSP)
  - [x] 3.7 Verify all service tests pass

- [ ] 4. Update Frontend API Client and Service Layer
  - [ ] 4.1 Write tests for addSponsoredAdsAccounts service method
  - [ ] 4.2 Write tests for addDSPAdvertisers service method
  - [ ] 4.3 Update accountService.ts to call new add endpoints per @api-spec Backend API Endpoints
  - [ ] 4.4 Handle OAuth redirect responses in frontend (requires_auth flag handling)
  - [ ] 4.5 Remove all sync-related service methods per @spec Out of Scope
  - [ ] 4.6 Update error handling for OAuth flow initiation per @technical-spec OAuth Flow UI
  - [ ] 4.7 Verify all frontend service tests pass

- [ ] 5. Connect UI Components to New Backend Endpoints
  - [ ] 5.1 Write component tests for new Add button behaviors (already implemented per @technical-spec UI Components)
  - [ ] 5.2 Update handleAddSponsoredAds to use new add endpoint instead of sync per @spec User Stories
  - [ ] 5.3 Update handleAddDSP to use new add endpoint instead of sync per @spec User Stories
  - [ ] 5.4 Implement OAuth redirect handling in button click handlers per @technical-spec OAuth Flow UI
  - [ ] 5.5 Remove all references to sync functionality from AccountManagementPage per @spec Spec Scope item 5
  - [ ] 5.6 Test end-to-end flow for both account types per @spec Expected Deliverable
  - [ ] 5.7 Verify loading states and error handling work correctly per @technical-spec UI Components
  - [ ] 5.8 Ensure all component tests pass