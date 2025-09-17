"""
FastAPI application entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
import structlog
from pathlib import Path

from app.config import settings
from app.utils.logger import configure_logging
from app.api.v1 import auth, health, users, webhooks, accounts, debug, test_endpoints
from app.api.v1 import settings as settings_router
from app.middleware.error_handler import (
    oauth_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.core.exceptions import OAuthException
from app.services.refresh_service import start_refresh_service, stop_refresh_service
from app.services.token_refresh_scheduler import get_token_refresh_scheduler

# Configure logging
logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    # Startup
    logger.info("Starting application", version=settings.api_version)

    # Start background token refresh service
    refresh_task = await start_refresh_service()

    # Start token refresh scheduler
    try:
        token_scheduler = get_token_refresh_scheduler()
        await token_scheduler.start()
        logger.info("Token refresh scheduler started")
    except Exception as e:
        logger.error(f"Failed to start token refresh scheduler: {e}")

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Stop token refresh scheduler
    try:
        token_scheduler = get_token_refresh_scheduler()
        await token_scheduler.stop()
        logger.info("Token refresh scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping token refresh scheduler: {e}")

    # Stop background services
    await stop_refresh_service(refresh_task)


# Create FastAPI application
app = FastAPI(
    title="neverMEH API",
    description="OAuth 2.0 authentication service for Amazon Advertising",
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# Configure CORS
cors_origins = [
    settings.frontend_url,
    "https://amazon-dsp-oauth-api-production.up.railway.app",
    "http://localhost:3000",
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(OAuthException, oauth_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(accounts.router, prefix="/api/v1", tags=["accounts"])
app.include_router(settings_router.router, prefix="/api/v1", tags=["settings"])
app.include_router(debug.router, prefix="/api/v1", tags=["debug"])
app.include_router(test_endpoints.router, prefix="/api/v1", tags=["test"])

# API endpoints
@app.get("/api")
async def api_info():
    """
    API information endpoint
    """
    return {
        "version": "v1",
        "endpoints": {
            "health": "/api/v1/health",
            "auth": {
                "login": "/api/v1/auth/amazon/login",
                "callback": "/api/v1/auth/amazon/callback",
                "status": "/api/v1/auth/status",
                "refresh": "/api/v1/auth/refresh",
                "revoke": "/api/v1/auth/revoke",
                "audit": "/api/v1/auth/audit"
            },
            "users": {
                "profile": "/api/v1/users/me",
                "accounts": "/api/v1/users/me/accounts",
                "session": "/api/v1/users/session"
            },
            "webhooks": {
                "clerk": "/api/v1/webhooks/clerk"
            },
            "accounts": {
                "list": "/api/v1/accounts",
                "amazon_ads_accounts": "/api/v1/accounts/amazon-ads-accounts",
                "amazon_profiles": "/api/v1/accounts/amazon-profiles",
                "details": "/api/v1/accounts/{account_id}",
                "disconnect": "/api/v1/accounts/{account_id}/disconnect",
                "health": "/api/v1/accounts/health",
                "reauthorize": "/api/v1/accounts/{account_id}/reauthorize",
                "batch": "/api/v1/accounts/batch"
            },
            "test": {
                "health": "/api/v1/test/health",
                "tokens": "/api/v1/test/tokens/status",
                "profiles": "/api/v1/test/amazon/profiles",
                "accounts": "/api/v1/test/amazon/accounts",
                "dsp_advertisers": "/api/v1/test/amazon/dsp-advertisers",
                "dsp_seats": "/api/v1/test/amazon/dsp-seats/{advertiser_id}",
                "database": "/api/v1/test/database/accounts",
                "sync": "/api/v1/test/amazon/sync-test",
                "note": "All test endpoints require X-Admin-Key header"
            }
        }
    }

# Check if frontend build exists and mount it
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount static files for assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    # Serve index.html for all non-API routes (MUST be last)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """
        Serve frontend for all non-API routes
        """
        # Skip API routes - this shouldn't be reached due to route ordering
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Check if requesting a static file
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        # Otherwise serve index.html for client-side routing
        return FileResponse(str(frontend_dist / "index.html"))
    
    @app.get("/")
    async def root():
        """
        Serve frontend index
        """
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        """
        Root endpoint (API-only mode)
        """
        return {
            "service": "Amazon DSP OAuth API",
            "version": settings.api_version,
            "status": "online",
            "docs": "/docs" if settings.environment == "development" else None
        }

