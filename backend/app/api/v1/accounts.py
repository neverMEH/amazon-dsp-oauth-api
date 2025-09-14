"""
Amazon Advertising Account Management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import structlog
from pydantic import BaseModel, Field
from uuid import uuid4

from app.middleware.clerk_auth import RequireAuth, get_user_context
from app.services.account_service import account_service
from app.services.amazon_oauth_service import amazon_oauth_service
from app.services.token_service import token_service
from app.db.base import get_supabase_client
from app.core.exceptions import TokenRefreshError, RateLimitError
from app.models.amazon_account import AmazonAccount

logger = structlog.get_logger()

router = APIRouter(prefix="/accounts", tags=["accounts"])


# ============================================================================
# SCHEMAS
# ============================================================================

class AmazonProfileResponse(BaseModel):
    """Amazon Advertising Profile/Account from API"""
    profile_id: int = Field(..., description="Amazon Profile ID")
    country_code: str = Field(..., description="Country code (e.g., US)")
    currency_code: str = Field(..., description="Currency code (e.g., USD)")
    timezone: str = Field(..., description="Timezone")
    marketplace_id: str = Field(..., description="Amazon Marketplace ID")
    account_info: Dict[str, Any] = Field(default={}, description="Account metadata")
    account_type: str = Field(..., description="Account type (seller, vendor, agency)")
    account_name: str = Field(..., description="Account name")
    account_id: str = Field(..., description="Amazon Account ID")
    valid_payment_method: bool = Field(default=True, description="Valid payment method on file")
    
class AccountHealthStatus(BaseModel):
    """Health status for an account"""
    account_id: str = Field(..., description="Internal account ID")
    amazon_account_id: str = Field(..., description="Amazon account ID")
    account_name: str = Field(..., description="Account name")
    status: str = Field(..., description="Health status (healthy, degraded, error)")
    is_active: bool = Field(..., description="Whether account is active")
    token_valid: bool = Field(..., description="Whether token is valid")
    last_synced_at: Optional[datetime] = Field(None, description="Last successful sync")
    error_message: Optional[str] = Field(None, description="Error message if any")
    requires_reauth: bool = Field(default=False, description="Needs re-authorization")

class AccountListResponse(BaseModel):
    """List of connected accounts"""
    accounts: List[Dict[str, Any]] = Field(..., description="List of accounts")
    total: int = Field(..., description="Total number of accounts")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")

class AccountDetailResponse(BaseModel):
    """Detailed account information"""
    id: str = Field(..., description="Internal account ID")
    user_id: str = Field(..., description="User ID")
    account_name: str = Field(..., description="Account display name")
    amazon_account_id: str = Field(..., description="Amazon account ID")
    marketplace_id: Optional[str] = Field(None, description="Marketplace ID")
    marketplace_name: str = Field(..., description="Marketplace name")
    account_type: str = Field(..., description="Account type")
    is_default: bool = Field(..., description="Default account flag")
    status: str = Field(..., description="Account status")
    connected_at: datetime = Field(..., description="Connection timestamp")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    profiles: Optional[List[Dict]] = Field(None, description="Associated profiles")

class DisconnectResponse(BaseModel):
    """Account disconnection response"""
    status: str = Field(default="success", description="Operation status")
    message: str = Field(..., description="Status message")
    account_id: str = Field(..., description="Disconnected account ID")

class ReauthorizeRequest(BaseModel):
    """Re-authorization request"""
    force_refresh: bool = Field(default=False, description="Force token refresh")

class ReauthorizeResponse(BaseModel):
    """Re-authorization response"""
    status: str = Field(default="success", description="Operation status")
    message: str = Field(..., description="Status message")
    token_refreshed: bool = Field(..., description="Whether token was refreshed")
    expires_at: datetime = Field(..., description="New token expiration")

class BatchOperation(BaseModel):
    """Batch operation definition"""
    operation: str = Field(..., description="Operation type (sync, disconnect, update)")
    account_ids: List[str] = Field(..., description="Account IDs to operate on")
    params: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")

class BatchResponse(BaseModel):
    """Batch operation response"""
    status: str = Field(default="completed", description="Overall status")
    total: int = Field(..., description="Total operations")
    successful: int = Field(..., description="Successful operations")
    failed: int = Field(..., description="Failed operations")
    results: List[Dict[str, Any]] = Field(..., description="Individual results")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_user_token(user_id: str, supabase) -> Optional[Dict]:
    """Get user's Amazon access token"""
    try:
        result = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).execute()
        if result.data and len(result.data) > 0:
            token_data = result.data[0]
            # Decrypt the token
            decrypted_token = token_service.decrypt_token(token_data["encrypted_access_token"])
            return {
                "access_token": decrypted_token,
                "refresh_token": token_service.decrypt_token(token_data["encrypted_refresh_token"]),
                "expires_at": token_data["expires_at"]
            }
        return None
    except Exception as e:
        logger.error("Failed to get user token", user_id=user_id, error=str(e))
        return None

async def refresh_token_if_needed(user_id: str, token_data: Dict, supabase) -> Dict:
    """Refresh token if expired or about to expire"""
    from datetime import datetime, timedelta
    
    expires_at = datetime.fromisoformat(token_data["expires_at"].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    # Refresh if expired or expiring in next 5 minutes
    if expires_at <= now + timedelta(minutes=5):
        try:
            # Refresh the token
            new_tokens = await amazon_oauth_service.refresh_access_token(
                token_data["refresh_token"]
            )
            
            # Update in database
            new_expires = now + timedelta(seconds=new_tokens.expires_in)
            
            update_data = {
                "encrypted_access_token": token_service.encrypt_token(new_tokens.access_token),
                "encrypted_refresh_token": token_service.encrypt_token(new_tokens.refresh_token),
                "expires_at": new_expires.isoformat(),
                "refresh_count": supabase.table("oauth_tokens").select("refresh_count").eq("user_id", user_id).execute().data[0]["refresh_count"] + 1,
                "last_refresh": now.isoformat()
            }
            
            supabase.table("oauth_tokens").update(update_data).eq("user_id", user_id).execute()
            
            return {
                "access_token": new_tokens.access_token,
                "refresh_token": new_tokens.refresh_token,
                "expires_at": new_expires.isoformat()
            }
        except Exception as e:
            logger.error("Failed to refresh token", user_id=user_id, error=str(e))
            raise
    
    return token_data


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/amazon-ads-accounts")
async def list_amazon_ads_accounts(
    current_user: Dict = Depends(RequireAuth),
    next_token: Optional[str] = Query(None, description="Pagination token for next page"),
    max_results: int = Query(100, ge=1, le=100, description="Maximum results per page"),
    supabase = Depends(get_supabase_client)
):
    """
    List Amazon Advertising accounts using the Account Management API v3.0

    **Endpoint Details:**
    - URL: POST https://advertising-api.amazon.com/adsAccounts/list
    - Method: POST
    - Version: v3.0
    - Content-Type: application/vnd.listaccountsresource.v1+json
    - Accept: application/vnd.listaccountsresource.v1+json
    - Required Headers: Authorization, Amazon-Advertising-API-ClientId

    **Amazon API Documentation:**
    https://advertising.amazon.com/API/docs/en-us/account-management#tag/Account/operation/ListAdsAccounts

    **Required Permissions:**
    - User must have valid Amazon OAuth tokens
    - Scopes: advertising::account_management

    **Response Structure (API v3.0):**
    Returns adsAccounts array with:
    - adsAccountId: Global advertising account ID
    - accountName: Account display name
    - status: CREATED, DISABLED, PARTIALLY_CREATED, or PENDING
    - alternateIds: Array of {countryCode, entityId, profileId}
    - countryCodes: Array of supported country codes
    - errors: Object mapping country codes to error arrays

    **Rate Limits:**
    - Default: 2 requests per second
    - Burst: 10 requests

    **Common Issues:**
    - 401: Token expired - needs refresh
    - 403: Insufficient permissions - missing account_management scope
    - 429: Rate limit exceeded - check Retry-After header
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        # Get user's token
        token_data = await get_user_token(user_id, supabase)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No Amazon account connected. Please connect your Amazon account first."
            )
        
        # Refresh token if needed
        token_data = await refresh_token_if_needed(user_id, token_data, supabase)
        
        # Call Amazon Account Management API with pagination
        response = await account_service.list_ads_accounts(
            token_data["access_token"],
            next_token=next_token
        )
        accounts = response.get("adsAccounts", [])

        # Store/update accounts in our database
        for account in accounts:
            # Check if account exists (using adsAccountId from API v3)
            existing = supabase.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).eq(
                "amazon_account_id", account.get("adsAccountId")  # Changed from accountId
            ).execute()
            
            if not existing.data:
                # Create new account record with API v3 structure
                # Extract first alternate ID if available for profile info
                alternate_ids = account.get("alternateIds", [])
                first_alternate = alternate_ids[0] if alternate_ids else {}

                # Map status to lowercase (API v3 uses CREATED, DISABLED, etc.)
                status_map = {
                    "CREATED": "active",
                    "PARTIALLY_CREATED": "partial",
                    "PENDING": "pending",
                    "DISABLED": "disabled"
                }
                api_status = account.get("status", "CREATED")

                new_account = AmazonAccount(
                    user_id=user_id,
                    account_name=account.get("accountName", "Unknown"),
                    amazon_account_id=account.get("adsAccountId"),  # Changed from accountId
                    marketplace_id=first_alternate.get("entityId"),  # From alternateIds
                    account_type="advertiser",  # Default since v3 doesn't specify type
                    status=status_map.get(api_status, "active"),
                    metadata={
                        "alternate_ids": alternate_ids,
                        "country_codes": account.get("countryCodes", []),
                        "errors": account.get("errors", {}),
                        "profile_id": first_alternate.get("profileId"),
                        "country_code": first_alternate.get("countryCode"),
                        "api_status": api_status  # Store original status
                    }
                )
                supabase.table("user_accounts").insert(new_account.to_dict()).execute()
            else:
                # Update existing account with API v3 structure
                alternate_ids = account.get("alternateIds", [])
                first_alternate = alternate_ids[0] if alternate_ids else {}

                # Map status to lowercase
                status_map = {
                    "CREATED": "active",
                    "PARTIALLY_CREATED": "partial",
                    "PENDING": "pending",
                    "DISABLED": "disabled"
                }
                api_status = account.get("status", "CREATED")

                supabase.table("user_accounts").update({
                    "last_synced_at": datetime.now(timezone.utc).isoformat(),
                    "status": status_map.get(api_status, "active"),
                    "metadata": {
                        **existing.data[0].get("metadata", {}),
                        "alternate_ids": alternate_ids,
                        "country_codes": account.get("countryCodes", []),
                        "errors": account.get("errors", {}),
                        "profile_id": first_alternate.get("profileId"),
                        "country_code": first_alternate.get("countryCode"),
                        "api_status": api_status
                    }
                }).eq("id", existing.data[0]["id"]).execute()
        
        logger.info(
            "Successfully retrieved Amazon Ads accounts",
            user_id=user_id,
            account_count=len(accounts)
        )
        
        return {
            "accounts": accounts,
            "total": len(accounts),
            "nextToken": response.get("nextToken"),
            "source": "Amazon Account Management API",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except TokenRefreshError as e:
        logger.error("Token refresh failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed. Please re-authenticate with Amazon."
        )
    except RateLimitError as e:
        logger.warning("Rate limit hit", user_id=user_id, retry_after=e.retry_after)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded. Please retry after {e.retry_after} seconds."},
            headers={"Retry-After": str(e.retry_after)}
        )
    except Exception as e:
        logger.error("Failed to list Amazon Ads accounts", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Amazon Ads accounts: {str(e)}"
        )


@router.get("/amazon-profiles", response_model=List[AmazonProfileResponse])
async def list_amazon_profiles(
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """
    List Amazon Advertising profiles using the Amazon Ads API
    
    **Endpoint Details:**
    - URL: GET https://advertising-api.amazon.com/v2/profiles
    - Required Headers: Authorization, Amazon-Advertising-API-ClientId
    - Returns: List of advertising profiles/accounts available to the authenticated user
    
    **Required Permissions:**
    - User must have valid Amazon OAuth tokens
    - Scopes: advertising::account_management
    
    **Response:**
    - Returns profiles with account information from Amazon's API
    - Each profile represents an advertising account
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        # Get user's token
        token_data = await get_user_token(user_id, supabase)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No Amazon account connected. Please connect your Amazon account first."
            )
        
        # Refresh token if needed
        token_data = await refresh_token_if_needed(user_id, token_data, supabase)
        
        # Call Amazon API to list profiles
        profiles = await account_service.list_profiles(token_data["access_token"])
        
        # Transform Amazon API response to our schema
        response_profiles = []
        for profile in profiles:
            response_profiles.append(AmazonProfileResponse(
                profile_id=profile.get("profileId"),
                country_code=profile.get("countryCode", ""),
                currency_code=profile.get("currencyCode", ""),
                timezone=profile.get("timezone", "UTC"),
                marketplace_id=profile.get("marketplaceId", ""),
                account_info=profile.get("accountInfo", {}),
                account_type=profile.get("accountInfo", {}).get("type", "unknown"),
                account_name=profile.get("accountInfo", {}).get("name", f"Profile {profile.get('profileId')}"),
                account_id=profile.get("accountInfo", {}).get("id", str(profile.get("profileId"))),
                valid_payment_method=profile.get("accountInfo", {}).get("validPaymentMethod", True)
            ))
        
        # Store/update profiles in our database
        for profile in response_profiles:
            # Check if account exists
            existing = supabase.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).eq(
                "amazon_account_id", profile.account_id
            ).execute()
            
            if not existing.data:
                # Create new account record
                account = AmazonAccount(
                    user_id=user_id,
                    account_name=profile.account_name,
                    amazon_account_id=profile.account_id,
                    marketplace_id=profile.marketplace_id,
                    account_type=profile.account_type,
                    metadata={
                        "profile_id": profile.profile_id,
                        "country_code": profile.country_code,
                        "currency_code": profile.currency_code,
                        "timezone": profile.timezone,
                        "account_info": profile.account_info
                    }
                )
                supabase.table("user_accounts").insert(account.to_dict()).execute()
            else:
                # Update existing account
                supabase.table("user_accounts").update({
                    "last_synced_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "profile_id": profile.profile_id,
                        "country_code": profile.country_code,
                        "currency_code": profile.currency_code,
                        "timezone": profile.timezone,
                        "account_info": profile.account_info
                    }
                }).eq("id", existing.data[0]["id"]).execute()
        
        logger.info(
            "Successfully retrieved Amazon profiles",
            user_id=user_id,
            profile_count=len(response_profiles)
        )
        
        return response_profiles
        
    except TokenRefreshError as e:
        logger.error("Token refresh failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed. Please re-authenticate with Amazon."
        )
    except RateLimitError as e:
        logger.warning("Rate limit hit", user_id=user_id, retry_after=e.retry_after)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded. Please retry after {e.retry_after} seconds."},
            headers={"Retry-After": str(e.retry_after)}
        )
    except Exception as e:
        logger.error("Failed to list Amazon profiles", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Amazon profiles: {str(e)}"
        )


@router.get("", response_model=AccountListResponse)
async def list_accounts(
    current_user: Dict = Depends(RequireAuth),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    account_status: Optional[str] = Query(None, description="Filter by status", alias="status"),
    supabase = Depends(get_supabase_client)
):
    """
    List all connected Amazon accounts for the current user
    
    Returns accounts stored in the database with pagination support.
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        # Build query
        query = supabase.table("user_accounts").select("*").eq("user_id", user_id)
        
        if account_status:
            query = query.eq("status", account_status)
        
        # Get total count
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)
        
        result = query.execute()
        
        accounts = []
        for acc in result.data:
            account_dict = AmazonAccount.from_dict(acc).to_dict()
            # Add marketplace name
            account_dict["marketplace_name"] = AmazonAccount.from_dict(acc).marketplace_name
            accounts.append(account_dict)
        
        return AccountListResponse(
            accounts=accounts,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to list accounts", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.get("/{account_id}", response_model=AccountDetailResponse)
async def get_account_details(
    account_id: str = Path(..., description="Account ID"),
    current_user: Dict = Depends(RequireAuth),
    include_profiles: bool = Query(False, description="Include associated profiles"),
    supabase = Depends(get_supabase_client)
):
    """
    Get detailed information for a specific account
    
    Includes account metadata and optionally fetches current profile information from Amazon API.
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        # Get account from database
        result = supabase.table("user_accounts").select("*").eq(
            "id", account_id
        ).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        account_data = result.data[0]
        account = AmazonAccount.from_dict(account_data)
        
        response = AccountDetailResponse(
            id=account.id,
            user_id=account.user_id,
            account_name=account.account_name,
            amazon_account_id=account.amazon_account_id,
            marketplace_id=account.marketplace_id,
            marketplace_name=account.marketplace_name,
            account_type=account.account_type,
            is_default=account.is_default,
            status=account.status,
            connected_at=account.connected_at,
            last_synced_at=account.last_synced_at,
            metadata=account.metadata
        )
        
        # Optionally fetch current profile info from Amazon
        if include_profiles and account.metadata.get("profile_id"):
            try:
                token_data = await get_user_token(user_id, supabase)
                if token_data:
                    token_data = await refresh_token_if_needed(user_id, token_data, supabase)
                    profile = await account_service.get_profile(
                        token_data["access_token"],
                        str(account.metadata["profile_id"])
                    )
                    response.profiles = [profile]
            except Exception as e:
                logger.warning(
                    "Failed to fetch profile from Amazon",
                    account_id=account_id,
                    error=str(e)
                )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get account details", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve account details: {str(e)}"
        )


@router.delete("/{account_id}/disconnect", response_model=DisconnectResponse)
async def disconnect_account(
    account_id: str = Path(..., description="Account ID to disconnect"),
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """
    Disconnect an Amazon account
    
    This will mark the account as inactive but preserve the record for audit purposes.
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        # Verify account ownership
        result = supabase.table("user_accounts").select("*").eq(
            "id", account_id
        ).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Update account status to disconnected
        supabase.table("user_accounts").update({
            "status": "disconnected",
            "metadata": {
                **result.data[0].get("metadata", {}),
                "disconnected_at": datetime.now(timezone.utc).isoformat(),
                "disconnected_by": user_id
            }
        }).eq("id", account_id).execute()
        
        logger.info(
            "Account disconnected",
            user_id=user_id,
            account_id=account_id
        )
        
        return DisconnectResponse(
            status="success",
            message="Account disconnected successfully",
            account_id=account_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect account", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect account: {str(e)}"
        )


@router.get("/health", response_model=List[AccountHealthStatus])
async def get_accounts_health(
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """
    Get health status of all connected accounts
    
    Checks token validity and last sync status for each account.
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        # Get all user accounts
        result = supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).execute()
        
        if not result.data:
            return []
        
        # Get user token status
        token_data = await get_user_token(user_id, supabase)
        token_valid = False
        requires_reauth = False
        
        if token_data:
            try:
                expires_at = datetime.fromisoformat(token_data["expires_at"].replace('Z', '+00:00'))
                token_valid = expires_at > datetime.now(timezone.utc)
            except:
                requires_reauth = True
        else:
            requires_reauth = True
        
        health_statuses = []
        for acc in result.data:
            account = AmazonAccount.from_dict(acc)
            
            # Determine health status
            if not token_valid:
                status = "error"
                error_message = "Authentication token expired or invalid"
            elif account.status != "active":
                status = "degraded"
                error_message = f"Account status: {account.status}"
            elif account.last_synced_at:
                # Check if last sync was recent (within 24 hours)
                last_sync = account.last_synced_at
                if (datetime.now(timezone.utc) - last_sync).days > 1:
                    status = "degraded"
                    error_message = "Account not synced recently"
                else:
                    status = "healthy"
                    error_message = None
            else:
                status = "degraded"
                error_message = "Account never synced"
            
            health_statuses.append(AccountHealthStatus(
                account_id=account.id,
                amazon_account_id=account.amazon_account_id,
                account_name=account.account_name,
                status=status,
                is_active=account.is_active,
                token_valid=token_valid,
                last_synced_at=account.last_synced_at,
                error_message=error_message,
                requires_reauth=requires_reauth
            ))
        
        return health_statuses
        
    except Exception as e:
        logger.error("Failed to get accounts health", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve health status: {str(e)}"
        )


@router.post("/{account_id}/reauthorize", response_model=ReauthorizeResponse)
async def reauthorize_account(
    account_id: str = Path(..., description="Account ID to re-authorize"),
    request: ReauthorizeRequest = Body(...),
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """
    Re-authorize an expired account
    
    Attempts to refresh the authentication token for the account.
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        # Verify account ownership
        result = supabase.table("user_accounts").select("*").eq(
            "id", account_id
        ).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Get current token
        token_data = await get_user_token(user_id, supabase)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication token found. Please reconnect your Amazon account."
            )
        
        # Force refresh or check if needed
        if request.force_refresh:
            # Force refresh the token
            try:
                new_tokens = await amazon_oauth_service.refresh_access_token(
                    token_data["refresh_token"]
                )
                
                # Update in database
                new_expires = datetime.now(timezone.utc) + timedelta(seconds=new_tokens.expires_in)
                
                update_data = {
                    "encrypted_access_token": token_service.encrypt_token(new_tokens.access_token),
                    "encrypted_refresh_token": token_service.encrypt_token(new_tokens.refresh_token),
                    "expires_at": new_expires.isoformat(),
                    "refresh_count": supabase.table("oauth_tokens").select("refresh_count").eq("user_id", user_id).execute().data[0]["refresh_count"] + 1,
                    "last_refresh": datetime.now(timezone.utc).isoformat()
                }
                
                supabase.table("oauth_tokens").update(update_data).eq("user_id", user_id).execute()
                
                # Update account status
                supabase.table("user_accounts").update({
                    "status": "active",
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", account_id).execute()
                
                return ReauthorizeResponse(
                    status="success",
                    message="Account re-authorized successfully",
                    token_refreshed=True,
                    expires_at=new_expires
                )
                
            except Exception as e:
                logger.error("Failed to refresh token", user_id=user_id, error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to refresh authentication. Please reconnect your Amazon account."
                )
        else:
            # Check if refresh is needed
            refreshed_token = await refresh_token_if_needed(user_id, token_data, supabase)
            token_refreshed = refreshed_token != token_data
            
            if token_refreshed:
                # Update account status
                supabase.table("user_accounts").update({
                    "status": "active",
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", account_id).execute()
            
            expires_at = datetime.fromisoformat(refreshed_token["expires_at"].replace('Z', '+00:00'))
            
            return ReauthorizeResponse(
                status="success",
                message="Account authorization checked",
                token_refreshed=token_refreshed,
                expires_at=expires_at
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reauthorize account", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-authorize account: {str(e)}"
        )


@router.post("/batch", response_model=BatchResponse)
async def batch_operations(
    batch: BatchOperation = Body(...),
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """
    Perform batch operations on multiple accounts
    
    Supported operations:
    - sync: Sync account data with Amazon API
    - disconnect: Disconnect multiple accounts
    - update: Update account metadata
    """
    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )
    
    try:
        results = []
        successful = 0
        failed = 0
        
        for account_id in batch.account_ids:
            try:
                # Verify ownership
                result = supabase.table("user_accounts").select("*").eq(
                    "id", account_id
                ).eq("user_id", user_id).execute()
                
                if not result.data:
                    results.append({
                        "account_id": account_id,
                        "status": "failed",
                        "error": "Account not found"
                    })
                    failed += 1
                    continue
                
                if batch.operation == "sync":
                    # Sync account with Amazon API
                    token_data = await get_user_token(user_id, supabase)
                    if token_data:
                        token_data = await refresh_token_if_needed(user_id, token_data, supabase)
                        
                        # Get profile data
                        profile_id = result.data[0].get("metadata", {}).get("profile_id")
                        if profile_id:
                            profile = await account_service.get_profile(
                                token_data["access_token"],
                                str(profile_id)
                            )
                            
                            # Update account data
                            supabase.table("user_accounts").update({
                                "last_synced_at": datetime.now(timezone.utc).isoformat(),
                                "metadata": {
                                    **result.data[0].get("metadata", {}),
                                    "last_sync_data": profile
                                }
                            }).eq("id", account_id).execute()
                            
                            results.append({
                                "account_id": account_id,
                                "status": "success",
                                "data": profile
                            })
                            successful += 1
                        else:
                            results.append({
                                "account_id": account_id,
                                "status": "failed",
                                "error": "No profile ID found"
                            })
                            failed += 1
                    else:
                        results.append({
                            "account_id": account_id,
                            "status": "failed",
                            "error": "No authentication token"
                        })
                        failed += 1
                        
                elif batch.operation == "disconnect":
                    # Disconnect account
                    supabase.table("user_accounts").update({
                        "status": "disconnected",
                        "metadata": {
                            **result.data[0].get("metadata", {}),
                            "disconnected_at": datetime.now(timezone.utc).isoformat()
                        }
                    }).eq("id", account_id).execute()
                    
                    results.append({
                        "account_id": account_id,
                        "status": "success"
                    })
                    successful += 1
                    
                elif batch.operation == "update":
                    # Update account metadata
                    if batch.params:
                        supabase.table("user_accounts").update(batch.params).eq(
                            "id", account_id
                        ).execute()
                        
                        results.append({
                            "account_id": account_id,
                            "status": "success"
                        })
                        successful += 1
                    else:
                        results.append({
                            "account_id": account_id,
                            "status": "failed",
                            "error": "No update parameters provided"
                        })
                        failed += 1
                        
                else:
                    results.append({
                        "account_id": account_id,
                        "status": "failed",
                        "error": f"Unknown operation: {batch.operation}"
                    })
                    failed += 1
                    
            except Exception as e:
                logger.error(
                    "Batch operation failed for account",
                    account_id=account_id,
                    operation=batch.operation,
                    error=str(e)
                )
                results.append({
                    "account_id": account_id,
                    "status": "failed",
                    "error": str(e)
                })
                failed += 1
        
        return BatchResponse(
            status="completed" if failed == 0 else "partial",
            total=len(batch.account_ids),
            successful=successful,
            failed=failed,
            results=results
        )
        
    except Exception as e:
        logger.error("Batch operation failed", operation=batch.operation, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch operation failed: {str(e)}"
        )


@router.post("/refresh-token", response_model=Dict[str, Any])
async def manual_token_refresh(
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """
    Manually trigger token refresh for the current user

    This endpoint allows testing the token refresh functionality
    and can be used to proactively refresh tokens before they expire.
    """
    from app.services.token_refresh_scheduler import get_token_refresh_scheduler

    # Get user ID from context
    user_context = current_user
    user_id = user_context.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )

    try:
        # Get the scheduler instance
        scheduler = get_token_refresh_scheduler()

        # Trigger manual refresh
        result = await scheduler.manual_refresh(user_id)

        if result['success']:
            logger.info(
                "Manual token refresh successful",
                user_id=user_id,
                token_id=result.get('token_id')
            )
            return {
                "status": "success",
                "message": result.get('message', 'Token refreshed successfully'),
                "token_id": result.get('token_id'),
                "refreshed_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            logger.warning(
                "Manual token refresh failed",
                user_id=user_id,
                error=result.get('error')
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Token refresh failed')
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Manual token refresh error", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )