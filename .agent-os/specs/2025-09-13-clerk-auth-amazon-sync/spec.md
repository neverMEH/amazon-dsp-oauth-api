# Spec Requirements Document

> Spec: Clerk Authentication & Amazon Account Sync
> Created: 2025-09-13

## Overview

Implement Clerk authentication system with Supabase integration to provide secure user authentication and enable Amazon Advertising API account synchronization. This feature will establish user-specific dashboards with multi-account management capabilities for tracking and refreshing OAuth tokens.

## User Stories

### User Authentication Flow

As a new user, I want to register and login through Clerk authentication, so that I can access my personalized dashboard and manage my Amazon advertising accounts securely.

The user arrives at the application and is presented with a Clerk-powered login page. They can either sign up with email/password or use social authentication providers. Once authenticated, they are redirected to their personalized dashboard where they can view their connected Amazon accounts and advertising data. The authentication state persists across sessions using Clerk's secure session management.

### Amazon Account Synchronization

As an authenticated user, I want to connect and sync my Amazon Advertising accounts through the profile dropdown menu, so that I can manage multiple advertising accounts and track their refresh tokens from a single dashboard.

From the dashboard, the user clicks on their profile icon in the top-right header, revealing a dropdown menu. They select "Accounts" which takes them to an account management page. Here they can initiate a new Amazon account sync by clicking "Connect Amazon Account", which triggers the OAuth flow with Amazon Advertising API. Once authorized, the system pulls in all associated advertising accounts and stores the refresh tokens securely. Users can view connection status, last sync time, and manually refresh tokens as needed.

### Multi-Account Management

As a user managing multiple brands, I want to switch between different Amazon advertising accounts seamlessly, so that I can view and manage advertising data for each account separately.

Users with multiple connected Amazon accounts can see all their accounts listed in the accounts page. Each account shows its status, last refresh time, and a quick-access button. Users can set a default account for their dashboard view and easily switch between accounts using a account selector in the main dashboard interface.

## Spec Scope

1. **Clerk Authentication Integration** - Implement Clerk authentication with Supabase database integration for user management and session handling
2. **User Dashboard** - Create a protected dashboard route that displays user-specific data and account information
3. **Profile Dropdown Component** - Build a profile dropdown in the header with user info and navigation to accounts management
4. **Amazon Account Sync** - Implement OAuth flow for connecting Amazon Advertising API accounts and storing refresh tokens
5. **Account Management Interface** - Create an accounts page for viewing, connecting, and managing multiple Amazon advertising accounts

## Out of Scope

- Advanced user permissions and role-based access control
- Team/organization management features
- Billing and subscription management
- Detailed advertising campaign management (beyond account connection)
- Data analytics and reporting features
- Email notifications for token expiration

## Expected Deliverable

1. Working Clerk authentication with login/logout functionality accessible at the application root
2. Protected dashboard route that redirects unauthenticated users to login
3. Functional account synchronization with Amazon Advertising API that successfully stores and refreshes OAuth tokens