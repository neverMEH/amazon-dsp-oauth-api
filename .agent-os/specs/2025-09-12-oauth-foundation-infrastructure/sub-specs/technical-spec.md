# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-12-oauth-foundation-infrastructure/spec.md

## Technical Requirements

### Project Structure
```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Environment configuration
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py        # OAuth endpoints router
│   │   │   │   └── health.py      # Health check endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py        # Fernet encryption utilities
│   │   │   ├── oauth.py           # Amazon OAuth client
│   │   │   └── exceptions.py      # Custom exception classes
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Supabase connection manager
│   │   │   └── models.py          # SQLAlchemy models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # Pydantic models for auth
│   │   │   └── token.py           # Token-related schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── token_service.py   # Token management logic
│   │   │   └── refresh_service.py # Background refresh service
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── error_handler.py   # Global error handling
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── logger.py           # Logging configuration
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              # Root layout with purple theme
│   │   ├── page.tsx                # Main dashboard page
│   │   └── globals.css             # Global styles with CSS variables
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── table.tsx
│   │   │   └── alert.tsx
│   │   ├── auth/
│   │   │   ├── connect-button.tsx  # Amazon connect button
│   │   │   └── status-card.tsx     # Token status display
│   │   ├── dashboard/
│   │   │   ├── token-timer.tsx     # Countdown timer component
│   │   │   ├── audit-log.tsx       # Audit events table
│   │   │   └── refresh-button.tsx  # Manual refresh trigger
│   │   └── providers/
│   │       └── theme-provider.tsx  # Purple theme provider
│   ├── lib/
│   │   ├── api.ts                  # API client functions
│   │   ├── utils.ts                # Utility functions
│   │   └── hooks/
│   │       ├── use-auth-status.ts  # Auth status polling hook
│   │       └── use-countdown.ts    # Countdown timer hook
│   ├── package.json
│   ├── tailwind.config.ts          # Tailwind with purple theme
│   ├── components.json             # shadcn/ui configuration
│   └── next.config.js
└── docker-compose.yml               # Local development setup
```

### Authentication Flow Implementation
- **Authorization URL Generation**: Build Amazon OAuth URL with required parameters including DSP Campaign Insights scope (`advertising::campaign_management`)
- **CSRF Protection**: Generate and validate state tokens using `secrets.token_urlsafe(32)`
- **Authorization Code Exchange**: POST to `https://api.amazon.com/auth/o2/token` with proper error handling
- **Token Response Handling**: Parse and validate token response, calculate expiration timestamp

### Encryption Requirements
- **Fernet Key Generation**: Use `Fernet.generate_key()` for production key, store in environment variable
- **Token Encryption**: Encrypt both access and refresh tokens before database storage
- **Decryption on Retrieval**: Automatic decryption when fetching from database
- **Key Rotation Strategy**: Support for key rotation without token loss (using MultiFernet)

### Background Service Architecture
- **AsyncIO Task**: Use `asyncio.create_task()` for non-blocking background execution
- **Refresh Timing**: Check tokens every 60 seconds, refresh if expiring within 5 minutes
- **Error Recovery**: Exponential backoff with max 5 retries on refresh failure
- **Logging**: Detailed logging of all refresh attempts and outcomes
- **Graceful Shutdown**: Proper task cancellation on application shutdown

### Railway Deployment Configuration
- **Procfile**: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Python Version**: Specify Python 3.11+ in `runtime.txt`
- **Environment Variables**: Configure via Railway dashboard (never commit to repo)
- **Health Checks**: Implement `/health` endpoint returning service status
- **Auto-deploy**: Configure GitHub integration for automatic deployments

### Error Handling Strategy
- **Amazon API Errors**: Map specific error codes (401, 403, 429) to custom exceptions
- **Rate Limiting**: Implement exponential backoff for 429 responses
- **Token Expiry**: Graceful handling with automatic retry after refresh
- **Network Failures**: Timeout configuration with retry logic
- **Logging**: Structured logging with correlation IDs for debugging

### Performance Criteria
- **Token Refresh Latency**: < 500ms for refresh operation
- **API Response Time**: < 200ms for auth endpoints (excluding Amazon redirects)
- **Background Task CPU**: < 1% CPU usage for refresh service
- **Memory Usage**: < 100MB RAM for base service
- **Concurrent Requests**: Support 100+ concurrent OAuth flows

## External Dependencies

### Core Dependencies
- **FastAPI** (0.104+) - High-performance async web framework
  - **Justification:** Native async support, automatic OpenAPI documentation, production-ready
- **uvicorn** (0.24+) - ASGI server for FastAPI
  - **Justification:** Production-grade ASGI server with excellent FastAPI integration
- **httpx** (0.25+) - Async HTTP client for Amazon API calls
  - **Justification:** Modern async/await support, better than requests for async operations
- **cryptography** (41.0+) - Fernet encryption implementation
  - **Justification:** Industry-standard encryption library, required for token security

### Database Dependencies
- **supabase** (2.0+) - Supabase Python client
  - **Justification:** Official client for Supabase integration, handles connection pooling
- **SQLAlchemy** (2.0+) - SQL toolkit and ORM
  - **Justification:** Type-safe database operations, migration support
- **asyncpg** (0.29+) - PostgreSQL async driver
  - **Justification:** High-performance async PostgreSQL driver for Supabase

### Utility Dependencies
- **pydantic** (2.4+) - Data validation using Python type annotations
  - **Justification:** Built into FastAPI, provides automatic validation and serialization
- **python-dotenv** (1.0+) - Environment variable management
  - **Justification:** Secure configuration management for local development
- **python-jose[cryptography]** (3.3+) - JWT token handling
  - **Justification:** Required for state token generation and validation
- **structlog** (23.2+) - Structured logging
  - **Justification:** Better debugging with structured logs, Railway-compatible

### Development Dependencies
- **pytest** (7.4+) - Testing framework
  - **Justification:** Industry standard for Python testing
- **pytest-asyncio** (0.21+) - Async test support
  - **Justification:** Required for testing async FastAPI endpoints
- **black** (23.10+) - Code formatter
  - **Justification:** Consistent code formatting
- **mypy** (1.6+) - Static type checker
  - **Justification:** Catch type errors before runtime

## Frontend Dependencies

### Core Framework
- **Next.js** (14.0+) - React framework with App Router
  - **Justification:** Server-side rendering, API routes, excellent DX
- **React** (18.2+) - UI library
  - **Justification:** Component-based architecture, vast ecosystem
- **TypeScript** (5.2+) - Type-safe JavaScript
  - **Justification:** Better code quality, IDE support, fewer runtime errors

### UI Components & Styling
- **@shadcn/ui** - Accessible component library
  - **Justification:** Beautiful, customizable, built on Radix UI primitives
- **@radix-ui/react-*** - Headless UI components
  - **Justification:** Accessibility-first, unstyled primitives for shadcn/ui
- **tailwindcss** (3.4+) - Utility-first CSS framework
  - **Justification:** Rapid development, consistent styling, tree-shaking
- **tailwind-merge** - Merge Tailwind classes
  - **Justification:** Proper class merging for dynamic styles
- **class-variance-authority** - Variant management
  - **Justification:** Type-safe component variants for shadcn/ui
- **clsx** - Class name utility
  - **Justification:** Conditional class names

### Data Fetching & State
- **@tanstack/react-query** (5.0+) - Server state management
  - **Justification:** Caching, refetching, real-time updates
- **axios** (1.6+) - HTTP client
  - **Justification:** Better error handling, interceptors, wide browser support
- **zustand** (4.4+) - Client state management
  - **Justification:** Simple, lightweight alternative to Redux

### UI Features
- **date-fns** (2.30+) - Date utilities
  - **Justification:** Lightweight date manipulation for countdown timer
- **react-countdown** (2.3+) - Countdown component
  - **Justification:** Flexible countdown timer for token expiration
- **sonner** (1.2+) - Toast notifications
  - **Justification:** Beautiful, accessible notifications
- **lucide-react** (0.290+) - Icon library
  - **Justification:** Consistent icons, tree-shakeable

### Development Tools
- **@types/react** - React type definitions
  - **Justification:** TypeScript support for React
- **@types/node** - Node.js type definitions
  - **Justification:** TypeScript support for Node.js APIs
- **eslint** (8.50+) - Linting
  - **Justification:** Code quality enforcement
- **prettier** (3.0+) - Code formatting
  - **Justification:** Consistent code style
- **postcss** - CSS processing
  - **Justification:** Required for Tailwind CSS