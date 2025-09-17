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
from app.services.dsp_amc_service import dsp_amc_service
from app.services.account_sync_service import account_sync_service
from app.db.base import get_supabase_client, get_supabase_service_client
from app.core.exceptions import TokenRefreshError, RateLimitError, DSPSeatsError, MissingDSPAccessError
from app.models.amazon_account import AmazonAccount
from app.schemas.account_types import (
    DSPSeatsResponse, DSPSeatsRefreshRequest, DSPSeatsRefreshResponse,
    DSPSyncHistoryResponse, DSPSyncHistoryEntry
)

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

            # Check if tokens are encrypted (have encryption prefix) or plain text
            access_token_raw = token_data["access_token"]
            refresh_token_raw = token_data["refresh_token"]

            # If tokens are encrypted, decrypt them. Otherwise use as-is
            try:
                access_token = token_service.decrypt_token(access_token_raw)
                refresh_token = token_service.decrypt_token(refresh_token_raw)
            except Exception:
                # Tokens might be stored as plain text
                logger.warning("Tokens appear to be stored as plain text", user_id=user_id)
                access_token = access_token_raw
                refresh_token = refresh_token_raw

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
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
                "access_token": token_service.encrypt_token(new_tokens.access_token),
                "refresh_token": token_service.encrypt_token(new_tokens.refresh_token),
                "expires_at": new_expires.isoformat(),
                "refresh_count": supabase.table("oauth_tokens").select("refresh_count").eq("user_id", user_id).execute().data[0]["refresh_count"] + 1,
                "last_refresh_at": now.isoformat()  # Also fixed field name here
            }
            
            supabase.table("oauth_tokens").update(update_data).eq("user_id", user_id).execute()

            # Update all user accounts' last_synced_at since they share the same token
            supabase.table("user_accounts").update({
                "last_synced_at": now.isoformat()
            }).eq("user_id", user_id).execute()

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

@router.get("/sponsored-ads")
async def get_sponsored_ads_accounts(
    current_user: Dict = Depends(RequireAuth),
    next_token: Optional[str] = Query(None, description="Pagination token for next page"),
    max_results: int = Query(100, ge=1, le=100, description="Maximum results per page")
) -> Dict[str, Any]:
    """
    Get Sponsored Ads accounts filtered by account_type='advertising'

    Returns:
        Dictionary containing advertising accounts from database
    """
    supabase = get_supabase_service_client()
    user_context = current_user
    user_id = user_context.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    try:
        # Query database for accounts with account_type='advertising'
        result = supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "account_type", "advertising"
        ).execute()

        accounts = []
        if result.data:
            for acc in result.data:
                account_dict = AmazonAccount.from_dict(acc).to_dict()
                # Add marketplace name
                account_dict["marketplace_name"] = AmazonAccount.from_dict(acc).marketplace_name
                accounts.append(account_dict)

        logger.info(f"Retrieved {len(accounts)} sponsored ads accounts from database for user {user_id}")

        return {
            "accounts": accounts,
            "total_count": len(accounts)
        }

    except Exception as e:
        logger.error(f"Failed to retrieve sponsored ads accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sponsored ads accounts: {str(e)}"
        )


@router.get("/dsp")
async def get_dsp_advertisers(
    current_user: Dict = Depends(RequireAuth)
) -> Dict[str, Any]:
    """
    Get DSP advertisers for the current user

    Returns:
        Dictionary containing DSP advertisers
    """
    supabase = get_supabase_service_client()
    user_context = current_user
    user_id = user_context.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    try:
        # Query database for accounts with account_type='dsp'
        result = supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "account_type", "dsp"
        ).execute()

        accounts = []
        if result.data:
            for acc in result.data:
                account_dict = AmazonAccount.from_dict(acc).to_dict()
                # Add marketplace name
                account_dict["marketplace_name"] = AmazonAccount.from_dict(acc).marketplace_name
                accounts.append(account_dict)

        logger.info(f"Retrieved {len(accounts)} DSP advertisers from database for user {user_id}")

        return {
            "accounts": accounts,
            "total_count": len(accounts)
        }

    except Exception as e:
        logger.error(f"Failed to retrieve DSP advertisers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve DSP advertisers: {str(e)}"
        )


@router.get("/amc")
async def get_amc_accounts(
    current_user: Dict = Depends(RequireAuth)
) -> Dict[str, Any]:
    """
    Get AMC accounts filtered by account_type='amc'

    Returns:
        Dictionary containing AMC accounts from database
    """
    supabase = get_supabase_service_client()
    user_context = current_user
    user_id = user_context.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    try:
        # Query database for accounts with account_type='amc'
        result = supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "account_type", "amc"
        ).execute()

        instances = []
        if result.data:
            for acc in result.data:
                account_dict = AmazonAccount.from_dict(acc).to_dict()
                # Add marketplace name
                account_dict["marketplace_name"] = AmazonAccount.from_dict(acc).marketplace_name
                instances.append(account_dict)

        logger.info(f"Retrieved {len(instances)} AMC accounts from database for user {user_id}")

        return {
            "instances": instances,
            "total_count": len(instances)
        }

    except Exception as e:
        logger.error(f"Failed to retrieve AMC accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AMC accounts: {str(e)}"
        )


@router.get("/amc-instances")
async def get_amc_instances(
    current_user: Dict = Depends(RequireAuth)
) -> Dict[str, Any]:
    """
    Get AMC instances for the current user

    Returns:
        Dictionary containing AMC instances
    """
    supabase = get_supabase_service_client()
    user_context = current_user
    user_id = user_context.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    try:
        # Query database for accounts with account_type='amc'
        result = supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "account_type", "amc"
        ).execute()

        instances = []
        if result.data:
            for acc in result.data:
                account_dict = AmazonAccount.from_dict(acc).to_dict()
                # Add marketplace name
                account_dict["marketplace_name"] = AmazonAccount.from_dict(acc).marketplace_name
                instances.append(account_dict)

        logger.info(f"Retrieved {len(instances)} AMC instances from database for user {user_id}")

        return {
            "instances": instances,
            "total_count": len(instances)
        }

    except Exception as e:
        logger.error(f"Failed to retrieve AMC instances: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AMC instances: {str(e)}"
        )

@router.get("/all-account-types")
async def list_all_account_types_simple(
    include_dsp: bool = Query(True, description="Include DSP advertisers")
):
    """
    Simplified account sync without authentication (development mode)
    """
    try:
        # Get OAuth tokens directly from token service
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete Amazon authentication first."
            )

        access_token = tokens["access_token"]

        # Fetch DSP advertisers from Amazon API
        account_data = await dsp_amc_service.list_all_account_types(
            access_token=access_token,
            include_regular=False,
            include_dsp=include_dsp,
            include_amc=False
        )

        # Return DSP advertisers directly from API (no database operations)
        normalized_accounts = []

        if include_dsp:
            for advertiser in account_data.get("dsp_advertisers", []):
                normalized_accounts.append({
                    "id": f"dsp_{advertiser.get('advertiserId')}",
                    "name": advertiser.get("name") or advertiser.get("advertiserName"),
                    "type": "dsp",
                    "platform_id": advertiser.get("advertiserId"),
                    "status": "active",
                    "metadata": {
                        **advertiser,
                        "sync_method": "direct_api"
                    }
                })

        return {
            "accounts": normalized_accounts,
            "summary": {
                "total": len(normalized_accounts),
                "dsp": len([a for a in normalized_accounts if a["type"] == "dsp"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to retrieve accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.get("/all-account-types-old")
async def list_all_account_types_old(
    include_advertising: bool = Query(True, description="Include regular advertising accounts"),
    include_dsp: bool = Query(True, description="Include DSP advertisers"),
    include_amc: bool = Query(True, description="Include AMC instances"),
):
    """
    List all Amazon account types (Advertising, DSP, AMC) in a unified response

    **What This Endpoint Does:**
    - Fetches regular advertising accounts, DSP advertisers, and AMC instances in parallel
    - Normalizes the data into a consistent format for the frontend
    - Stores/updates all account types in the database

    **Account Type Differences:**
    - **Advertising Accounts**: Standard Sponsored Products/Brands/Display accounts
    - **DSP Advertisers**: Display advertising entities with programmatic capabilities
    - **AMC Instances**: Analytics instances for advanced data analysis

    **Response Structure:**
    ```json
    {
        "accounts": [
            {
                "id": "unique_id",
                "name": "Account Name",
                "type": "advertising|dsp|amc",
                "platform_id": "adsAccountId|advertiserId|instanceId",
                "status": "active|suspended|provisioning",
                "metadata": {...}
            }
        ],
        "summary": {
            "total": 10,
            "advertising": 5,
            "dsp": 3,
            "amc": 2
        }
    }
    ```

    **Required Scopes:**
    - advertising::account_management (for regular accounts)
    - advertising::dsp_campaigns (for DSP)
    - advertising::amc:read (for AMC)
    """
    # Use default user ID for development (no authentication)
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    supabase = get_supabase_service_client()

    try:
        # Get OAuth tokens directly from token service
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete Amazon authentication first."
            )

        access_token = tokens["access_token"]

        # Fetch all account types in parallel
        account_data = await dsp_amc_service.list_all_account_types(
            access_token=access_token,
            include_regular=include_advertising,
            include_dsp=include_dsp,
            include_amc=include_amc
        )

        # Normalize and store all accounts
        normalized_accounts = []

        # Process advertising accounts
        for account in account_data.get("advertising_accounts", []):
            # Check if account exists
            existing = supabase.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).eq(
                "amazon_account_id", account.get("adsAccountId")
            ).execute()

            if not existing.data:
                # Create new account record
                alternate_ids = account.get("alternateIds", [])
                first_alternate = alternate_ids[0] if alternate_ids else {}

                status_map = {
                    "CREATED": "active",
                    "PARTIALLY_CREATED": "partial",
                    "PENDING": "pending",
                    "DISABLED": "suspended"
                }
                api_status = account.get("status", "CREATED")

                new_account = AmazonAccount(
                    user_id=user_id,
                    account_name=account.get("accountName", "Unknown"),
                    amazon_account_id=account.get("adsAccountId"),
                    marketplace_id=first_alternate.get("entityId"),
                    account_type="advertising",
                    status=status_map.get(api_status, "active"),
                    metadata={
                        "alternate_ids": alternate_ids,
                        "country_codes": account.get("countryCodes", []),
                        "errors": account.get("errors", {}),
                        "profile_id": first_alternate.get("profileId"),
                        "country_code": first_alternate.get("countryCode"),
                        "api_status": api_status
                    }
                )
                result = supabase.table("user_accounts").insert(new_account.to_dict()).execute()
                db_account = result.data[0] if result.data else new_account.to_dict()
            else:
                # Update existing account
                db_account = existing.data[0]
                supabase.table("user_accounts").update({
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", db_account["id"]).execute()

            normalized_accounts.append({
                "id": db_account["id"],
                "name": account.get("accountName"),
                "type": "advertising",
                "platform_id": account.get("adsAccountId"),
                "status": db_account["status"],
                "metadata": {
                    **account,
                    "db_id": db_account["id"]
                }
            })

        # Process DSP advertisers using the updated sync service
        for advertiser in account_data.get("dsp_advertisers", []):
            try:
                # Use the updated account_sync_service that properly maps to dedicated columns
                success, was_created = await account_sync_service._upsert_dsp_advertiser(user_id, advertiser)

                if success:
                    # Get the updated account from database to return in response
                    existing = supabase.table("user_accounts").select("*").eq(
                        "user_id", user_id
                    ).eq(
                        "amazon_account_id", advertiser.get("advertiserId")
                    ).execute()

                    if existing.data:
                        db_account = existing.data[0]
                        normalized_accounts.append({
                            "id": db_account["id"],
                            "name": advertiser.get("name") or advertiser.get("advertiserName"),
                            "type": "dsp",
                            "platform_id": advertiser.get("advertiserId"),
                            "status": db_account["status"],
                            "metadata": {
                                **advertiser,
                                "db_id": db_account["id"],
                                "was_created": was_created
                            }
                        })
                else:
                    logger.error(f"Failed to sync DSP advertiser {advertiser.get('advertiserId')}")
            except Exception as e:
                logger.error(f"Error syncing DSP advertiser {advertiser.get('advertiserId')}: {str(e)}")
                # Continue with other advertisers even if one fails

        # Process AMC instances
        for instance in account_data.get("amc_instances", []):
            # Check if AMC instance exists
            existing = supabase.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).eq(
                "amazon_account_id", instance.get("instanceId")
            ).execute()

            if not existing.data:
                # Create new AMC instance record
                status_map = {
                    "ACTIVE": "active",
                    "PROVISIONING": "provisioning",
                    "SUSPENDED": "suspended"
                }

                # Get first linked advertiser if available
                linked_advertisers = instance.get("advertisers", [])
                first_advertiser = linked_advertisers[0] if linked_advertisers else {}

                new_account = AmazonAccount(
                    user_id=user_id,
                    account_name=instance.get("instanceName", "Unknown AMC"),
                    amazon_account_id=instance.get("instanceId"),
                    marketplace_id=instance.get("region"),
                    account_type="amc",
                    status=status_map.get(instance.get("status", "ACTIVE"), "active"),
                    metadata={
                        "instance_type": instance.get("instanceType"),
                        "region": instance.get("region"),
                        "data_retention_days": instance.get("dataRetentionDays"),
                        "created_date": instance.get("createdDate"),
                        "linked_advertisers": linked_advertisers,
                        "primary_advertiser_id": first_advertiser.get("advertiserId"),
                        "primary_advertiser_name": first_advertiser.get("advertiserName")
                    }
                )
                result = supabase.table("user_accounts").insert(new_account.to_dict()).execute()
                db_account = result.data[0] if result.data else new_account.to_dict()
            else:
                # Update existing AMC instance
                db_account = existing.data[0]
                supabase.table("user_accounts").update({
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", db_account["id"]).execute()

            normalized_accounts.append({
                "id": db_account["id"],
                "name": instance.get("instanceName"),
                "type": "amc",
                "platform_id": instance.get("instanceId"),
                "status": db_account["status"],
                "metadata": {
                    **instance,
                    "db_id": db_account["id"]
                }
            })

        # Calculate summary
        summary = {
            "total": len(normalized_accounts),
            "advertising": len([a for a in normalized_accounts if a["type"] == "advertising"]),
            "dsp": len([a for a in normalized_accounts if a["type"] == "dsp"]),
            "amc": len([a for a in normalized_accounts if a["type"] == "amc"])
        }

        logger.info(
            "Successfully retrieved all account types",
            user_id=user_id,
            summary=summary
        )

        return {
            "accounts": normalized_accounts,
            "summary": summary,
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
        logger.error("Failed to list all account types", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.get("/amazon-ads-accounts")
async def list_amazon_ads_accounts(
    current_user: Dict = Depends(RequireAuth),
    next_token: Optional[str] = Query(None, description="Pagination token for next page"),
    max_results: int = Query(100, ge=1, le=100, description="Maximum results per page")
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
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

    # Get user ID from context - use the database UUID
    user_context = current_user
    user_id = user_context.get("user_id")  # This is the database UUID

    if not user_id:
        # If no database user ID, user hasn't been synced yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Please log out and log in again."
        )

    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
):
    """
    List all connected Amazon accounts for the current user
    
    Returns accounts stored in the database with pagination support.
    """
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
        
        # Get token info for the user to determine account status
        token_data = await get_user_token(user_id, supabase)
        token_expires_at = None
        if token_data:
            token_expires_at = token_data.get("expires_at")

        accounts = []
        for acc in result.data:
            account_dict = AmazonAccount.from_dict(acc).to_dict()
            # Add marketplace name
            account_dict["marketplace_name"] = AmazonAccount.from_dict(acc).marketplace_name
            # Add token expiry info for status determination
            account_dict["token_expires_at"] = token_expires_at
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
):
    """
    Get detailed information for a specific account
    
    Includes account metadata and optionally fetches current profile information from Amazon API.
    """
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
):
    """
    Disconnect an Amazon account
    
    This will mark the account as inactive but preserve the record for audit purposes.
    """
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
):
    """
    Get health status of all connected accounts
    
    Checks token validity and last sync status for each account.
    """
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
):
    """
    Re-authorize an expired account
    
    Attempts to refresh the authentication token for the account.
    """
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
                    "access_token": token_service.encrypt_token(new_tokens.access_token),
                    "refresh_token": token_service.encrypt_token(new_tokens.refresh_token),
                    "expires_at": new_expires.isoformat(),
                    "refresh_count": supabase.table("oauth_tokens").select("refresh_count").eq("user_id", user_id).execute().data[0]["refresh_count"] + 1,
                    "last_refresh_at": datetime.now(timezone.utc).isoformat()
                }
                
                supabase.table("oauth_tokens").update(update_data).eq("user_id", user_id).execute()

                # Update ALL user accounts' status and last_synced_at since they share the same token
                supabase.table("user_accounts").update({
                    "status": "active",
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }).eq("user_id", user_id).execute()
                
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
                # Update ALL user accounts' status and last_synced_at since they share the same token
                supabase.table("user_accounts").update({
                    "status": "active",
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }).eq("user_id", user_id).execute()
            
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
):
    """
    Perform batch operations on multiple accounts
    
    Supported operations:
    - sync: Sync account data with Amazon API
    - disconnect: Disconnect multiple accounts
    - update: Update account metadata
    """
    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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
):
    """
    Manually trigger token refresh for the current user

    This endpoint allows testing the token refresh functionality
    and can be used to proactively refresh tokens before they expire.
    """
    from app.services.token_refresh_scheduler import get_token_refresh_scheduler

    # Use service role client for database operations to bypass RLS
    supabase = get_supabase_service_client()

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


# ============================================================================
# DSP SEATS ENDPOINTS
# ============================================================================

@router.get("/dsp/{advertiser_id}/seats")
async def get_dsp_advertiser_seats(
    advertiser_id: str = Path(..., description="DSP Advertiser ID"),
    current_user: Dict = Depends(RequireAuth),
    exchange_ids: Optional[List[str]] = Query(None, description="Filter by exchange IDs"),
    max_results: int = Query(200, ge=1, le=200, description="Maximum results"),
    next_token: Optional[str] = Query(None, description="Pagination token"),
    profile_id: Optional[str] = Query(None, description="Optional profile ID filter")
) -> Dict[str, Any]:
    """
    Get seat information for a DSP advertiser

    **Endpoint Details:**
    - Calls Amazon DSP Seats API: POST /dsp/v1/seats/advertisers/current/list
    - Requires DSP advertiser access
    - Returns seat allocations across exchanges

    **Required Permissions:**
    - Valid DSP advertiser ID
    - advertising::dsp_campaigns scope

    **Response Structure:**
    {
        "advertiserSeats": [...],
        "nextToken": "string",
        "timestamp": "ISO 8601",
        "cached": false
    }
    """
    supabase = get_supabase_service_client()
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    try:
        # Verify user owns this DSP advertiser
        account_result = supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "amazon_account_id", advertiser_id
        ).eq(
            "account_type", "dsp"
        ).execute()

        if not account_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DSP advertiser not found or not owned by user"
            )

        # Get user's token
        token_data = await get_user_token(user_id, supabase)
        if not token_data:
            logger.warning(
                "User has no Amazon token for DSP seats request",
                user_id=user_id,
                advertiser_id=advertiser_id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Amazon account not connected. Please reconnect your Amazon account in Settings."
            )

        # Refresh token if needed
        token_data = await refresh_token_if_needed(user_id, token_data, supabase)

        # Call DSP Seats API
        seats_data = await dsp_amc_service.list_advertiser_seats(
            access_token=token_data["access_token"],
            advertiser_id=advertiser_id,
            exchange_ids=exchange_ids,
            max_results=max_results,
            next_token=next_token,
            profile_id=profile_id
        )

        # Update database with seats information
        seats_count = 0
        exchanges_count = 0
        sync_status = "success"

        if seats_data.get("advertiserSeats"):
            seats_metadata = {
                "exchanges": [],
                "last_seats_sync": datetime.now(timezone.utc).isoformat(),
                "total_seats": 0
            }

            for advertiser_seat in seats_data["advertiserSeats"]:
                if advertiser_seat["advertiserId"] == advertiser_id:
                    current_seats = advertiser_seat.get("currentSeats", [])
                    seats_metadata["exchanges"] = current_seats
                    seats_metadata["total_seats"] = len(current_seats)
                    seats_count = len(current_seats)
                    exchanges_count = len(set(seat.get("exchangeId") for seat in current_seats if seat.get("exchangeId")))
                    break

            # Update account metadata
            current_metadata = account_result.data[0].get("metadata", {})
            current_metadata["seats"] = seats_metadata

            supabase.table("user_accounts").update({
                "seats_metadata": seats_metadata,
                "last_synced_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", account_result.data[0]["id"]).execute()
        else:
            sync_status = "partial" if seats_data.get("error") else "success"

        # Log sync attempt in dsp_seats_sync_log
        try:
            supabase.table("dsp_seats_sync_log").insert({
                "user_account_id": account_result.data[0]["id"],
                "advertiser_id": advertiser_id,
                "sync_status": sync_status,
                "seats_retrieved": seats_count,
                "exchanges_count": exchanges_count,
                "error_message": seats_data.get("error") if sync_status != "success" else None,
                "request_metadata": {
                    "max_results": max_results,
                    "next_token": next_token,
                    "exchange_ids": exchange_ids,
                    "profile_id": profile_id
                },
                "response_metadata": {
                    "has_next_token": bool(seats_data.get("nextToken")),
                    "advertiser_seats_count": len(seats_data.get("advertiserSeats", []))
                }
            }).execute()
        except Exception as sync_log_error:
            logger.warning(
                "Failed to log DSP seats sync attempt",
                user_id=user_id,
                advertiser_id=advertiser_id,
                error=str(sync_log_error)
            )

        logger.info(
            "Successfully retrieved DSP advertiser seats",
            user_id=user_id,
            advertiser_id=advertiser_id,
            seat_count=len(seats_data.get("advertiserSeats", []))
        )

        return {
            **seats_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cached": False
        }

    except HTTPException:
        raise
    except TokenRefreshError as e:
        logger.error("Token refresh failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed. Please re-authenticate."
        )
    except RateLimitError as e:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded. Retry after {e.retry_after} seconds."},
            headers={"Retry-After": str(e.retry_after)}
        )
    except Exception as e:
        logger.error(
            "Failed to get DSP advertiser seats",
            user_id=user_id,
            advertiser_id=advertiser_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve seats: {str(e)}"
        )


@router.post("/dsp/{advertiser_id}/seats/refresh", response_model=DSPSeatsRefreshResponse)
async def refresh_dsp_seats(
    advertiser_id: str = Path(..., description="DSP Advertiser ID"),
    request: DSPSeatsRefreshRequest = Body(...),
    current_user: Dict = Depends(RequireAuth)
) -> DSPSeatsRefreshResponse:
    """
    Force refresh of seat data for a DSP advertiser, bypassing cache

    **Purpose:**
    - Manually trigger data updates
    - Bypass cache for immediate freshness
    - Useful after making changes in Amazon DSP console
    """
    supabase = get_supabase_service_client()
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    try:
        # Verify user owns this DSP advertiser
        account_result = supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "amazon_account_id", advertiser_id
        ).eq(
            "account_type", "dsp"
        ).execute()

        if not account_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DSP advertiser not found or not owned by user"
            )

        # Check if sync is already in progress
        recent_sync = supabase.table("dsp_seats_sync_log").select("*").eq(
            "advertiser_id", advertiser_id
        ).eq(
            "sync_status", "in_progress"
        ).gte(
            "created_at",
            (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        ).execute()

        if recent_sync.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sync already in progress for this advertiser"
            )

        # Get user's token
        token_data = await get_user_token(user_id, supabase)
        if not token_data:
            logger.warning(
                "User has no Amazon token for DSP seats request",
                user_id=user_id,
                advertiser_id=advertiser_id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Amazon account not connected. Please reconnect your Amazon account in Settings."
            )

        # Force refresh token if requested
        if request.force:
            token_data = await refresh_token_if_needed(user_id, token_data, supabase)

        # Call DSP Seats API
        seats_data = await dsp_amc_service.list_advertiser_seats(
            access_token=token_data["access_token"],
            advertiser_id=advertiser_id
        )

        # Process seats data
        seats_updated = 0
        if seats_data.get("advertiserSeats"):
            for advertiser_seat in seats_data["advertiserSeats"]:
                if advertiser_seat["advertiserId"] == advertiser_id:
                    seats_updated = len(advertiser_seat.get("currentSeats", []))
                    break

        # Log the sync
        sync_log_entry = {
            "user_account_id": account_result.data[0]["id"],
            "advertiser_id": advertiser_id,
            "sync_status": "success",
            "seats_retrieved": seats_updated,
            "exchanges_count": seats_updated,
            "request_metadata": {"force": request.force},
            "response_metadata": {"has_more": bool(seats_data.get("nextToken"))}
        }

        sync_log_result = supabase.table("dsp_seats_sync_log").insert(
            sync_log_entry
        ).execute()

        sync_log_id = sync_log_result.data[0]["id"] if sync_log_result.data else None

        # Update account metadata
        seats_metadata = {
            "exchanges": [],
            "last_seats_sync": datetime.now(timezone.utc).isoformat(),
            "total_seats": seats_updated,
            "sync_status": "success"
        }

        if seats_data.get("advertiserSeats"):
            for advertiser_seat in seats_data["advertiserSeats"]:
                if advertiser_seat["advertiserId"] == advertiser_id:
                    seats_metadata["exchanges"] = advertiser_seat.get("currentSeats", [])
                    break

        supabase.table("user_accounts").update({
            "seats_metadata": seats_metadata,
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", account_result.data[0]["id"]).execute()

        logger.info(
            "Successfully refreshed DSP seats",
            user_id=user_id,
            advertiser_id=advertiser_id,
            seats_updated=seats_updated
        )

        return DSPSeatsRefreshResponse(
            success=True,
            seats_updated=seats_updated,
            last_sync=datetime.now(timezone.utc),
            sync_log_id=sync_log_id if request.include_sync_log else None
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log failed sync
        try:
            supabase.table("dsp_seats_sync_log").insert({
                "user_account_id": account_result.data[0]["id"] if account_result.data else None,
                "advertiser_id": advertiser_id,
                "sync_status": "failed",
                "seats_retrieved": 0,
                "exchanges_count": 0,
                "error_message": str(e)
            }).execute()
        except:
            pass

        logger.error(
            "Failed to refresh DSP seats",
            user_id=user_id,
            advertiser_id=advertiser_id,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh seats: {str(e)}"
        )


@router.get("/dsp/{advertiser_id}/seats/sync-history", response_model=DSPSyncHistoryResponse)
async def get_dsp_seats_sync_history(
    advertiser_id: str = Path(..., description="DSP Advertiser ID"),
    current_user: Dict = Depends(RequireAuth),
    limit: int = Query(10, ge=1, le=100, description="Number of records"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    status_filter: Optional[str] = Query(None, regex="^(success|failed|partial)$", description="Filter by sync status")
) -> DSPSyncHistoryResponse:
    """
    Retrieve synchronization history for DSP seats data

    **Purpose:**
    - View sync history and patterns
    - Debug sync issues
    - Audit data refresh operations
    """
    supabase = get_supabase_service_client()
    user_id = current_user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    try:
        # Verify user owns this DSP advertiser
        account_result = supabase.table("user_accounts").select("id").eq(
            "user_id", user_id
        ).eq(
            "amazon_account_id", advertiser_id
        ).eq(
            "account_type", "dsp"
        ).execute()

        if not account_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DSP advertiser not found or not owned by user"
            )

        account_id = account_result.data[0]["id"]

        # Build query
        query = supabase.table("dsp_seats_sync_log").select("*").eq(
            "user_account_id", account_id
        ).eq(
            "advertiser_id", advertiser_id
        )

        # Apply status filter if provided
        if status_filter:
            query = query.eq("sync_status", status_filter)

        # Get total count
        count_result = query.execute()
        total_count = len(count_result.data) if count_result.data else 0

        # Get paginated results
        sync_logs = query.order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        # Format response
        sync_history = []
        for log in sync_logs.data or []:
            sync_history.append(DSPSyncHistoryEntry(
                id=log["id"],
                sync_status=log["sync_status"],
                seats_retrieved=log["seats_retrieved"],
                exchanges_count=log["exchanges_count"],
                error_message=log.get("error_message"),
                created_at=datetime.fromisoformat(log["created_at"].replace("Z", "+00:00"))
            ))

        logger.info(
            "Retrieved DSP seats sync history",
            user_id=user_id,
            advertiser_id=advertiser_id,
            records=len(sync_history)
        )

        return DSPSyncHistoryResponse(
            sync_history=sync_history,
            total_count=total_count,
            limit=limit,
            offset=offset
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get sync history",
            user_id=user_id,
            advertiser_id=advertiser_id,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sync history: {str(e)}"
        )


@router.post("/sync")
async def sync_all_accounts() -> Dict[str, Any]:
    """
    Sync all account types (Sponsored Ads, DSP, AMC) from Amazon API to database
    Note: Clerk auth removed, using hardcoded user

    Returns:
        Dictionary with sync results including counts by account type
    """
    try:
        # Since Clerk auth was removed, use hardcoded user ID
        user_id = "52a86382-266b-4004-bfd9-6bd6a64026eb"
        logger.info(f"Sync requested for user: {user_id}")

        # Get tokens
        from app.services.token_service import token_service
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No Amazon tokens found. Please connect your Amazon account."
            )

        access_token = tokens["access_token"]

        # Use account sync service to fetch and save all account types
        from app.services.account_sync_service import account_sync_service

        # Fetch all account types from Amazon API
        all_data = await account_sync_service._fetch_all_account_types(access_token)

        # Process and save to database
        result = await account_sync_service._process_all_account_types(
            user_id=user_id,
            account_data=all_data
        )

        logger.info(
            "Successfully synced all account types",
            user_id=user_id,
            result=result
        )

        return {
            "status": "success",
            "message": "Account sync completed",
            "result": result,
            "data": {
                "advertising_accounts": len(all_data.get("advertising_accounts", [])),
                "dsp_advertisers": len(all_data.get("dsp_advertisers", [])),
                "amc_instances": len(all_data.get("amc_instances", []))
            }
        }

    except HTTPException:
        raise
    except TokenRefreshError as e:
        logger.error("Token refresh failed during sync", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed. Please re-authenticate."
        )
    except Exception as e:
        logger.error(
            "Failed to sync accounts",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync accounts: {str(e)}"
        )


@router.post("/sync-direct")
async def sync_all_accounts_direct() -> Dict[str, Any]:
    """
    Direct sync endpoint without Clerk auth for testing
    Syncs all account types to the hardcoded user
    """
    try:
        # Use hardcoded user ID
        user_id = "52a86382-266b-4004-bfd9-6bd6a64026eb"

        # Get tokens
        from app.services.token_service import token_service
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No Amazon tokens found. Please connect your Amazon account."
            )

        access_token = tokens["access_token"]

        # Use account sync service to fetch and save all account types
        from app.services.account_sync_service import account_sync_service

        # Fetch all account types from Amazon API
        all_data = await account_sync_service._fetch_all_account_types(access_token)

        # Process and save to database
        result = await account_sync_service._process_all_account_types(
            user_id=user_id,
            account_data=all_data
        )

        logger.info(
            "Successfully synced all account types (direct)",
            user_id=user_id,
            result=result
        )

        return {
            "status": "success",
            "message": "Account sync completed (direct)",
            "result": result,
            "data": {
                "advertising_accounts": len(all_data.get("advertising_accounts", [])),
                "dsp_advertisers": len(all_data.get("dsp_advertisers", [])),
                "amc_instances": len(all_data.get("amc_instances", []))
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to sync accounts (direct)",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync accounts: {str(e)}"
        )