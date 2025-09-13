"""
OAuth authentication endpoints
"""
from fastapi import APIRouter, Query, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional
from datetime import datetime, timezone
import structlog

from app.config import settings
from app.core.oauth import oauth_client
from app.core.exceptions import (
    OAuthException,
    InvalidStateTokenError,
    TokenExchangeError,
    TokenRefreshError
)
from app.services.token_service import token_service
from app.schemas.auth import (
    LoginResponse,
    CallbackResponse,
    TokenInfo,
    AuthStatus,
    RefreshResponse,
    ErrorResponse
)

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/amazon/login", response_model=LoginResponse)
async def login():
    """
    Initiate OAuth 2.0 authorization flow with Amazon
    
    Generates an authorization URL and state token for CSRF protection.
    Redirect the user to the auth_url to begin authentication.
    """
    try:
        # Check if already authenticated (optional - log warning but allow re-auth)
        existing_token = await token_service.get_active_token()
        if existing_token:
            # Check if token is still valid
            expires_at = datetime.fromisoformat(
                existing_token["expires_at"].replace("Z", "+00:00")
            )
            if expires_at > datetime.now(timezone.utc):
                logger.warning(
                    "Re-authentication requested with active token",
                    expires_at=existing_token["expires_at"]
                )
                # Allow re-authentication but log it
                # This is useful for testing and when users want to refresh their credentials
        
        # Generate authorization URL and state
        auth_url, state_token = oauth_client.generate_authorization_url()
        
        # Store state token
        await token_service.store_state_token(
            state_token,
            settings.amazon_redirect_uri
        )
        
        return LoginResponse(
            auth_url=auth_url,
            state=state_token,
            expires_in=600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate login URL", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "LOGIN_INIT_FAILED",
                "message": "Failed to initialize login",
                "details": {"error": str(e)}
            }}
        )


@router.get("/amazon/callback")
async def callback(
    code: Optional[str] = Query(None, description="Authorization code"),
    state: str = Query(..., description="State token"),
    error: Optional[str] = Query(None, description="Error code"),
    error_description: Optional[str] = Query(None, description="Error description")
):
    """
    Handle OAuth callback from Amazon
    
    Processes the authorization code and exchanges it for access tokens.
    Validates the state token for CSRF protection.
    """
    try:
        # Check for authorization errors
        if error:
            logger.warning("Authorization denied", error=error, description=error_description)
            raise HTTPException(
                status_code=400,
                detail={"error": {
                    "code": "AUTHORIZATION_DENIED",
                    "message": error_description or "Authorization was denied",
                    "details": {"error": error}
                }}
            )
        
        # Validate authorization code
        if not code:
            raise HTTPException(
                status_code=400,
                detail={"error": {
                    "code": "MISSING_AUTH_CODE",
                    "message": "Authorization code is required",
                    "details": {}
                }}
            )
        
        # Validate state token
        is_valid = await token_service.validate_state_token(state)
        if not is_valid:
            raise InvalidStateTokenError(state)
        
        # Exchange code for tokens
        token_data = await oauth_client.exchange_code_for_tokens(code)
        
        # Store encrypted tokens
        stored_token = await token_service.store_tokens(token_data)
        
        # Redirect to frontend callback handler with success
        # The frontend will handle displaying the tokens
        # Remove trailing slash from frontend_url if present
        frontend_base = settings.frontend_url.rstrip('/')
        frontend_callback_url = f"{frontend_base}/callback?success=true&state={state}"
        return RedirectResponse(url=frontend_callback_url, status_code=302)
        
    except OAuthException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": {
                "code": e.code,
                "message": e.message,
                "details": e.details
            }}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Callback processing failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "CALLBACK_FAILED",
                "message": "Failed to process callback",
                "details": {"error": str(e)}
            }}
        )


@router.get("/status", response_model=AuthStatus)
async def get_auth_status():
    """
    Check current authentication status
    
    Returns information about the active token including validity and expiration.
    """
    try:
        token_record = await token_service.get_active_token()
        
        if not token_record:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "NO_ACTIVE_TOKEN",
                    "message": "No active authentication found",
                    "details": {}
                }}
            )
        
        # Check token validity
        expires_at = datetime.fromisoformat(
            token_record["expires_at"].replace("Z", "+00:00")
        )
        is_valid = expires_at > datetime.now(timezone.utc)
        
        return AuthStatus(
            authenticated=True,
            token_valid=is_valid,
            expires_at=expires_at,
            refresh_count=token_record.get("refresh_count", 0),
            last_refresh=token_record.get("last_refresh_at"),
            scope=token_record["scope"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get auth status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "STATUS_CHECK_FAILED",
                "message": "Failed to check authentication status",
                "details": {"error": str(e)}
            }}
        )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    x_admin_key: Optional[str] = Header(None, description="Admin key for manual refresh")
):
    """
    Manually trigger token refresh
    
    Requires admin key for authorization. Refreshes the access token using
    the stored refresh token.
    """
    try:
        # Validate admin key
        if x_admin_key != settings.admin_key:
            raise HTTPException(
                status_code=401,
                detail={"error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or missing admin key",
                    "details": {}
                }}
            )
        
        # Get current tokens
        tokens = await token_service.get_decrypted_tokens()
        
        if not tokens:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "NO_TOKEN_TO_REFRESH",
                    "message": "No active token found to refresh",
                    "details": {}
                }}
            )
        
        # Check if refresh is needed
        expires_at = datetime.fromisoformat(
            tokens["expires_at"].replace("Z", "+00:00")
        )
        time_until_expiry = (expires_at - datetime.now(timezone.utc)).total_seconds()
        
        if time_until_expiry > settings.token_refresh_buffer:
            raise HTTPException(
                status_code=422,
                detail={"error": {
                    "code": "REFRESH_NOT_NEEDED",
                    "message": f"Token still valid for {int(time_until_expiry)} seconds",
                    "details": {"expires_at": tokens["expires_at"]}
                }}
            )
        
        # Refresh the token
        new_token_data = await oauth_client.refresh_access_token(tokens["refresh_token"])
        
        # Update stored tokens
        updated_token = await token_service.update_tokens(tokens["id"], new_token_data)
        
        return RefreshResponse(
            status="success",
            message="Token refreshed successfully",
            new_expiry=datetime.fromisoformat(
                updated_token["expires_at"].replace("Z", "+00:00")
            ),
            refresh_count=updated_token["refresh_count"]
        )
        
    except OAuthException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": {
                "code": e.code,
                "message": e.message,
                "details": e.details
            }}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "REFRESH_FAILED",
                "message": "Failed to refresh token",
                "details": {"error": str(e)}
            }}
        )


@router.delete("/revoke")
async def revoke_tokens(
    x_admin_key: Optional[str] = Header(None, description="Admin key for revocation")
):
    """
    Revoke current tokens and clear authentication
    
    Requires admin key for authorization. Deactivates all active tokens.
    """
    try:
        # Validate admin key
        if x_admin_key != settings.admin_key:
            raise HTTPException(
                status_code=401,
                detail={"error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or missing admin key",
                    "details": {}
                }}
            )
        
        # Revoke tokens
        success = await token_service.revoke_tokens()
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "NO_TOKEN_TO_REVOKE",
                    "message": "No active tokens found to revoke",
                    "details": {}
                }}
            )
        
        return {
            "status": "success",
            "message": "Tokens revoked successfully",
            "revoked_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token revocation failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "REVOKE_FAILED",
                "message": "Failed to revoke tokens",
                "details": {"error": str(e)}
            }}
        )


@router.get("/audit")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=100, description="Number of entries"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    Retrieve authentication audit logs
    
    Returns a paginated list of authentication events for debugging and monitoring.
    """
    try:
        logs = await token_service.get_audit_logs(limit, offset)
        
        # Apply filters if provided
        events = logs["events"]
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        if status:
            events = [e for e in events if e.get("event_status") == status]
        
        return {
            "total": logs["total"],
            "limit": limit,
            "offset": offset,
            "events": events
        }
        
    except Exception as e:
        logger.error("Failed to get audit logs", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "AUDIT_FETCH_FAILED",
                "message": "Failed to retrieve audit logs",
                "details": {"error": str(e)}
            }}
        )