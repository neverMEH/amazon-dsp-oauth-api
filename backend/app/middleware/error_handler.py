"""
Global error handling middleware
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog
import traceback
from datetime import datetime

from app.core.exceptions import OAuthException

logger = structlog.get_logger()


async def oauth_exception_handler(request: Request, exc: OAuthException):
    """
    Handle custom OAuth exceptions
    """
    logger.error(
        "OAuth error",
        code=exc.code,
        message=exc.message,
        details=exc.details,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle FastAPI HTTP exceptions
    """
    logger.warning(
        "HTTP error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    
    # If detail is already structured, use it as-is
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, structure it
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors
    """
    logger.warning(
        "Validation error",
        errors=exc.errors(),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {
                    "errors": exc.errors()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle uncaught exceptions
    """
    error_id = datetime.utcnow().timestamp()
    
    logger.error(
        "Unhandled exception",
        error_id=error_id,
        error=str(exc),
        traceback=traceback.format_exc(),
        path=request.url.path
    )
    
    # Don't expose internal errors in production
    message = "An internal error occurred"
    if hasattr(exc, "__class__"):
        error_type = exc.__class__.__name__
    else:
        error_type = "UnknownError"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": message,
                "details": {
                    "error_id": error_id,
                    "type": error_type
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )