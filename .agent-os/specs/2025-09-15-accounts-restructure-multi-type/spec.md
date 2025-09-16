# Spec Requirements Document

> Spec: Accounts Page Multi-Type Restructure
> Created: 2025-09-15

## Overview

Restructure the accounts page with three subpages for Sponsored Ads (default), DSP, and AMC accounts, displaying profile IDs, entity IDs, marketplaces, and management status. This will provide clearer account type separation while AMC accounts will show their associated DSP and Sponsored Ads account information.

## User Stories

### Account Type Navigation

As an advertising professional, I want to land on the Sponsored Ads subpage by default when clicking Accounts from the dashboard, and easily navigate between Sponsored Ads, DSP, and AMC subpages, so that I can view all my different account types with their specific identifiers.

Users will navigate from Dashboard → Accounts → Sponsored Ads (default subpage). They can switch to DSP or AMC subpages using tabs. The Sponsored Ads page shows profile IDs, entity IDs, marketplaces, and last managed date. DSP shows similar identifiers, while AMC displays instances with their associated account information.

### AMC Account Associations

As a user with AMC access, I want to see my AMC accounts/instances with their associated DSP and Sponsored Ads account information, so that I can understand which accounts feed data into each AMC instance.

When viewing the AMC subpage, users will see AMC instances with embedded information showing the associated DSP and Sponsored Ads accounts, including their profile IDs and entity IDs. This provides clear visibility into the data sources for each AMC instance.

### Progressive Access Management

As a user with limited permissions, I want to see helpful empty states when I don't have DSP or AMC access, so that I understand what's required to gain access.

Users without DSP or AMC access will see informative empty states explaining the requirements and providing actionable next steps, rather than confusing error messages or blank screens.

## Spec Scope

1. **Sponsored Ads Subpage (Default)** - Display Sponsored Ads accounts with profile ID, entity ID, marketplaces, and last managed timestamp
2. **DSP Accounts Subpage** - Show DSP accounts with entity ID, profile ID, and marketplace information
3. **AMC Instances Subpage** - Display AMC accounts/instances with embedded associated DSP and Sponsored Ads account information
4. **Navigation Flow** - Dashboard → Accounts (defaults to Sponsored Ads) → Tab navigation between subpages
5. **Account Data Display** - Show specific identifiers (profile ID, entity ID) and operational data (marketplaces, last managed date)

## Out of Scope

- Account creation or provisioning workflows
- Direct AMC query execution interface
- DSP campaign management features
- Cross-account data aggregation or reporting
- Mobile-specific responsive layouts (desktop-first approach)

## Expected Deliverable

1. Users can navigate from Dashboard to Accounts page, which defaults to Sponsored Ads subpage with profile/entity IDs and last managed dates
2. Tab navigation allows switching between Sponsored Ads, DSP, and AMC subpages with account-specific data
3. AMC subpage displays instances with embedded associated DSP and Sponsored Ads account information