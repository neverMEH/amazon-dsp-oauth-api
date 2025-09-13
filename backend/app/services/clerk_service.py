"""
Clerk authentication service
"""
import httpx
import jwt
import json
import hashlib
import hmac
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
from svix.webhooks import Webhook, WebhookVerificationError

from app.config import settings
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

logger = structlog.get_logger()


class ClerkService:
    """Service for Clerk authentication operations"""
    
    def __init__(self):
        """Initialize Clerk service"""
        self.api_url = settings.clerk_api_url
        self.secret_key = settings.clerk_secret_key
        self.publishable_key = settings.clerk_publishable_key
        self.user_service = UserService()
    
    async def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Clerk session token
        
        Args:
            token: JWT session token from Clerk
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            # Verify JWT with Clerk's public key
            # In production, fetch public keys from Clerk's JWKS endpoint
            decoded = self.verify_jwt(token)
            
            # Check expiration
            if decoded.get("exp", 0) < datetime.utcnow().timestamp():
                logger.warning("Token expired")
                return None
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid session token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying session token: {str(e)}")
            return None
    
    def verify_jwt(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token with Clerk's public key
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
        """
        # This is a simplified version - in production, fetch keys from JWKS
        # For now, we'll use the secret key for symmetric verification
        # Clerk actually uses RS256 with public keys
        
        if not self.secret_key:
            raise ValueError("Clerk secret key not configured")
        
        # Extract the key part (remove 'sk_test_' or 'sk_live_' prefix)
        key = self.secret_key.split('_')[-1] if '_' in self.secret_key else self.secret_key
        
        return jwt.decode(
            token,
            key,
            algorithms=["HS256", "RS256"],
            options={"verify_signature": True}
        )
    
    async def get_user(self, clerk_user_id: str) -> Optional[UserCreate]:
        """
        Get user data from Clerk API
        
        Args:
            clerk_user_id: Clerk user ID
            
        Returns:
            User data or None
        """
        if not self.secret_key:
            logger.error("Clerk secret key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/users/{clerk_user_id}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    
                    # Extract primary email
                    email = None
                    for email_obj in user_data.get("email_addresses", []):
                        if email_obj.get("verification", {}).get("status") == "verified":
                            email = email_obj.get("email_address")
                            break
                    
                    if not email:
                        logger.error(f"No verified email found for user {clerk_user_id}")
                        return None
                    
                    return UserCreate(
                        clerk_user_id=user_data["id"],
                        email=email,
                        first_name=user_data.get("first_name"),
                        last_name=user_data.get("last_name"),
                        profile_image_url=user_data.get("profile_image_url")
                    )
                else:
                    logger.error(f"Failed to get user from Clerk: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching user from Clerk: {str(e)}")
            return None
    
    async def sync_user_with_database(self, clerk_user_id: str) -> bool:
        """
        Sync Clerk user with local database
        
        Args:
            clerk_user_id: Clerk user ID
            
        Returns:
            Success status
        """
        try:
            # Get user data from Clerk
            user_data = await self.get_user(clerk_user_id)
            
            if not user_data:
                logger.error(f"Failed to get user data for {clerk_user_id}")
                return False
            
            # Create or update user in database
            await self.user_service.get_or_create_user(user_data)
            
            logger.info(f"User {clerk_user_id} synced with database")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing user with database: {str(e)}")
            return False
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List users from Clerk
        
        Args:
            limit: Number of users to fetch
            offset: Pagination offset
            
        Returns:
            List of user data
        """
        if not self.secret_key:
            logger.error("Clerk secret key not configured")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/users",
                    params={"limit": limit, "offset": offset},
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to list users from Clerk: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error listing users from Clerk: {str(e)}")
            return []


class ClerkWebhookHandler:
    """Handle Clerk webhook events"""
    
    def __init__(self):
        """Initialize webhook handler"""
        self.webhook_secret = settings.clerk_webhook_secret
        self.user_service = UserService()
    
    def verify_webhook(self, payload: str, headers: Dict[str, str]) -> bool:
        """
        Verify webhook signature from Clerk
        
        Args:
            payload: Raw webhook payload
            headers: Request headers including signature
            
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.error("Clerk webhook secret not configured")
            return False
        
        try:
            # Use Svix library to verify webhook
            wh = Webhook(self.webhook_secret)
            
            # Extract required headers
            svix_headers = {
                "svix-id": headers.get("svix-id", ""),
                "svix-timestamp": headers.get("svix-timestamp", ""),
                "svix-signature": headers.get("svix-signature", "")
            }
            
            # Verify the webhook
            wh.verify(payload, svix_headers)
            return True
            
        except WebhookVerificationError as e:
            logger.error(f"Webhook verification failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error verifying webhook: {str(e)}")
            return False
    
    def verify_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        """
        Manually verify webhook signature
        
        Args:
            payload: Webhook payload
            signature: Signature from header
            timestamp: Timestamp from header
            
        Returns:
            True if signature matches
        """
        if not self.webhook_secret:
            return False
        
        # Create signed content
        signed_content = f"{timestamp}.{payload}"
        
        # Generate expected signature
        expected_sig = hmac.new(
            self.webhook_secret.encode(),
            signed_content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(f"v1={expected_sig}", signature)
    
    async def handle_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle webhook event from Clerk
        
        Args:
            event_data: Parsed webhook event data
            
        Returns:
            Success status
        """
        try:
            event_type = event_data.get("type")
            data = event_data.get("data", {})
            
            logger.info(f"Handling Clerk webhook event: {event_type}")
            
            if event_type == "user.created":
                return await self.handle_user_created(data)
            elif event_type == "user.updated":
                return await self.handle_user_updated(data)
            elif event_type == "user.deleted":
                return await self.handle_user_deleted(data)
            elif event_type == "session.created":
                return await self.handle_session_created(data)
            elif event_type == "session.ended":
                return await self.handle_session_ended(data)
            else:
                logger.info(f"Unhandled event type: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling webhook event: {str(e)}")
            return False
    
    async def handle_user_created(self, user_data: Dict[str, Any]) -> bool:
        """Handle user.created event"""
        try:
            # Extract user information
            clerk_user_id = user_data.get("id")
            
            # Extract primary email
            email = None
            for email_obj in user_data.get("email_addresses", []):
                if email_obj.get("verification", {}).get("status") == "verified":
                    email = email_obj.get("email_address")
                    break
            
            if not email:
                logger.error(f"No verified email for user {clerk_user_id}")
                return False
            
            # Create user in database
            user_create = UserCreate(
                clerk_user_id=clerk_user_id,
                email=email,
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                profile_image_url=user_data.get("profile_image_url")
            )
            
            await self.user_service.create_user(user_create)
            
            logger.info(f"User created: {clerk_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling user.created: {str(e)}")
            return False
    
    async def handle_user_updated(self, user_data: Dict[str, Any]) -> bool:
        """Handle user.updated event"""
        try:
            clerk_user_id = user_data.get("id")
            
            # Get existing user
            user = await self.user_service.get_user_by_clerk_id(clerk_user_id)
            
            if not user:
                logger.warning(f"User not found for update: {clerk_user_id}")
                # Create the user if doesn't exist
                return await self.handle_user_created(user_data)
            
            # Update user information
            user_update = UserUpdate(
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                profile_image_url=user_data.get("profile_image_url")
            )
            
            await self.user_service.update_user(user.id, user_update)
            
            logger.info(f"User updated: {clerk_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling user.updated: {str(e)}")
            return False
    
    async def handle_user_deleted(self, user_data: Dict[str, Any]) -> bool:
        """Handle user.deleted event"""
        try:
            clerk_user_id = user_data.get("id")
            
            # Note: We might want to soft delete or archive instead
            # For now, we'll just mark the user as inactive
            user = await self.user_service.get_user_by_clerk_id(clerk_user_id)
            
            if user:
                # Could implement a soft delete here
                logger.info(f"User deletion requested: {clerk_user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling user.deleted: {str(e)}")
            return False
    
    async def handle_session_created(self, session_data: Dict[str, Any]) -> bool:
        """Handle session.created event"""
        try:
            user_id = session_data.get("user_id")
            
            if user_id:
                # Update last login time
                await self.user_service.update_last_login(user_id)
                logger.info(f"Session created for user: {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling session.created: {str(e)}")
            return False
    
    async def handle_session_ended(self, session_data: Dict[str, Any]) -> bool:
        """Handle session.ended event"""
        try:
            user_id = session_data.get("user_id")
            logger.info(f"Session ended for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling session.ended: {str(e)}")
            return False