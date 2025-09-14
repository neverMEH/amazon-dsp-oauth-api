"""
Debug endpoints for troubleshooting authentication and database issues
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
import structlog

from app.middleware.clerk_auth import RequireAuth, get_user_context
from app.services.user_service import UserService
from app.db.base import get_supabase_client

logger = structlog.get_logger()
router = APIRouter(prefix="/debug", tags=["Debug"])

user_service = UserService()


@router.get("/auth-test")
async def test_authentication(
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Simple authentication test endpoint

    Returns:
        Basic auth info and user context
    """
    try:
        user_context = get_user_context(current_user)

        return {
            "authenticated": True,
            "clerk_user_id": user_context.get("clerk_user_id"),
            "email": user_context.get("email"),
            "user_id": user_context.get("user_id"),
            "current_user_keys": list(current_user.keys()),
            "timestamp": logger._context.get("timestamp", "unknown")
        }

    except Exception as e:
        logger.error("Debug auth test failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auth test failed: {str(e)}"
        )


@router.get("/db-test")
async def test_database():
    """
    Simple database connection test

    Returns:
        Database connection status
    """
    try:
        supabase = get_supabase_client()

        # Try a simple query
        result = supabase.table("users").select("id").limit(1).execute()

        return {
            "database_connected": True,
            "query_successful": True,
            "user_count_sample": len(result.data) if result.data else 0,
            "supabase_url": supabase.url if hasattr(supabase, 'url') else "unknown"
        }

    except Exception as e:
        logger.error("Database test failed", error=str(e))
        return {
            "database_connected": False,
            "error": str(e),
            "query_successful": False
        }


@router.get("/user-test")
async def test_user_operations(
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Test user creation and retrieval operations

    Returns:
        User operation status
    """
    try:
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]

        # Try to get user from database
        user = await user_service.get_user_by_clerk_id(clerk_user_id)

        return {
            "user_found": user is not None,
            "clerk_user_id": clerk_user_id,
            "database_user_id": user.id if user else None,
            "user_email": user.email if user else None,
            "user_created_at": str(user.created_at) if user else None
        }

    except Exception as e:
        logger.error("User test failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User test failed: {str(e)}"
        )


@router.get("/settings-table-test")
async def test_settings_table():
    """
    Test user_settings table access

    Returns:
        Settings table status
    """
    try:
        supabase = get_supabase_client()

        # Try to query the settings table
        result = supabase.table("user_settings").select("id").limit(1).execute()

        return {
            "table_accessible": True,
            "query_successful": True,
            "sample_record_count": len(result.data) if result.data else 0,
            "table_exists": True
        }

    except Exception as e:
        logger.error("Settings table test failed", error=str(e))
        return {
            "table_accessible": False,
            "table_exists": "unknown",
            "error": str(e),
            "query_successful": False
        }


@router.get("/full-pipeline-test")
async def test_full_pipeline(
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Test the full settings endpoint pipeline

    Returns:
        Step-by-step pipeline results
    """
    results = {
        "steps": {},
        "overall_success": False
    }

    try:
        # Step 1: Authentication
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]
        results["steps"]["1_authentication"] = {
            "success": True,
            "clerk_user_id": clerk_user_id
        }

        # Step 2: User lookup
        user = await user_service.get_user_by_clerk_id(clerk_user_id)
        results["steps"]["2_user_lookup"] = {
            "success": True,
            "user_found": user is not None,
            "user_id": user.id if user else None
        }

        # Step 3: Database connection
        supabase = get_supabase_client()
        results["steps"]["3_database_connection"] = {
            "success": True,
            "connected": True
        }

        # Step 4: Settings table query (if user exists)
        if user:
            try:
                response = supabase.table("user_settings").select("*").eq("user_id", user.id).execute()
                results["steps"]["4_settings_query"] = {
                    "success": True,
                    "settings_found": bool(response.data),
                    "record_count": len(response.data) if response.data else 0
                }
            except Exception as e:
                results["steps"]["4_settings_query"] = {
                    "success": False,
                    "error": str(e)
                }
        else:
            results["steps"]["4_settings_query"] = {
                "success": False,
                "error": "No user found to query settings for"
            }

        # Check overall success
        all_successful = all(
            step.get("success", False)
            for step in results["steps"].values()
        )
        results["overall_success"] = all_successful

        return results

    except Exception as e:
        logger.error("Full pipeline test failed", error=str(e))
        results["steps"]["error"] = {
            "success": False,
            "error": str(e)
        }
        return results