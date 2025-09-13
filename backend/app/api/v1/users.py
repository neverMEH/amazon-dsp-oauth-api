"""
User management endpoints with Clerk integration
"""
from fastapi import APIRouter, HTTPException, status, Request, Depends
from typing import Dict, Any, List
import structlog

from app.middleware.clerk_auth import RequireAuth, OptionalAuth, get_user_context
from app.services.user_service import UserService, AmazonAccountService
from app.services.clerk_service import ClerkService
from app.schemas.user import UserResponse, UserUpdate, UserWithAccounts
from app.schemas.amazon_account import AmazonAccountResponse

logger = structlog.get_logger()
router = APIRouter()

# Initialize services
user_service = UserService()
account_service = AmazonAccountService()
clerk_service = ClerkService()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    request: Request,
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Get current user's profile
    
    Returns:
        Current user's profile information
    """
    try:
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]
        
        # Get user from database
        user = await user_service.get_user_by_clerk_id(clerk_user_id)
        
        if not user:
            # Sync user from Clerk if not found in database
            await clerk_service.sync_user_with_database(clerk_user_id)
            user = await user_service.get_user_by_clerk_id(clerk_user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
        
        return UserResponse(
            id=user.id,
            clerk_user_id=user.clerk_user_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    request: Request,
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Update current user's profile
    
    Args:
        user_update: Fields to update
        
    Returns:
        Updated user profile
    """
    try:
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]
        
        # Get user from database
        user = await user_service.get_user_by_clerk_id(clerk_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user
        updated_user = await user_service.update_user(user.id, user_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user"
            )
        
        return UserResponse(
            id=updated_user.id,
            clerk_user_id=updated_user.clerk_user_id,
            email=updated_user.email,
            first_name=updated_user.first_name,
            last_name=updated_user.last_name,
            profile_image_url=updated_user.profile_image_url,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            last_login_at=updated_user.last_login_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me/accounts", response_model=List[AmazonAccountResponse])
async def get_current_user_accounts(
    request: Request,
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Get current user's connected Amazon accounts
    
    Returns:
        List of connected Amazon accounts
    """
    try:
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]
        
        # Get user from database
        user = await user_service.get_user_by_clerk_id(clerk_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user's Amazon accounts
        accounts = await account_service.get_user_accounts(user.id)
        
        return [
            AmazonAccountResponse(
                id=account.id,
                user_id=account.user_id,
                account_name=account.account_name,
                amazon_account_id=account.amazon_account_id,
                marketplace_id=account.marketplace_id,
                account_type=account.account_type,
                is_default=account.is_default,
                status=account.status,
                connected_at=account.connected_at,
                last_synced_at=account.last_synced_at,
                metadata=account.metadata
            )
            for account in accounts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me/full", response_model=UserWithAccounts)
async def get_current_user_with_accounts(
    request: Request,
    current_user: Dict[str, Any] = Depends(RequireAuth)
):
    """
    Get current user's profile with connected accounts
    
    Returns:
        User profile with connected Amazon accounts
    """
    try:
        user_context = get_user_context(current_user)
        clerk_user_id = user_context["clerk_user_id"]
        
        # Get user from database
        user = await user_service.get_user_by_clerk_id(clerk_user_id)
        
        if not user:
            # Sync user from Clerk if not found
            await clerk_service.sync_user_with_database(clerk_user_id)
            user = await user_service.get_user_by_clerk_id(clerk_user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
        
        # Get user's Amazon accounts
        accounts = await account_service.get_user_accounts(user.id)
        
        return UserWithAccounts(
            id=user.id,
            clerk_user_id=user.clerk_user_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            amazon_accounts=[
                AmazonAccountResponse(
                    id=account.id,
                    user_id=account.user_id,
                    account_name=account.account_name,
                    amazon_account_id=account.amazon_account_id,
                    marketplace_id=account.marketplace_id,
                    account_type=account.account_type,
                    is_default=account.is_default,
                    status=account.status,
                    connected_at=account.connected_at,
                    last_synced_at=account.last_synced_at,
                    metadata=account.metadata
                )
                for account in accounts
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user with accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/session", response_model=Dict[str, Any])
async def get_session_info(
    request: Request,
    current_user: Dict[str, Any] = Depends(OptionalAuth)
):
    """
    Get current session information
    
    Returns:
        Session information and authentication status
    """
    try:
        if current_user:
            user_context = get_user_context(current_user)
            
            return {
                "authenticated": True,
                "user": user_context,
                "session_id": user_context.get("session_id"),
                "auth_time": user_context.get("auth_time")
            }
        else:
            return {
                "authenticated": False,
                "user": None,
                "session_id": None,
                "auth_time": None
            }
            
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        return {
            "authenticated": False,
            "user": None,
            "session_id": None,
            "auth_time": None,
            "error": "Session check failed"
        }