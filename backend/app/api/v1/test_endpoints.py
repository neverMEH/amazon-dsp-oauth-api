"""
Test endpoints for Amazon API calls without Clerk authentication

These endpoints bypass Clerk authentication and use admin key protection instead.
They are designed for testing and debugging Amazon API responses.
"""

from fastapi import APIRouter, HTTPException, Header, Query, status
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime, timezone

from app.config import settings
from app.services.dsp_amc_service import dsp_amc_service
from app.services.account_service import account_service
from app.services.token_service import token_service
from app.db.base import get_supabase_service_client

router = APIRouter(prefix="/test", tags=["test"])
logger = structlog.get_logger()


def validate_admin_key(admin_key: Optional[str]) -> None:
    """Validate admin key for test endpoints"""
    if admin_key != settings.admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Invalid or missing admin key. Required for test endpoints.",
                "hint": "Use X-Admin-Key header with valid admin key"
            }
        )


@router.get("/health")
async def test_health():
    """Test endpoint health check"""
    return {
        "status": "healthy",
        "message": "Test endpoints are available",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "admin_key_required": True
    }


@router.get("/tokens/status")
async def get_token_status(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """Get current OAuth token status"""
    validate_admin_key(admin_key)

    try:
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            return {
                "status": "no_tokens",
                "message": "No OAuth tokens found in database"
            }

        return {
            "status": "tokens_found",
            "token_info": {
                "user_id": tokens.get("user_id"),
                "expires_at": tokens.get("expires_at"),
                "refresh_count": tokens.get("refresh_count", 0),
                "scope": tokens.get("scope"),
                "has_access_token": bool(tokens.get("access_token")),
                "has_refresh_token": bool(tokens.get("refresh_token"))
            }
        }
    except Exception as e:
        logger.error("Failed to get token status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get token status: {str(e)}"
        )


@router.get("/amazon/profiles")
async def test_amazon_profiles(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """Test Amazon Profiles API call"""
    validate_admin_key(admin_key)

    try:
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete authentication first."
            )

        access_token = tokens["access_token"]
        profiles = await account_service.list_profiles(access_token)

        return {
            "status": "success",
            "endpoint": "GET /v2/profiles",
            "profiles_count": len(profiles) if isinstance(profiles, list) else 0,
            "profiles": profiles,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to test profiles endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Amazon Profiles API test failed: {str(e)}"
        )


@router.get("/amazon/accounts")
async def test_amazon_accounts(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    max_results: int = Query(100, ge=1, le=500, description="Max results to return")
):
    """Test Amazon Account Management API call"""
    validate_admin_key(admin_key)

    try:
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete authentication first."
            )

        access_token = tokens["access_token"]
        accounts_data = await account_service.list_ads_accounts(
            access_token,
            next_token=None
        )

        accounts = accounts_data.get("adsAccounts", [])

        return {
            "status": "success",
            "endpoint": "POST /adsAccounts/list",
            "accounts_count": len(accounts),
            "total_results": len(accounts),
            "next_token": accounts_data.get("nextToken"),
            "accounts": accounts,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to test accounts endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Amazon Accounts API test failed: {str(e)}"
        )


@router.get("/amazon/dsp-advertisers")
async def test_dsp_advertisers(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    profile_id: Optional[str] = Query(None, description="Specific profile ID to test"),
    count: int = Query(20, ge=1, le=100, description="Number of advertisers to return")
):
    """Test DSP Advertisers API call"""
    validate_admin_key(admin_key)

    try:
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete authentication first."
            )

        access_token = tokens["access_token"]

        # If no profile_id specified, get all DSP advertisers across all profiles
        if profile_id:
            result = await dsp_amc_service.list_dsp_advertisers(
                access_token=access_token,
                profile_id=profile_id,
                count=count
            )

            return {
                "status": "success",
                "endpoint": "GET /dsp/advertisers",
                "profile_id": profile_id,
                "total_results": result.get("totalResults", 0),
                "advertisers_count": len(result.get("response", [])),
                "advertisers": result.get("response", []),
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Get advertisers across all profiles
            all_data = await dsp_amc_service.list_all_account_types(
                access_token=access_token,
                include_regular=False,
                include_dsp=True,
                include_amc=False
            )

            dsp_advertisers = all_data.get("dsp_advertisers", [])

            return {
                "status": "success",
                "endpoint": "GET /dsp/advertisers (all profiles)",
                "profiles_checked": len(all_data.get("advertising_accounts", [])),
                "total_advertisers": len(dsp_advertisers),
                "advertisers": dsp_advertisers[:count],  # Limit to requested count
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        logger.error("Failed to test DSP advertisers endpoint", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DSP Advertisers API test failed: {str(e)}"
        )


@router.get("/amazon/dsp-seats/{advertiser_id}")
async def test_dsp_seats(
    advertiser_id: str,
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    profile_id: Optional[str] = Query(None, description="Profile ID for the advertiser"),
    max_results: int = Query(50, ge=1, le=200, description="Max seats to return"),
    exchange_ids: Optional[List[str]] = Query(None, description="Filter by exchange IDs")
):
    """Test DSP Seats API call"""
    validate_admin_key(admin_key)

    try:
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete authentication first."
            )

        access_token = tokens["access_token"]

        # If no profile_id provided, try to find it from database
        if not profile_id:
            supabase = get_supabase_service_client()
            result = supabase.table("user_accounts").select("profile_id, metadata").eq(
                "amazon_account_id", advertiser_id
            ).eq("account_type", "dsp").limit(1).execute()

            if result.data:
                profile_id = result.data[0].get("profile_id")
                if not profile_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Profile ID required and not found in database for this advertiser"
                    )

        seats_data = await dsp_amc_service.list_advertiser_seats(
            access_token=access_token,
            advertiser_id=advertiser_id,
            profile_id=profile_id,
            max_results=max_results,
            exchange_ids=exchange_ids
        )

        seats = seats_data.get("seats", [])

        return {
            "status": "success",
            "endpoint": f"POST /dsp/v1/seats/advertisers/{advertiser_id}/list",
            "advertiser_id": advertiser_id,
            "profile_id": profile_id,
            "total_seats": len(seats),
            "exchange_ids_filter": exchange_ids,
            "seats": seats,
            "next_token": seats_data.get("nextToken"),
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to test DSP seats endpoint", error=str(e), advertiser_id=advertiser_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DSP Seats API test failed: {str(e)}"
        )


@router.get("/database/accounts")
async def test_database_accounts(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    limit: int = Query(50, ge=1, le=500, description="Max accounts to return")
):
    """Test database accounts table"""
    validate_admin_key(admin_key)

    try:
        supabase = get_supabase_service_client()

        query = supabase.table("user_accounts").select("*")
        if account_type:
            query = query.eq("account_type", account_type)

        result = query.limit(limit).execute()

        accounts = result.data or []

        # Group by account type for summary
        type_summary = {}
        for account in accounts:
            acc_type = account.get("account_type", "unknown")
            if acc_type not in type_summary:
                type_summary[acc_type] = 0
            type_summary[acc_type] += 1

        return {
            "status": "success",
            "table": "user_accounts",
            "total_accounts": len(accounts),
            "account_types": type_summary,
            "filter_applied": account_type,
            "accounts": accounts,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to test database accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database accounts test failed: {str(e)}"
        )


@router.post("/amazon/sync-test")
async def test_sync_accounts(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    include_dsp: bool = Query(True, description="Include DSP advertisers"),
    include_regular: bool = Query(True, description="Include regular accounts"),
    include_amc: bool = Query(False, description="Include AMC instances")
):
    """Test full account sync process"""
    validate_admin_key(admin_key)

    try:
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete authentication first."
            )

        access_token = tokens["access_token"]
        user_id = tokens.get("user_id", "test_user")

        # Get all account types
        all_data = await dsp_amc_service.list_all_account_types(
            access_token=access_token,
            include_regular=include_regular,
            include_dsp=include_dsp,
            include_amc=include_amc
        )

        return {
            "status": "success",
            "operation": "account_sync_test",
            "user_id": user_id,
            "data_retrieved": {
                "advertising_accounts": len(all_data.get("advertising_accounts", [])),
                "dsp_advertisers": len(all_data.get("dsp_advertisers", [])),
                "amc_instances": len(all_data.get("amc_instances", []))
            },
            "full_data": all_data,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to test sync accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account sync test failed: {str(e)}"
        )


@router.post("/database/sync-dsp")
async def test_sync_dsp_to_database(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    user_id: str = Query("test_user", description="User ID to sync for")
):
    """Test syncing DSP advertisers to database with proper field mapping"""
    validate_admin_key(admin_key)

    try:
        tokens = await token_service.get_decrypted_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OAuth tokens found. Complete authentication first."
            )

        # Import sync service
        from app.services.account_sync_service import account_sync_service

        # Get DSP advertisers from API
        access_token = tokens["access_token"]
        all_data = await dsp_amc_service.list_all_account_types(
            access_token=access_token,
            include_regular=False,
            include_dsp=True,
            include_amc=False
        )

        dsp_advertisers = all_data.get("dsp_advertisers", [])

        # Sync each DSP advertiser to database
        synced_count = 0
        created_count = 0
        updated_count = 0
        errors = []

        for advertiser in dsp_advertisers:
            try:
                success, was_created = await account_sync_service._upsert_dsp_advertiser(user_id, advertiser)
                if success:
                    synced_count += 1
                    if was_created:
                        created_count += 1
                    else:
                        updated_count += 1
            except Exception as e:
                errors.append({
                    "advertiser_id": advertiser.get("advertiserId"),
                    "error": str(e)
                })

        return {
            "status": "success",
            "operation": "sync_dsp_to_database",
            "user_id": user_id,
            "api_data": {
                "total_advertisers": len(dsp_advertisers),
                "sample_advertiser": dsp_advertisers[0] if dsp_advertisers else None
            },
            "sync_results": {
                "synced": synced_count,
                "created": created_count,
                "updated": updated_count,
                "errors": len(errors)
            },
            "errors": errors,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to test sync accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account sync test failed: {str(e)}"
        )