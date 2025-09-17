# Spec Requirements Document

> Spec: Account Type Specific OAuth Connection
> Created: 2025-01-17

## Overview

Replace the existing "Sync from Amazon" functionality with account-type-specific OAuth flows that allow users to connect new Sponsored Ads accounts or DSP advertisers directly through dedicated buttons on each tab. This feature removes automatic syncing in favor of explicit user-initiated account connections with local persistence.

## User Stories

### Connecting Sponsored Ads Accounts

As an advertising manager, I want to connect my Sponsored Ads accounts through a dedicated OAuth flow, so that I can manage and monitor my sponsored advertising campaigns without manual synchronization.

The user navigates to the Sponsored Ads tab and clicks the "Add Sponsored Ads" button. This initiates an OAuth flow that authenticates with Amazon, retrieves all Sponsored Ads accounts associated with their Amazon account, and persists them locally. The accounts remain in the database until explicitly deleted by the user.

### Connecting DSP Advertisers

As a DSP campaign manager, I want to connect my DSP advertiser accounts through a separate OAuth flow, so that I can access and manage my demand-side platform advertisers independently from other account types.

The user navigates to the DSP tab and clicks the "Add DSP Advertiser" button. This triggers a DSP-specific OAuth flow that authenticates with Amazon, fetches all DSP advertisers linked to their credentials, and stores them in the local database. These advertisers persist locally without requiring re-synchronization.

### Managing Connected Accounts

As a user, I want to delete accounts I no longer need from my local database, so that I can maintain a clean list of only the accounts I actively manage.

Users can delete any connected account directly from the UI, which removes it from the local database. If they need the account again, they must re-connect it through the appropriate OAuth flow.

## Spec Scope

1. **Account-Type-Specific Add Buttons** - Replace the generic "Sync from Amazon" with "Add Sponsored Ads" button on Sponsored Ads tab and "Add DSP Advertiser" button on DSP tab
2. **Dedicated OAuth Flows** - Implement separate OAuth authentication flows for Sponsored Ads and DSP account connections
3. **Local Account Persistence** - Store connected accounts in the database without automatic re-synchronization
4. **Account Deletion UI** - Maintain ability to delete/disconnect accounts from the UI with database removal
5. **Remove Sync Infrastructure** - Remove all existing sync-related code, endpoints, and UI components

## Out of Scope

- AMC account connection flow (no changes to AMC tab functionality)
- Automatic background synchronization of account data
- Bulk account operations or batch connections
- Account data refresh/update functionality (accounts persist as initially retrieved)
- Migration of existing connected accounts

## Expected Deliverable

1. Users can connect Sponsored Ads accounts by clicking "Add Sponsored Ads" button which triggers OAuth flow and persists accounts locally
2. Users can connect DSP advertisers by clicking "Add DSP Advertiser" button which triggers separate OAuth flow and persists advertisers locally
3. All sync-related functionality is removed from the UI and backend, with accounts persisting in database unless explicitly deleted