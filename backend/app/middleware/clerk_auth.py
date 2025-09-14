"""
Clerk authentication middleware
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Callable
import structlog

from app.services.clerk_service import ClerkService
from app.services.user_service import UserService
from app.schemas.user import UserCreate

logger = structlog.get_logger()
security = HTTPBearer(auto_error=False)


class ClerkAuthMiddleware:
    """Middleware for Clerk authentication"""
    
    def __init__(self):
        """Initialize middleware"""
        self.clerk_service = ClerkService()
        self.user_service = UserService()
    
    async def authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Authenticate request using Clerk session token

        Args:
            request: FastAPI request object

        Returns:
            User data if authenticated, None otherwise
        """
        try:
            # Try to get token from Authorization header
            auth_header = request.headers.get("Authorization")
            token = None

            logger.debug(f"Auth header present: {bool(auth_header)}")

            if auth_header:
                token = self.extract_token_from_header(auth_header)
                logger.debug(f"Token extracted from header: {bool(token)}")

            # If no token in header, try session cookie
            if not token:
                token = request.cookies.get("__session")
                logger.debug(f"Token from cookie: {bool(token)}")

            if not token:
                logger.debug("No token found in request")
                return None

            # Log token prefix for debugging (first 20 chars)
            logger.debug(f"Token prefix: {token[:20]}..." if len(token) > 20 else f"Token: {token}")

            # Verify token with Clerk
            clerk_data = await self.clerk_service.verify_session_token(token)

            if clerk_data:
                logger.info(f"User authenticated: {clerk_data.get('sub')}")

                # Ensure user exists in our database
                user_data = await self.ensure_user_exists(clerk_data)

                # Combine Clerk data with user data
                if user_data:
                    return {
                        **clerk_data,
                        "user_id": user_data.get("id"),  # Add database user ID
                        "email": user_data.get("email"),
                        "db_user": user_data  # Include full database user data
                    }
                else:
                    # If we couldn't create/find user, still return Clerk data
                    return clerk_data
            else:
                logger.warning("Token verification failed")

            return None

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            return None
    
    async def ensure_user_exists(self, clerk_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ensure user exists in database, create if not

        Args:
            clerk_data: Verified Clerk token data

        Returns:
            User data from database or None
        """
        try:
            clerk_user_id = clerk_data.get("sub")
            if not clerk_user_id:
                logger.error("No sub (user ID) in Clerk data")
                return None

            # Try to get existing user
            user = await self.user_service.get_user_by_clerk_id(clerk_user_id)

            if user:
                # Update last login
                await self.user_service.update_last_login(clerk_user_id)
                return user.to_dict()

            # User doesn't exist, create them
            logger.info(f"Creating new user for Clerk ID: {clerk_user_id}")

            # Get user details from Clerk if needed
            # For now, use data from the token
            user_create = UserCreate(
                clerk_user_id=clerk_user_id,
                email=clerk_data.get("email") or f"{clerk_user_id}@clerk.user",
                first_name=clerk_data.get("first_name") or "",
                last_name=clerk_data.get("last_name") or "",
                profile_image_url=clerk_data.get("image_url")
            )

            new_user = await self.user_service.create_user(user_create)
            return new_user.to_dict() if new_user else None

        except Exception as e:
            logger.error(f"Error ensuring user exists: {str(e)}", exc_info=True)
            return None

    def extract_token_from_header(self, auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header
        
        Args:
            auth_header: Authorization header value
            
        Returns:
            Token if found, None otherwise
        """
        if not auth_header:
            return None
        
        # Handle "Bearer token" format
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Handle just the token
        return auth_header if auth_header else None
    
    async def get_current_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Get current authenticated user
        
        Args:
            request: FastAPI request object
            
        Returns:
            Current user data or None
        """
        return await self.authenticate_request(request)


# Create middleware instance
clerk_middleware = ClerkAuthMiddleware()


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Dependency to get current authenticated user
    
    Args:
        request: FastAPI request
        
    Returns:
        Current user data or None
    """
    return await clerk_middleware.get_current_user(request)


async def get_current_user_required(request: Request) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user (required)
    
    Args:
        request: FastAPI request
        
    Returns:
        Current user data
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user = await clerk_middleware.get_current_user(request)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for endpoint
    
    Args:
        func: Endpoint function to protect
        
    Returns:
        Protected function
    """
    async def wrapper(request: Request, *args, **kwargs):
        user = await get_current_user_required(request)
        
        # Add current user to kwargs
        kwargs['current_user'] = user
        
        return await func(request, *args, **kwargs)
    
    return wrapper


class ClerkUserDependency:
    """Dependency class for Clerk user authentication"""
    
    def __init__(self, required: bool = True):
        """
        Initialize dependency
        
        Args:
            required: Whether authentication is required
        """
        self.required = required
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Get authenticated user
        
        Args:
            request: FastAPI request
            
        Returns:
            User data if authenticated
            
        Raises:
            HTTPException: If authentication required but user not authenticated
        """
        user = await clerk_middleware.get_current_user(request)
        
        if self.required and not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user


# Common dependency instances
RequireAuth = ClerkUserDependency(required=True)
OptionalAuth = ClerkUserDependency(required=False)


async def verify_clerk_webhook(request: Request) -> bool:
    """
    Verify Clerk webhook signature
    
    Args:
        request: FastAPI request with webhook payload
        
    Returns:
        True if signature is valid
        
    Raises:
        HTTPException: If signature verification fails
    """
    try:
        # Get raw body
        body = await request.body()
        headers = dict(request.headers)
        
        # Initialize webhook handler
        from app.services.clerk_service import ClerkWebhookHandler
        webhook_handler = ClerkWebhookHandler()
        
        # Verify signature
        if not webhook_handler.verify_webhook(body.decode(), headers):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Webhook verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook verification failed"
        )


def get_user_context(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract useful context from user data for application use
    
    Args:
        user_data: Raw user data from Clerk
        
    Returns:
        User context for application
    """
    return {
        "user_id": user_data.get("sub"),
        "clerk_user_id": user_data.get("sub"),
        "email": user_data.get("email"),
        "email_verified": user_data.get("email_verified", False),
        "first_name": user_data.get("given_name"),
        "last_name": user_data.get("family_name"),
        "full_name": user_data.get("name"),
        "profile_image": user_data.get("picture"),
        "is_authenticated": True,
        "auth_time": user_data.get("auth_time"),
        "session_id": user_data.get("sid")
    }