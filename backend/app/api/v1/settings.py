"""
User settings and preferences API endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import structlog
import json

from app.middleware.clerk_auth import RequireAuth, get_user_context
from app.services.user_service import UserService
from app.schemas.settings import (
    UserSettingsResponse,
    UserSettingsUpdate,
    UserPreferences,
    DefaultSettings
)
from app.db.base import get_supabase_client, get_supabase_service_client

logger = structlog.get_logger()
router = APIRouter(prefix="/settings", tags=["User Settings"])

# Initialize services
user_service = UserService()


@router.get("", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Get current user's settings and preferences

    Returns:
        User settings including preferences, defaults, and configuration
    """
    try:
        logger.info("Starting get_user_settings", current_user_keys=list(current_user.keys()) if current_user else None)

        user_context = get_user_context(current_user)
        logger.info("User context retrieved", user_context_keys=list(user_context.keys()) if user_context else None)

        clerk_user_id = user_context.get("clerk_user_id")
        if not clerk_user_id:
            logger.error("No clerk_user_id in user_context", user_context=user_context)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user context: missing clerk_user_id"
            )

        # Get user from database
        logger.info("Querying user from database", clerk_user_id=clerk_user_id)
        user = await user_service.get_user_by_clerk_id(clerk_user_id)

        if not user:
            # Try to create user if they don't exist
            logger.warning(f"User not found in database, attempting to create: {clerk_user_id}")
            try:
                from app.schemas.user import UserCreate
                user_create = UserCreate(
                    clerk_user_id=clerk_user_id,
                    email=user_context.get("email", f"{clerk_user_id}@clerk.user"),
                    first_name=user_context.get("first_name", ""),
                    last_name=user_context.get("last_name", ""),
                    profile_image_url=user_context.get("profile_image")
                )
                logger.info("Creating new user", user_create_data=user_create.dict())
                user = await user_service.create_user(user_create)

                if user:
                    logger.info("User created successfully", user_id=user.id)
                else:
                    logger.error("User creation returned None")

            except Exception as create_error:
                logger.error("Error creating user", error=str(create_error), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create user: {str(create_error)}"
                )

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Failed to create user in database"
                )
        else:
            logger.info("User found in database", user_id=user.id)

        # Get settings from database or return defaults
        logger.info("Getting settings from database", user_id=user.id)
        # Use service role client to bypass RLS policies
        supabase = get_supabase_service_client()

        # Query user_settings table
        try:
            logger.info("Querying user_settings table", user_id=user.id)
            response = supabase.table("user_settings").select("*").eq("user_id", user.id).single().execute()
            logger.info("Settings query completed", has_data=bool(response.data))
        except Exception as e:
            logger.info("No settings found, creating default response", error=str(e))
            # Handle case where no settings exist yet
            response = type('obj', (object,), {'data': None})()
        
        if response.data:
            settings_data = response.data
            preferences = json.loads(settings_data.get("preferences", "{}"))
        else:
            # Return default settings if none exist
            preferences = get_default_preferences()
            
            # Create default settings record
            default_settings = {
                "user_id": user.id,
                "preferences": json.dumps(preferences),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("user_settings").insert(default_settings).execute()
            settings_data = default_settings
        
        return UserSettingsResponse(
            user_id=user.id,
            preferences=UserPreferences(**preferences),
            updated_at=settings_data.get("updated_at"),
            created_at=settings_data.get("created_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user settings"
        )


@router.patch("", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Update user's settings and preferences
    
    Args:
        settings_update: Partial update of user preferences
        
    Returns:
        Updated user settings
    """
    try:
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]

        # Get user from database
        user = await user_service.get_user_by_clerk_id(clerk_user_id)
        if not user:
            # Try to create user if they don't exist
            logger.warning(f"User not found in database, attempting to create: {clerk_user_id}")
            from app.schemas.user import UserCreate
            user_create = UserCreate(
                clerk_user_id=clerk_user_id,
                email=user_context.get("email", f"{clerk_user_id}@clerk.user"),
                first_name=user_context.get("first_name", ""),
                last_name=user_context.get("last_name", ""),
                profile_image_url=user_context.get("profile_image")
            )
            user = await user_service.create_user(user_create)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Failed to create user in database"
                )
        
        # Use service role client to bypass RLS policies
        supabase = get_supabase_service_client()
        
        # Get existing settings
        try:
            response = supabase.table("user_settings").select("*").eq("user_id", user.id).single().execute()
        except Exception as e:
            # Handle case where no settings exist yet
            response = type('obj', (object,), {'data': None})()
        
        if response.data:
            existing_preferences = json.loads(response.data.get("preferences", "{}"))
        else:
            existing_preferences = get_default_preferences()
        
        # Merge with updates (only update provided fields)
        if settings_update.preferences:
            update_dict = settings_update.preferences.dict(exclude_unset=True)
            existing_preferences.update(update_dict)
        
        # Validate preferences
        if not validate_preferences(existing_preferences):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid preference values"
            )
        
        # Update in database
        updated_settings = {
            "preferences": json.dumps(existing_preferences),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if response.data:
            # Update existing record
            result = supabase.table("user_settings").update(updated_settings).eq("user_id", user.id).execute()
        else:
            # Create new record
            updated_settings["user_id"] = user.id
            updated_settings["created_at"] = datetime.now(timezone.utc).isoformat()
            result = supabase.table("user_settings").insert(updated_settings).execute()
        
        settings_data = result.data[0] if result.data else updated_settings
        
        return UserSettingsResponse(
            user_id=user.id,
            preferences=UserPreferences(**existing_preferences),
            updated_at=settings_data.get("updated_at"),
            created_at=settings_data.get("created_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user settings"
        )


@router.post("/reset", response_model=UserSettingsResponse)
async def reset_user_settings(
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Reset user settings to defaults
    
    Returns:
        Default user settings
    """
    try:
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]

        # Get user from database
        user = await user_service.get_user_by_clerk_id(clerk_user_id)
        if not user:
            # Try to create user if they don't exist
            logger.warning(f"User not found in database, attempting to create: {clerk_user_id}")
            from app.schemas.user import UserCreate
            user_create = UserCreate(
                clerk_user_id=clerk_user_id,
                email=user_context.get("email", f"{clerk_user_id}@clerk.user"),
                first_name=user_context.get("first_name", ""),
                last_name=user_context.get("last_name", ""),
                profile_image_url=user_context.get("profile_image")
            )
            user = await user_service.create_user(user_create)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Failed to create user in database"
                )
        
        # Get default preferences
        default_prefs = get_default_preferences()
        
        # Update in database
        # Use service role client to bypass RLS policies
        supabase = get_supabase_service_client()
        
        updated_settings = {
            "preferences": json.dumps(default_prefs),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if settings exist
        try:
            response = supabase.table("user_settings").select("*").eq("user_id", user.id).single().execute()
        except Exception as e:
            # Handle case where no settings exist yet
            response = type('obj', (object,), {'data': None})()
        
        if response.data:
            # Update existing
            result = supabase.table("user_settings").update(updated_settings).eq("user_id", user.id).execute()
        else:
            # Create new
            updated_settings["user_id"] = user.id
            updated_settings["created_at"] = datetime.now(timezone.utc).isoformat()
            result = supabase.table("user_settings").insert(updated_settings).execute()
        
        settings_data = result.data[0] if result.data else updated_settings
        
        return UserSettingsResponse(
            user_id=user.id,
            preferences=UserPreferences(**default_prefs),
            updated_at=settings_data.get("updated_at"),
            created_at=settings_data.get("created_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting user settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset user settings"
        )


@router.get("/defaults", response_model=DefaultSettings)
async def get_default_settings():
    """
    Get default settings configuration
    
    Returns:
        Default settings and available options
    """
    return DefaultSettings(
        preferences=UserPreferences(**get_default_preferences()),
        available_timezones=get_available_timezones(),
        available_layouts=["grid", "list", "compact"],
        available_themes=["light", "dark", "system"]
    )


def get_default_preferences() -> dict:
    """Get default user preferences"""
    return {
        "notifications_enabled": True,
        "email_notifications": True,
        "auto_refresh_tokens": True,
        "refresh_interval_hours": 6,
        "default_account_id": None,
        "dashboard_layout": "grid",
        "items_per_page": 20,
        "timezone": "UTC",
        "date_format": "MM/DD/YYYY",
        "time_format": "12h",
        "theme": "system",
        "show_expired_accounts": True,
        "show_disconnected_accounts": False,
        "auto_expand_details": False,
        "enable_keyboard_shortcuts": True
    }


def validate_preferences(preferences: dict) -> bool:
    """Validate user preferences"""
    try:
        # Validate dashboard layout
        if "dashboard_layout" in preferences:
            if preferences["dashboard_layout"] not in ["grid", "list", "compact"]:
                return False
        
        # Validate timezone
        if "timezone" in preferences:
            if preferences["timezone"] not in get_available_timezones():
                return False
        
        # Validate theme
        if "theme" in preferences:
            if preferences["theme"] not in ["light", "dark", "system"]:
                return False
        
        # Validate date format
        if "date_format" in preferences:
            if preferences["date_format"] not in ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]:
                return False
        
        # Validate time format
        if "time_format" in preferences:
            if preferences["time_format"] not in ["12h", "24h"]:
                return False
        
        # Validate numeric values
        if "refresh_interval_hours" in preferences:
            if not 1 <= preferences["refresh_interval_hours"] <= 24:
                return False
        
        if "items_per_page" in preferences:
            if not 5 <= preferences["items_per_page"] <= 100:
                return False
        
        return True
        
    except Exception:
        return False


def get_available_timezones() -> list:
    """Get list of available timezones"""
    return [
        "UTC",
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Toronto",
        "America/Vancouver",
        "America/Mexico_City",
        "America/Sao_Paulo",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Madrid",
        "Europe/Rome",
        "Europe/Moscow",
        "Europe/Istanbul",
        "Asia/Dubai",
        "Asia/Mumbai",
        "Asia/Bangkok",
        "Asia/Singapore",
        "Asia/Hong_Kong",
        "Asia/Shanghai",
        "Asia/Tokyo",
        "Asia/Seoul",
        "Australia/Sydney",
        "Australia/Melbourne",
        "Pacific/Auckland"
    ]