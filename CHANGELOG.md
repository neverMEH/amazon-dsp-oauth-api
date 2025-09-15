# Changelog

All notable changes to the Amazon DSP OAuth API project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-01-15

### Added
- Professional table view component (`AccountTable.tsx`) with sortable columns for accounts page
- Animated status overview cards with gradient backgrounds and hover effects
- Visual status indicators with colored icons in table view
- Tooltips throughout the UI for additional information
- Smooth transitions between different views using framer-motion

### Changed
- **BREAKING**: Removed grid/tile view from accounts page - now table-only view
- All main screens (Dashboard, Accounts, Settings) now use full viewport width
- Removed max-width containers (`max-w-7xl`) across all pages
- Updated responsive padding pattern to `px-4 sm:px-6 lg:px-8` consistently
- Enhanced grid layouts with more responsive breakpoints (sm, md, lg, xl, 2xl)
- Improved information hierarchy with better use of colors, icons, and spacing

### Removed
- Grid view toggle buttons from accounts page
- AccountCard component from main accounts display (still used in modals)
- View mode state management and transitions
- Unused imports: ScrollArea, AnimatePresence, Badge, Separator

### Technical Details
- Bundle size reduced by ~14KB after removing grid view components
- TypeScript build errors fixed in AccountTable component
- Removed 'pending' status that didn't exist in AccountStatus type
- Fixed marketplace codes array type assertion

## Previous Updates

### Authentication & Token Management
- Implemented automatic token refresh with 5-minute buffer before expiration
- Added exponential backoff retry logic for token refresh
- Comprehensive audit logging in `auth_audit_log` table
- Rate limiting protection (2 requests per second default)

### Amazon Ads API Integration (v3.0)
- Full OAuth 2.0 flow implementation with required scopes
- Account Management API v1 support with v3.0 response format
- Encrypted token storage using Fernet encryption
- Support for alternateIds with country-specific profile mappings

### Database Schema
- Core tables: users, user_accounts, oauth_tokens
- Supporting tables: oauth_states, auth_audit_log, application_config, rate_limit_buckets
- JSONB metadata storage for flexible account information

### Frontend Architecture
- React with TypeScript and Vite build system
- shadcn/ui component library for consistent design
- Zustand for state management
- Clerk integration for user authentication
- Full responsive design with Tailwind CSS