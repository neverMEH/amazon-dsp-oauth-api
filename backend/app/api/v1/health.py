"""
Health check endpoints
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import structlog

from app.config import settings
from app.db.base import get_supabase_client
from app.schemas.auth import HealthResponse
from app.services.token_service import token_service

logger = structlog.get_logger()

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring
    
    Returns the current health status of the service including
    database connectivity and background service status.
    """
    try:
        services = {}
        
        # Check database connection
        try:
            db = get_supabase_client()
            # Simple query to verify connection
            result = db.table("application_config").select("key").limit(1).execute()
            services["database"] = "connected"
        except Exception as e:
            logger.warning("Database health check failed", error=str(e))
            services["database"] = "disconnected"
        
        # Check token refresh service
        try:
            # Check if there's an active token
            active_token = await token_service.get_active_token()
            if active_token:
                services["token_refresh"] = "running"
                services["last_refresh"] = active_token.get(
                    "last_refresh_at",
                    active_token.get("created_at")
                )
            else:
                services["token_refresh"] = "idle"
                services["last_refresh"] = None
        except Exception as e:
            logger.warning("Token service health check failed", error=str(e))
            services["token_refresh"] = "error"
        
        # Determine overall status
        overall_status = "healthy"
        if services.get("database") == "disconnected":
            overall_status = "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.api_version,
            services=services
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e)
            }
        )