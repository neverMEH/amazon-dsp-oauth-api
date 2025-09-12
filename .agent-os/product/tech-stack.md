# Technical Stack

## Core Technologies

- **application_framework:** FastAPI v0.104+
- **database_system:** Supabase (PostgreSQL)
- **javascript_framework:** Next.js v14
- **import_strategy:** node
- **css_framework:** Tailwind CSS v3.4
- **ui_component_library:** shadcn/ui
- **fonts_provider:** Google Fonts
- **icon_library:** Lucide Icons
- **application_hosting:** Railway
- **database_hosting:** Supabase Cloud
- **asset_hosting:** Railway CDN
- **deployment_solution:** Railway CI/CD
- **code_repository_url:** github.com/[your-username]/amazon-ads-reporting

## Backend Stack

### API Framework
- **FastAPI:** High-performance async Python framework for building the OAuth and reporting APIs
- **Pydantic:** Data validation and settings management
- **SQLAlchemy:** ORM for database interactions with Supabase

### Authentication & Security
- **Cryptography (Fernet):** Symmetric encryption for token storage
- **python-jose:** JWT token handling
- **httpx:** Async HTTP client for Amazon API calls
- **python-dotenv:** Environment variable management

### Task Processing
- **Celery:** Distributed task queue for background token refresh
- **Redis:** Message broker for Celery (via Railway)
- **APScheduler:** Lightweight scheduling for periodic tasks

## Frontend Stack

### Framework & UI
- **Next.js 14:** React framework with App Router
- **TypeScript:** Type-safe development
- **shadcn/ui:** Accessible component library
- **Tailwind CSS:** Utility-first styling

### State Management
- **Zustand:** Lightweight state management
- **TanStack Query:** Server state synchronization
- **React Hook Form:** Form handling with validation

### Data Visualization
- **Recharts:** Composable charting library
- **Tremor:** Dashboard components
- **date-fns:** Date manipulation utilities

## Design System

### Color Scheme (Purple Theme)
```css
--purple-50: #faf5ff;
--purple-100: #f3e8ff;
--purple-200: #e9d5ff;
--purple-300: #d8b4fe;
--purple-400: #c084fc;
--purple-500: #a855f7;
--purple-600: #9333ea;
--purple-700: #7e22ce;
--purple-800: #6b21a8;
--purple-900: #581c87;
--purple-950: #3b0764;
```

## Infrastructure

### Deployment Platform
- **Railway:** Container orchestration and deployment
- **Environment:** Production, Staging, Development
- **CI/CD:** GitHub Actions + Railway Auto-deploy

### Database
- **Supabase:** PostgreSQL with real-time subscriptions
- **Row Level Security:** Multi-tenant data isolation
- **Database Migrations:** Alembic for schema versioning

### Monitoring & Logging
- **Sentry:** Error tracking and performance monitoring
- **LogDNA:** Centralized logging (via Railway)
- **Prometheus:** Metrics collection
- **Grafana:** Metrics visualization

## External APIs

### Amazon Advertising APIs
- **OAuth 2.0 Endpoint:** `https://api.amazon.com/auth/o2/token`
- **DSP Campaign Insights API:** Campaign performance metrics
- **AMC Administration API:** Marketing Cloud instance management
- **AMC Reporting API:** Custom query execution and results

### Supporting Services
- **Keepa API:** Historical pricing data (optional)
- **AWS S3:** Report storage and archival
- **SendGrid:** Email notifications for scheduled reports

## Development Tools

### Code Quality
- **Black:** Python code formatter
- **ESLint:** JavaScript/TypeScript linting
- **Prettier:** Code formatting
- **Husky:** Git hooks for pre-commit checks

### Testing
- **pytest:** Python unit and integration testing
- **Jest:** JavaScript/TypeScript testing
- **Playwright:** E2E testing
- **Coverage.py:** Code coverage reporting

### Documentation
- **MkDocs:** Technical documentation
- **OpenAPI/Swagger:** API documentation
- **Storybook:** Component documentation