"""
OAuth authentication endpoints
"""
from fastapi import APIRouter, Query, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional, Dict, Any
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
from app.services.account_service import account_service
from app.services.amazon_oauth_service import amazon_oauth_service
from app.services.user_service import UserService
from app.services.dsp_amc_service import DSPAMCService
from app.middleware.clerk_auth import RequireAuth, OptionalAuth, get_user_context
from app.schemas.auth import (
    LoginResponse,
    CallbackResponse,
    TokenInfo,
    AuthStatus,
    RefreshResponse,
    ErrorResponse,
    AmazonTokenResponse,
    AmazonAccountInfo,
    AmazonConnectionRequest,
    AmazonConnectionStatus,
    AmazonDisconnectionRequest
)

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize services
user_service = UserService()
dsp_amc_service = DSPAMCService()


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
    error_description: Optional[str] = Query(None, description="Error description"),
    current_user: Optional[Dict[str, Any]] = Depends(OptionalAuth)
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

        # Fetch Amazon account data using the new access token
        try:
            access_token = token_data.get("access_token")
            if access_token:
                logger.info("Fetching Amazon account data after OAuth callback")

                # Fetch all types of accounts (advertising, DSP, AMC)
                account_data = await dsp_amc_service.list_all_account_types(
                    access_token=access_token,
                    include_regular=True,
                    include_dsp=True,
                    include_amc=True
                )

                logger.info("Successfully fetched Amazon accounts",
                          advertising_count=len(account_data.get("advertising_accounts", [])),
                          dsp_count=len(account_data.get("dsp_advertisers", [])),
                          amc_count=len(account_data.get("amc_instances", [])))

                # Handle user context if available
                user_context = None
                clerk_user_id = None

                if current_user:
                    try:
                        user_context = get_user_context(current_user)
                        clerk_user_id = user_context.get("clerk_user_id")
                        logger.info("OAuth callback with authenticated user",
                                  clerk_user_id=clerk_user_id[:8] + "..." if clerk_user_id else None)
                    except Exception as e:
                        logger.warning("Failed to get user context", error=str(e))

                # TODO: Create user and account records with proper user association
                # If clerk_user_id is available, associate the tokens and accounts with that user
                # If not, we may need to handle this case differently (e.g., store temporarily)

                if clerk_user_id:
                    logger.info("User authenticated - ready to associate Amazon accounts with user")
                    # TODO: Implementation needed:
                    # 1. Update stored_token to include user_id
                    # 2. Create account records for each fetched account
                    # 3. Associate accounts with the user
                else:
                    logger.warning("No user context available - Amazon accounts fetched but not associated")

        except Exception as e:
            # Don't fail the OAuth flow if account fetching fails
            # Just log the error and continue
            logger.warning("Failed to fetch Amazon account data after OAuth", error=str(e))

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


@router.get("/tokens")
async def get_tokens(
    x_admin_key: Optional[str] = Header(None, description="Admin key for token retrieval")
):
    """
    Retrieve the actual access and refresh tokens
    
    Requires admin key for authorization. Returns the decrypted tokens
    for use in API calls.
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
        
        # Get decrypted tokens
        tokens = await token_service.get_decrypted_tokens()
        
        if not tokens:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "NO_TOKENS_FOUND",
                    "message": "Authentication succeeded but no tokens found. Please complete the OAuth flow first.",
                    "details": {}
                }}
            )
        
        # Check if token is still valid
        expires_at = datetime.fromisoformat(
            tokens["expires_at"].replace("Z", "+00:00")
        )
        is_valid = expires_at > datetime.now(timezone.utc)
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_at": tokens["expires_at"],
            "token_valid": is_valid,
            "refresh_count": tokens["refresh_count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve tokens", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "TOKEN_RETRIEVAL_FAILED",
                "message": "Failed to retrieve tokens",
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


@router.get("/profiles")
async def list_profiles(
    x_admin_key: Optional[str] = Header(None, description="Admin key for account access")
):
    """
    List Amazon Advertising profiles (accounts)
    
    Requires admin key and valid authentication. Returns available advertising
    profiles that can be used for API operations.
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
        
        # Get access token
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "NO_TOKENS_FOUND",
                    "message": "No active authentication found. Complete OAuth flow first.",
                    "details": {}
                }}
            )
        
        # Check token validity and refresh if needed
        expires_at = datetime.fromisoformat(
            tokens["expires_at"].replace("Z", "+00:00")
        )
        if expires_at <= datetime.now(timezone.utc):
            # Token expired, try to refresh
            try:
                new_token_data = await oauth_client.refresh_access_token(tokens["refresh_token"])
                tokens = await token_service.update_tokens(tokens["id"], new_token_data)
            except Exception as refresh_error:
                logger.error("Failed to refresh expired token", error=str(refresh_error))
                raise HTTPException(
                    status_code=401,
                    detail={"error": {
                        "code": "TOKEN_EXPIRED",
                        "message": "Token expired and refresh failed. Please re-authenticate.",
                        "details": {"refresh_error": str(refresh_error)}
                    }}
                )
        
        # List profiles
        profiles = await account_service.list_profiles(tokens["access_token"])
        
        return {
            "profiles": profiles,
            "profile_count": len(profiles),
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list profiles", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "PROFILES_FETCH_FAILED",
                "message": "Failed to retrieve advertising profiles",
                "details": {"error": str(e)}
            }}
        )


@router.get("/profiles/{profile_id}")
async def get_profile_details(
    profile_id: str,
    x_admin_key: Optional[str] = Header(None, description="Admin key for account access")
):
    """
    Get specific profile details
    
    Requires admin key and valid authentication. Returns detailed information
    about a specific advertising profile.
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
        
        # Get access token
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "NO_TOKENS_FOUND",
                    "message": "No active authentication found. Complete OAuth flow first.",
                    "details": {}
                }}
            )
        
        # Get profile details
        profile = await account_service.get_profile(tokens["access_token"], profile_id)
        
        return {
            "profile": profile,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get profile details", profile_id=profile_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "PROFILE_FETCH_FAILED",
                "message": f"Failed to retrieve profile {profile_id}",
                "details": {"error": str(e)}
            }}
        )


@router.get("/profiles/{profile_id}/dsp-advertisers")
async def list_dsp_advertisers(
    profile_id: str,
    x_admin_key: Optional[str] = Header(None, description="Admin key for account access")
):
    """
    List DSP advertisers under a profile

    Requires admin key and valid authentication. Returns DSP advertisers available
    for campaign management under the specified profile.
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

        # Get access token
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "NO_TOKENS_FOUND",
                    "message": "No active authentication found. Complete OAuth flow first.",
                    "details": {}
                }}
            )

        # Import DSP service
        from app.services.dsp_amc_service import dsp_amc_service

        # List DSP advertisers
        result = await dsp_amc_service.list_dsp_advertisers(
            access_token=tokens["access_token"],
            profile_id=profile_id
        )

        advertisers = result.get("response", [])

        return {
            "dsp_advertisers": advertisers,
            "advertiser_count": len(advertisers),
            "profile_id": profile_id,
            "total_results": result.get("totalResults", len(advertisers)),
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list DSP accounts", profile_id=profile_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "DSP_ACCOUNTS_FETCH_FAILED",
                "message": f"Failed to retrieve DSP accounts for profile {profile_id}",
                "details": {"error": str(e)}
            }}
        )


# Amazon Account Connection Endpoints

@router.get("/amazon/connect/{user_id}")
async def initiate_amazon_connection(
    user_id: str,
    x_admin_key: Optional[str] = Header(None, description="Admin key for authorization")
):
    """
    Initiate Amazon account connection for a specific user
    
    Creates an OAuth authorization URL for the user to connect their Amazon account.
    Requires admin key for authorization.
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
        
        # Generate Amazon OAuth URL with user-specific state
        import secrets
        state = f"{user_id}_{secrets.token_urlsafe(24)}"
        auth_url, state_token = amazon_oauth_service.generate_oauth_url(state=state)
        
        # Store state for validation (extend token_service for user-specific states)
        await token_service.store_state_token(state_token, settings.amazon_redirect_uri)
        
        return {
            "auth_url": auth_url,
            "state": state_token,
            "user_id": user_id,
            "expires_in": 600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to initiate Amazon connection", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "CONNECTION_INIT_FAILED",
                "message": "Failed to initiate Amazon account connection",
                "details": {"error": str(e)}
            }}
        )


@router.post("/amazon/connect/callback")
async def amazon_connection_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State token"), 
    error: Optional[str] = Query(None, description="Error code"),
    error_description: Optional[str] = Query(None, description="Error description")
):
    """
    Handle Amazon OAuth callback for user account connection
    
    Processes the authorization code and stores tokens for the specific user.
    """
    try:
        # Check for authorization errors
        if error:
            logger.warning("Amazon authorization denied", error=error, description=error_description)
            raise HTTPException(
                status_code=400,
                detail={"error": {
                    "code": "AMAZON_AUTHORIZATION_DENIED",
                    "message": error_description or "Amazon authorization was denied",
                    "details": {"error": error}
                }}
            )
        
        # Extract user_id from state
        if not state or "_" not in state:
            raise HTTPException(
                status_code=400,
                detail={"error": {
                    "code": "INVALID_STATE_FORMAT",
                    "message": "State token format is invalid",
                    "details": {}
                }}
            )
        
        user_id = state.split("_")[0]
        
        # Validate state token
        is_valid = await token_service.validate_state_token(state)
        if not is_valid:
            raise InvalidStateTokenError(state)
        
        # Exchange code for tokens
        token_response = await amazon_oauth_service.exchange_code_for_tokens(code, state)
        
        # Get user's Amazon profiles
        profiles = await amazon_oauth_service.get_user_profiles(token_response.access_token)
        
        if not profiles:
            raise HTTPException(
                status_code=400,
                detail={"error": {
                    "code": "NO_PROFILES_FOUND",
                    "message": "No Amazon advertising profiles found for this account",
                    "details": {}
                }}
            )
        
        # Store tokens for each profile (user can have multiple Amazon accounts)
        stored_profiles = []
        for profile in profiles:
            # Store tokens in user_accounts table
            await token_service.store_amazon_tokens(
                user_id=user_id,
                profile_id=profile.profile_id,
                tokens=token_response.dict()
            )
            stored_profiles.append({
                "profile_id": profile.profile_id,
                "country_code": profile.country_code,
                "currency_code": profile.currency_code,
                "account_name": profile.account_info.get("name", "Unknown")
            })
        
        # Redirect to frontend with success
        frontend_base = settings.frontend_url.rstrip('/')
        callback_url = f"{frontend_base}/amazon/callback?success=true&user_id={user_id}&profiles={len(stored_profiles)}"
        return RedirectResponse(url=callback_url, status_code=302)
        
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
        logger.error("Amazon callback processing failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "AMAZON_CALLBACK_FAILED",
                "message": "Failed to process Amazon OAuth callback",
                "details": {"error": str(e)}
            }}
        )


@router.get("/amazon/status/{user_id}")
async def get_amazon_connection_status(
    user_id: str,
    x_admin_key: Optional[str] = Header(None, description="Admin key for authorization")
):
    """
    Get Amazon account connection status for a user
    
    Returns connection status and profile information for all connected Amazon accounts.
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
        
        # Get user's connected Amazon accounts
        amazon_accounts = await token_service.get_user_amazon_accounts(user_id)
        
        connection_statuses = []
        for account in amazon_accounts:
            status = await token_service.get_connection_status(user_id, account["profile_id"])
            connection_statuses.append(status)
        
        return {
            "user_id": user_id,
            "total_connections": len(connection_statuses),
            "connections": connection_statuses,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get Amazon connection status", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "STATUS_CHECK_FAILED",
                "message": "Failed to check Amazon connection status",
                "details": {"error": str(e)}
            }}
        )


@router.delete("/amazon/disconnect/{user_id}/{profile_id}")
async def disconnect_amazon_account(
    user_id: str,
    profile_id: int,
    x_admin_key: Optional[str] = Header(None, description="Admin key for authorization")
):
    """
    Disconnect a specific Amazon account for a user
    
    Removes stored tokens and connection for the specified profile.
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
        
        # Disconnect the account
        success = await token_service.disconnect_amazon_account(user_id, profile_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={"error": {
                    "code": "CONNECTION_NOT_FOUND",
                    "message": f"No Amazon connection found for user {user_id} and profile {profile_id}",
                    "details": {}
                }}
            )
        
        return {
            "status": "success",
            "message": f"Amazon account {profile_id} disconnected successfully",
            "user_id": user_id,
            "profile_id": profile_id,
            "disconnected_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect Amazon account", user_id=user_id, profile_id=profile_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "DISCONNECT_FAILED",
                "message": "Failed to disconnect Amazon account",
                "details": {"error": str(e)}
            }}
        )