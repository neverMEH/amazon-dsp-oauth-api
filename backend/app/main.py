"""
FastAPI application entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import asyncio
import structlog

from app.config import settings
from app.utils.logger import configure_logging
from app.api.v1 import auth, health
from app.middleware.error_handler import (
    oauth_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.core.exceptions import OAuthException
from app.services.refresh_service import start_refresh_service, stop_refresh_service

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
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    
    # Stop background services
    await stop_refresh_service(refresh_task)


# Create FastAPI application
app = FastAPI(
    title="Amazon DSP OAuth API",
    description="OAuth 2.0 authentication service for Amazon DSP Campaign Insights API",
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
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


@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "service": "Amazon DSP OAuth API",
        "version": settings.api_version,
        "status": "online",
        "docs": "/docs" if settings.environment == "development" else None
    }


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
            }
        }
    }