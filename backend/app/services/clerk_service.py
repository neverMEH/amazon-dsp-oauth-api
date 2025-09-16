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
from jwt.algorithms import RSAAlgorithm

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
        self._jwks_cache = None
        self._jwks_cache_time = None
    
    async def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Clerk session token

        Args:
            token: JWT session token from Clerk

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            logger.debug("Starting token verification")

            # Get JWKS from Clerk
            jwks = await self.get_jwks()
            if not jwks:
                logger.error("Failed to fetch JWKS")
                return None

            logger.debug(f"JWKS fetched, contains {len(jwks.get('keys', []))} keys")

            # Decode without verification first to get the kid
            unverified = jwt.decode(token, options={"verify_signature": False})
            kid = jwt.get_unverified_header(token).get("kid")

            logger.debug(f"Token kid: {kid}")
            logger.debug(f"Token claims: sub={unverified.get('sub')}, exp={unverified.get('exp')}")

            # Find the matching key
            public_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    public_key = RSAAlgorithm.from_jwk(json.dumps(key))
                    logger.debug(f"Found matching key for kid: {kid}")
                    break

            if not public_key:
                logger.error(f"No matching key found for kid: {kid}")
                logger.debug(f"Available kids: {[k.get('kid') for k in jwks.get('keys', [])]}")
                return None

            # Verify the token with the public key
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_signature": True}
            )

            logger.debug("Token signature verified successfully")

            # Check expiration
            if decoded.get("exp", 0) < datetime.utcnow().timestamp():
                logger.warning(f"Token expired: exp={decoded.get('exp')}, now={datetime.utcnow().timestamp()}")
                return None

            logger.debug(f"Token verified successfully for user: {decoded.get('sub')}")
            return decoded

        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid session token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying session token: {str(e)}", exc_info=True)
            return None
    
    async def get_jwks(self) -> Optional[Dict[str, Any]]:
        """
        Fetch JWKS from Clerk's endpoint

        Returns:
            JWKS data or None
        """
        # Cache JWKS for 1 hour
        if self._jwks_cache and self._jwks_cache_time:
            if datetime.utcnow() - self._jwks_cache_time < timedelta(hours=1):
                logger.debug("Using cached JWKS")
                return self._jwks_cache

        try:
            # Extract instance ID from publishable key
            # Format: pk_test_XXX or pk_live_XXX
            if not self.publishable_key:
                logger.error("Clerk publishable key not configured")
                logger.error(f"CLERK_PUBLISHABLE_KEY value: {self.publishable_key}")
                return None

            logger.debug(f"Publishable key prefix: {self.publishable_key[:20]}...")

            # Get the instance domain from the publishable key
            # The format is pk_[env]_[encoded_domain]
            # The encoded part is base64 encoded domain
            parts = self.publishable_key.split('_')
            if len(parts) < 3:
                logger.error(f"Invalid Clerk publishable key format. Parts: {parts}")
                return None

            env = parts[1]  # 'test' or 'live'

            # The third part is base64 encoded domain - decode it
            import base64
            try:
                encoded_domain = parts[2]
                # Remove trailing $ if present (it's part of Clerk's key format)
                if encoded_domain.endswith('$'):
                    encoded_domain = encoded_domain[:-1]

                # Add padding if needed for base64 decoding
                padding = 4 - len(encoded_domain) % 4
                if padding != 4:
                    encoded_domain += '=' * padding

                decoded = base64.b64decode(encoded_domain).decode('utf-8')
                # Remove trailing $ from decoded domain if present
                if decoded.endswith('$'):
                    decoded = decoded[:-1]

                # Extract just the subdomain (first part before .clerk.accounts.dev)
                instance_id = decoded.split('.')[0]
                logger.debug(f"Decoded domain: {decoded}, instance: {instance_id}")
            except Exception as e:
                logger.error(f"Failed to decode instance from key: {e}")
                # Fallback: try using it directly
                instance_id = parts[2].split('.')[0]

            logger.debug(f"Clerk instance: {instance_id}, env: {env}")

            # Construct JWKS URL
            jwks_url = f"https://{instance_id}.clerk.accounts.dev/.well-known/jwks.json"
            logger.debug(f"JWKS URL: {jwks_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url)
                if response.status_code == 200:
                    self._jwks_cache = response.json()
                    self._jwks_cache_time = datetime.utcnow()
                    logger.debug(f"JWKS fetched successfully, {len(self._jwks_cache.get('keys', []))} keys")
                    return self._jwks_cache
                else:
                    logger.error(f"Failed to fetch JWKS: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching JWKS: {str(e)}", exc_info=True)
            return None
    
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