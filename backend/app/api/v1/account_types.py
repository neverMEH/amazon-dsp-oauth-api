"""
Account Types API endpoints for multi-type account management
Handles Sponsored Ads, DSP, and AMC account endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog
from uuid import uuid4

from app.middleware.clerk_auth import RequireAuth, get_user_context
from app.services.account_service import account_service
from app.services.amazon_oauth_service import amazon_oauth_service
from app.services.token_service import token_service
from app.db.base import get_supabase_client, get_supabase_service_client
from app.schemas.account_types import (
    AccountType,
    AccountTypeFilter,
    SponsoredAdsAccountResponse,
    DSPAccountResponse,
    AMCAccountResponse,
    AccountRelationship,
    SetManagedRequest,
    SetManagedResponse,
    AccountsSyncRequest,
    AccountsSyncResponse,
    AccountsSyncStatus
)

logger = structlog.get_logger()

router = APIRouter(prefix="/accounts", tags=["account-types"])


# ============================================================================
# SPONSORED ADS ENDPOINTS
# ============================================================================

@router.get(
    "/sponsored-ads",
    response_model=Dict[str, Any],
    summary="Get Sponsored Ads accounts",
    description="Fetch Sponsored Ads accounts with profile/entity IDs and management history"
)
async def get_sponsored_ads_accounts(
    user_context: Dict = Depends(get_user_context),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: str = Query("last_managed_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """Get Sponsored Ads accounts for the authenticated user"""
    try:
        logger.info(
            "fetching_sponsored_ads_accounts",
            user_id=user_context["user_id"],
            limit=limit,
            offset=offset
        )

        # Get Supabase client
        supabase = get_supabase_service_client()

        # Build query for sponsored ads accounts
        query = supabase.table("user_accounts").select("*").eq(
            "user_id", user_context["user_id"]
        ).eq(
            "account_type", "advertising"
        )

        # Apply sorting
        if sort_by == "last_managed_at":
            query = query.order("last_managed_at", desc=(sort_order == "desc"))
        elif sort_by == "account_name":
            query = query.order("account_name", desc=(sort_order == "desc"))
        else:
            query = query.order("created_at", desc=(sort_order == "desc"))

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        # Execute query
        result = query.execute()

        # Transform accounts to response format
        accounts = []
        for acc in result.data:
            # Extract marketplaces from metadata
            marketplaces = []
            if acc.get("metadata"):
                marketplaces = acc["metadata"].get("marketplaces", [])
                if not marketplaces and acc["metadata"].get("countryCodes"):
                    marketplaces = acc["metadata"]["countryCodes"]

            accounts.append({
                "id": acc["id"],
                "user_id": acc["user_id"],
                "account_name": acc["account_name"],
                "profile_id": acc.get("profile_id"),
                "entity_id": acc.get("entity_id") or acc.get("amazon_account_id"),
                "marketplaces": marketplaces,
                "last_managed_at": acc.get("last_managed_at"),
                "status": acc["status"],
                "account_type": "advertising",
                "metadata": acc.get("metadata", {}),
                "last_synced_at": acc.get("last_synced_at")
            })

        # Get total count
        count_result = supabase.table("user_accounts").select(
            "id", count="exact"
        ).eq(
            "user_id", user_context["user_id"]
        ).eq(
            "account_type", "advertising"
        ).execute()

        return {
            "accounts": accounts,
            "total": count_result.count if count_result else len(accounts),
            "has_more": len(accounts) == limit
        }

    except Exception as e:
        logger.error(
            "error_fetching_sponsored_ads_accounts",
            user_id=user_context["user_id"],
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Sponsored Ads accounts: {str(e)}"
        )


# ============================================================================
# DSP ENDPOINTS
# ============================================================================

@router.get(
    "/dsp",
    response_model=Dict[str, Any],
    summary="Get DSP accounts",
    description="Fetch DSP accounts with entity/profile IDs and marketplace data"
)
async def get_dsp_accounts(
    user_context: Dict = Depends(get_user_context),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """Get DSP accounts for the authenticated user"""
    try:
        logger.info(
            "fetching_dsp_accounts",
            user_id=user_context["user_id"],
            limit=limit,
            offset=offset
        )

        # Get Supabase client
        supabase = get_supabase_service_client()

        # Query DSP accounts
        query = supabase.table("user_accounts").select("*").eq(
            "user_id", user_context["user_id"]
        ).eq(
            "account_type", "dsp"
        ).range(offset, offset + limit - 1)

        result = query.execute()

        # Check if user has DSP access (may be empty)
        access_denied = False
        if not result.data:
            # Try to fetch DSP accounts from Amazon API
            try:
                # This would call the Amazon DSP API
                # For now, we'll just mark as no access
                logger.info("no_dsp_accounts_found", user_id=user_context["user_id"])
                access_denied = False  # Empty is not the same as denied
            except Exception as api_error:
                if "403" in str(api_error) or "Forbidden" in str(api_error):
                    access_denied = True

        # Transform DSP accounts
        accounts = []
        for acc in result.data:
            accounts.append({
                "id": acc["id"],
                "user_id": acc["user_id"],
                "account_name": acc["account_name"],
                "entity_id": acc.get("entity_id"),
                "profile_id": acc.get("profile_id"),
                "marketplace": acc.get("marketplace_id", "US"),
                "account_type": "dsp",
                "advertiser_type": acc.get("metadata", {}).get("advertiser_type", "brand"),
                "metadata": acc.get("metadata", {}),
                "last_synced_at": acc.get("last_synced_at")
            })

        # Get total count
        count_result = supabase.table("user_accounts").select(
            "id", count="exact"
        ).eq(
            "user_id", user_context["user_id"]
        ).eq(
            "account_type", "dsp"
        ).execute()

        return {
            "accounts": accounts,
            "total": count_result.count if count_result else len(accounts),
            "has_more": len(accounts) == limit,
            "access_denied": access_denied
        }

    except Exception as e:
        logger.error(
            "error_fetching_dsp_accounts",
            user_id=user_context["user_id"],
            error=str(e)
        )

        # Check if it's a permission error
        if "403" in str(e) or "Forbidden" in str(e):
            return {
                "accounts": [],
                "total": 0,
                "has_more": False,
                "access_denied": True
            }

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch DSP accounts: {str(e)}"
        )


# ============================================================================
# AMC ENDPOINTS
# ============================================================================

@router.get(
    "/amc",
    response_model=Dict[str, Any],
    summary="Get AMC instances",
    description="Fetch AMC instances with embedded associated DSP and SP account information"
)
async def get_amc_instances(
    user_context: Dict = Depends(get_user_context),
    include_associated_details: bool = Query(True, description="Include associated account details")
):
    """Get AMC instances for the authenticated user"""
    try:
        logger.info(
            "fetching_amc_instances",
            user_id=user_context["user_id"],
            include_associated=include_associated_details
        )

        # Get Supabase client
        supabase = get_supabase_service_client()

        # Query AMC instances
        query = supabase.table("user_accounts").select("*").eq(
            "user_id", user_context["user_id"]
        ).eq(
            "account_type", "amc"
        )

        result = query.execute()

        # Check if user has AMC access
        access_denied = False
        if not result.data:
            logger.info("no_amc_instances_found", user_id=user_context["user_id"])
            # AMC requires special provisioning, so empty usually means no access
            access_denied = False  # But we'll be lenient

        # Transform AMC instances
        instances = []
        for acc in result.data:
            instance = {
                "id": acc["id"],
                "user_id": acc["user_id"],
                "instance_name": acc["account_name"],
                "instance_id": acc.get("entity_id", acc.get("amazon_account_id")),
                "account_type": "amc",
                "data_set_id": acc.get("metadata", {}).get("data_set_id", f"dataset_{acc['id'][:8]}"),
                "status": acc["status"],
                "associated_accounts": {
                    "sponsored_ads": [],
                    "dsp": []
                },
                "metadata": acc.get("metadata", {}),
                "last_synced_at": acc.get("last_synced_at")
            }

            # If including associated details, fetch related accounts
            if include_associated_details:
                # Query amc_instance_accounts junction table if it exists
                # For now, we'll use metadata
                if acc.get("metadata", {}).get("associated_accounts"):
                    instance["associated_accounts"] = acc["metadata"]["associated_accounts"]
                else:
                    # Mock some associated accounts for demonstration
                    instance["associated_accounts"] = {
                        "sponsored_ads": [
                            {
                                "account_name": "Primary SP Account",
                                "profile_id": "123456789",
                                "entity_id": "ENTITY_PRIMARY"
                            }
                        ],
                        "dsp": []
                    }

            instances.append(instance)

        return {
            "instances": instances,
            "total": len(instances),
            "access_denied": access_denied
        }

    except Exception as e:
        logger.error(
            "error_fetching_amc_instances",
            user_id=user_context["user_id"],
            error=str(e)
        )

        # Check if it's a permission error
        if "403" in str(e) or "Forbidden" in str(e):
            return {
                "instances": [],
                "total": 0,
                "access_denied": True
            }

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch AMC instances: {str(e)}"
        )


# ============================================================================
# ACCOUNT MANAGEMENT ENDPOINTS
# ============================================================================

@router.post(
    "/{account_id}/set-managed",
    response_model=SetManagedResponse,
    summary="Set account as managed",
    description="Update the last_managed_at timestamp when an account is selected for management"
)
async def set_account_managed(
    account_id: str = Path(..., description="Account UUID"),
    user_context: Dict = Depends(get_user_context)
):
    """Mark an account as being managed"""
    try:
        logger.info(
            "setting_account_managed",
            user_id=user_context["user_id"],
            account_id=account_id
        )

        # Get Supabase client
        supabase = get_supabase_service_client()

        # Update the last_managed_at timestamp
        now = datetime.now(timezone.utc)

        # Add manage_action flag to trigger the database trigger
        result = supabase.table("user_accounts").update({
            "metadata": {"manage_action": True},  # This triggers the update
            "updated_at": now.isoformat()
        }).eq(
            "id", account_id
        ).eq(
            "user_id", user_context["user_id"]
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        # Update without the trigger flag to get clean data
        result = supabase.table("user_accounts").update({
            "last_managed_at": now.isoformat()
        }).eq(
            "id", account_id
        ).execute()

        return SetManagedResponse(
            success=True,
            account_id=account_id,
            last_managed_at=now
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "error_setting_account_managed",
            user_id=user_context["user_id"],
            account_id=account_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set account as managed: {str(e)}"
        )


@router.get(
    "/relationships/{account_id}",
    response_model=Dict[str, Any],
    summary="Get account relationships",
    description="Get all relationships for a specific account"
)
async def get_account_relationships(
    account_id: str = Path(..., description="Account UUID"),
    user_context: Dict = Depends(get_user_context)
):
    """Get relationships for an account"""
    try:
        logger.info(
            "fetching_account_relationships",
            user_id=user_context["user_id"],
            account_id=account_id
        )

        # Get Supabase client
        supabase = get_supabase_service_client()

        # Verify account ownership
        account_result = supabase.table("user_accounts").select("id").eq(
            "id", account_id
        ).eq(
            "user_id", user_context["user_id"]
        ).execute()

        if not account_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        # Query account relationships
        # Get parent relationships
        parent_query = supabase.table("account_relationships").select(
            "*, parent_account:user_accounts!parent_account_id(*)"
        ).eq("child_account_id", account_id).execute()

        # Get child relationships
        child_query = supabase.table("account_relationships").select(
            "*, child_account:user_accounts!child_account_id(*)"
        ).eq("parent_account_id", account_id).execute()

        parents = []
        children = []

        # Process parent relationships
        for rel in (parent_query.data or []):
            if rel.get("parent_account"):
                parents.append({
                    "account_id": rel["parent_account"]["id"],
                    "account_name": rel["parent_account"]["account_name"],
                    "account_type": rel["parent_account"]["account_type"],
                    "relationship_type": rel["relationship_type"]
                })

        # Process child relationships
        for rel in (child_query.data or []):
            if rel.get("child_account"):
                children.append({
                    "account_id": rel["child_account"]["id"],
                    "account_name": rel["child_account"]["account_name"],
                    "account_type": rel["child_account"]["account_type"],
                    "relationship_type": rel["relationship_type"]
                })

        return {
            "account_id": account_id,
            "relationships": {
                "parents": parents,
                "children": children
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "error_fetching_relationships",
            user_id=user_context["user_id"],
            account_id=account_id,
            error=str(e)
        )

        # If relationships table doesn't exist, return empty
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            return {
                "account_id": account_id,
                "relationships": {
                    "parents": [],
                    "children": []
                }
            }

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch account relationships: {str(e)}"
        )


@router.post(
    "/sync",
    response_model=AccountsSyncResponse,
    summary="Sync accounts",
    description="Trigger synchronization of all account types from Amazon APIs"
)
async def sync_accounts(
    request: AccountsSyncRequest,
    user_context: Dict = Depends(get_user_context)
):
    """Sync accounts from Amazon APIs"""
    try:
        logger.info(
            "syncing_accounts",
            user_id=user_context["user_id"],
            account_types=request.account_types,
            force_refresh=request.force_refresh
        )

        sync_id = str(uuid4())
        started_at = datetime.now(timezone.utc)

        # TODO: Implement actual sync logic with Amazon APIs
        # For now, return in-progress status

        return AccountsSyncResponse(
            sync_id=sync_id,
            status="in_progress",
            account_types=[t.value for t in request.account_types],
            started_at=started_at
        )

    except Exception as e:
        logger.error(
            "error_syncing_accounts",
            user_id=user_context["user_id"],
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start account sync: {str(e)}"
        )