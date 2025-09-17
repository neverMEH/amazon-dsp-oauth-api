# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-01-17-account-type-specific-oauth/spec.md

## Technical Requirements

### Frontend Requirements

#### UI Components (shadcn/ui Implementation)

- **TabActionButton Component**: Reusable button following shadcn/ui patterns
  ```tsx
  interface TabActionButtonProps {
    accountType: AccountType;
    onClick: () => void;
    isLoading?: boolean;
    disabled?: boolean;
    className?: string;
  }
  ```
  - Uses shadcn/ui `Button` component with `variant="default"`
  - Plus icon from lucide-react (h-4 w-4 sizing)
  - Loading state with `animate-pulse` on icon and opacity changes
  - Responsive text: Full label on desktop, "Add" on mobile
  - Accessibility: aria-label, aria-busy, aria-disabled attributes
  - Transitions: `transition-all duration-200`

- **Tab-Specific Implementations**:
  - **Sponsored Ads Tab**: "Add Sponsored Ads" button in tab header
  - **DSP Tab**: "Add DSP Advertiser" button in tab header
  - **AMC Tab**: "Add AMC Instance" button in tab header
  - Position: Right-aligned in tab content header
  - States: Disabled during initial load, loading state during add operation

- **Delete/Disconnect Action**: Maintain existing delete functionality in account tables
  - Confirmation dialog before deletion
  - Remove from local database only
  - Update UI immediately after deletion

#### OAuth Flow UI
- Loading state during OAuth redirect
- Error handling for OAuth failures with user-friendly messages
- Success notification after accounts are connected
- Handle OAuth callback in dedicated route

#### Component Changes
- Remove all "Sync from Amazon" buttons and related UI
- Remove sync-related loading states and progress indicators
- Remove refresh token UI elements
- Update AccountManagementPage component
- Update AccountTypeTabs component
- Update AccountTypeTable component actions

### Backend Requirements

#### OAuth Token Reuse Strategy
- **Leverage Existing Infrastructure**: Use the current OAuth token system in `oauth_tokens` table
- **Single Token Per User**: One set of Amazon OAuth tokens per user, not per account type
- **Shared Authentication**: Both Sponsored Ads and DSP use the same stored tokens
- **Token Refresh**: Existing `token_refresh_scheduler.py` handles automatic refresh

#### OAuth Flow Modifications
- **Scope Expansion**: Update `amazon_oauth_service.py` to include all required scopes:
  ```python
  scopes = [
      "advertising::campaign_management",
      "advertising::account_management",
      "advertising::dsp_campaigns"
  ]
  ```
- **Check Existing Tokens**: Before initiating OAuth, check if user already has valid tokens
- **Fetch on Demand**: Use existing tokens to fetch accounts when "Add" button is clicked

#### New Endpoints (Using Existing Tokens)
- **POST /api/v1/accounts/sponsored-ads/add**
  - Check for existing valid OAuth tokens
  - If no tokens, return redirect URL for OAuth flow
  - If tokens exist, fetch Sponsored Ads accounts from Amazon API
  - Store fetched accounts in `user_accounts` table
  - Return list of added accounts

- **POST /api/v1/accounts/dsp/add**
  - Check for existing valid OAuth tokens
  - If no tokens, return redirect URL for OAuth flow with DSP scopes
  - If tokens exist, fetch DSP advertisers from Amazon API
  - Store fetched advertisers in `user_accounts` table
  - Return list of added advertisers

- **DELETE /api/v1/accounts/{account_id}**
  - Removes account from `user_accounts` table only
  - Does NOT affect OAuth tokens
  - Returns success confirmation

#### Service Layer Changes
- Update `amazon_oauth_service.py` to support expanded scopes
- Modify `account_service.py` to add account-type-specific fetching methods:
  - `fetch_and_store_sponsored_ads()`
  - `fetch_and_store_dsp_advertisers()`
- Remove all sync-related methods from services
- Keep token refresh infrastructure intact

### Data Persistence
- Accounts stored in `user_accounts` table with appropriate `account_type`
- No automatic refresh or sync mechanisms
- Accounts persist until explicitly deleted
- Store initial fetch timestamp in `connected_at` field
- Remove `last_synced_at` updates

### Security Considerations
- Separate OAuth state tokens for each flow type
- CSRF protection with state parameter validation
- Secure token storage with encryption
- Rate limiting on OAuth endpoints
- Audit logging for account connections and deletions

### Performance Criteria
- OAuth flow completion within 5 seconds
- Account fetching and storage within 3 seconds
- Immediate UI update after account deletion
- No background sync processes or scheduled tasks