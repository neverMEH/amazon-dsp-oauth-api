# Spec Requirements Document

> Spec: OAuth Foundation & Core Infrastructure
> Created: 2025-09-12
> **Status: ✅ COMPLETED - 2025-09-13**

## Overview

Establish a secure, production-ready OAuth 2.0 authentication system for Amazon DSP Campaign Insights API integration with automated token management, encrypted storage, and a Next.js testing interface using shadcn/ui components. This foundation will enable reliable API access with zero-maintenance token refresh and visual monitoring capabilities, supporting all future Amazon Advertising API integrations.

## User Stories

### Secure Authentication Flow

As an advertising consultant, I want to authenticate with Amazon Advertising APIs using OAuth 2.0, so that I can securely access DSP campaign data without managing credentials manually.

The authentication workflow begins when I click "Connect Amazon Account" which redirects me to Amazon's login page. After granting permissions for the DSP Campaign Insights scope, I'm redirected back to the application where my tokens are encrypted and stored. The system automatically refreshes tokens before expiration, ensuring uninterrupted API access for weeks without any manual intervention. All sensitive credentials are encrypted using Fernet encryption, and the refresh process runs silently in the background using FastAPI's async capabilities.

### Automated Token Management

As a single user of this platform, I want tokens to refresh automatically, so that I never experience authentication failures during report generation.

The system monitors token expiration continuously through a background service. When tokens approach expiration (within 5 minutes), the service automatically initiates a refresh using the stored refresh token. If a refresh fails, the system retries with exponential backoff and logs the issue for debugging. The entire process is transparent, with tokens remaining valid 24/7 without any manual intervention required. This ensures that scheduled reports and API calls never fail due to expired authentication.

### Railway Deployment Configuration

As the platform owner, I want to deploy the authentication service to Railway, so that I have a reliable production environment with proper environment variable management.

The deployment process uses Railway's native Python buildpack with FastAPI support. Environment variables for Amazon credentials, Fernet keys, and Supabase connection strings are securely managed through Railway's dashboard. The service auto-deploys from GitHub commits, includes health check endpoints for monitoring, and supports both development and production environments. Railway handles SSL certificates, custom domains, and provides built-in logging for debugging authentication issues.

### Visual Testing Interface

As a developer, I want a simple UI dashboard to test the OAuth connection and monitor token refresh status, so that I can visually confirm the authentication system is working correctly.

The testing interface built with Next.js and shadcn/ui provides a clean, purple-themed dashboard showing authentication status, token expiration countdown, refresh history, and real-time connection testing. The interface includes a "Connect to Amazon" button using shadcn's Button component, status cards showing token validity with color-coded indicators, an audit log table displaying recent authentication events, and a manual refresh trigger for testing purposes. All components follow the purple color scheme defined in the tech stack and provide real-time updates via polling or websockets.

## Spec Scope

1. **OAuth 2.0 Authorization Flow** - Complete implementation of authorization code exchange with Amazon's OAuth endpoints for DSP Campaign Insights API access
2. **Encrypted Token Storage** - Fernet-encrypted token storage in Supabase with automatic encryption/decryption on all database operations
3. **Automatic Token Refresh Service** - Background FastAPI task that monitors and refreshes tokens before expiration using asyncio
4. **Production FastAPI Architecture** - Modular project structure with separate routers, services, models, and middleware for maintainability
5. **Railway Deployment Pipeline** - Complete deployment configuration with environment variables, health checks, and GitHub auto-deploy
6. **Next.js Testing Dashboard** - Visual interface using shadcn/ui components for OAuth testing, token monitoring, and connection verification
7. **Real-time Status Updates** - Live token status display with countdown timer and automatic UI refresh when tokens are renewed

## Out of Scope

- Multi-user authentication and user management
- Complex reporting features beyond basic testing
- Additional Amazon API scopes beyond DSP Campaign Insights
- Email notifications for authentication events
- Advanced analytics or data visualization
- Rate limiting and API quota management
- Mobile responsive design

## Expected Deliverable

1. ✅ **Working OAuth flow** accessible at `/api/auth/amazon/login` that successfully authenticates with Amazon and stores encrypted tokens
2. ✅ **Automatic token refresh** verified by checking token validity after 1 hour of initial authentication
3. ✅ **Deployed service on Railway** accessible via HTTPS with all environment variables properly configured and health check passing at `/health`
4. ✅ **React dashboard** at `/` showing connection status, token expiration countdown, and "Connect to Amazon" button with shadcn/ui components
5. ✅ **Visual confirmation of token refresh** with real-time UI updates showing new expiration time when tokens are automatically renewed

## Completion Summary

**Date Completed:** September 13, 2025

### Achievements:
- ✅ Full OAuth 2.0 flow with Amazon Advertising API
- ✅ Encrypted token storage in Supabase using Fernet encryption
- ✅ Automatic token refresh service with 5-minute buffer
- ✅ Production deployment on Railway at https://amazon-dsp-oauth-api-production.up.railway.app
- ✅ React frontend with shadcn/ui components for authentication management
- ✅ Real-time token status monitoring with countdown timer
- ✅ ConnectionStatus component showing live token validity
- ✅ Manual refresh capability for testing

### Key Technical Implementations:
- FastAPI backend with modular architecture
- Supabase for encrypted token persistence
- React with TypeScript for frontend
- shadcn/ui for consistent component design
- Automatic token refresh before expiration
- CORS configuration for production deployment
- Health check endpoints for monitoring

### Production URL:
https://amazon-dsp-oauth-api-production.up.railway.app