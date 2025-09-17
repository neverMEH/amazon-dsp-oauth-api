"""
Token management service
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import structlog
from supabase import Client

from app.core.security import token_encryption
from app.core.exceptions import DatabaseError, EncryptionError
from app.db.base import get_supabase_client

logger = structlog.get_logger()


class TokenService:
    """Manage token storage and retrieval"""
    
    def __init__(self, db_client: Optional[Client] = None):
        """Initialize with database client"""
        self.db = db_client or get_supabase_client()
    
    async def store_state_token(self, state_token: str, redirect_uri: str) -> Dict:
        """
        Store OAuth state token for CSRF protection
        
        Args:
            state_token: Generated state token
            redirect_uri: Redirect URI for this auth flow
            
        Returns:
            Stored state record
        """
        try:
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            
            data = {
                "state_token": state_token,
                "redirect_uri": redirect_uri,
                "expires_at": expires_at,
                "used": False
            }
            
            result = self.db.table("oauth_states").insert(data).execute()
            
            logger.info("Stored state token", state_token=state_token[:10] + "...")
            return result.data[0] if result.data else data
            
        except Exception as e:
            logger.error("Failed to store state token", error=str(e))
            raise DatabaseError("store_state_token", str(e))
    
    async def validate_state_token(self, state_token: str) -> bool:
        """
        Validate and mark state token as used
        
        Args:
            state_token: State token to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Find the state token
            result = self.db.table("oauth_states").select("*").eq(
                "state_token", state_token
            ).eq("used", False).execute()
            
            if not result.data:
                logger.warning("State token not found", state_token=state_token[:10] + "...")
                return False
            
            state_record = result.data[0]
            
            # Check if expired
            expires_at = datetime.fromisoformat(state_record["expires_at"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if expires_at < now:
                logger.warning("State token expired", state_token=state_token[:10] + "...", expires_at=expires_at, now=now)
                return False
            
            # Mark as used
            self.db.table("oauth_states").update(
                {"used": True}
            ).eq("state_token", state_token).execute()
            
            logger.info("State token validated", state_token=state_token[:10] + "...")
            return True
            
        except Exception as e:
            logger.error("Failed to validate state token", error=str(e))
            return False
    
    async def store_tokens(self, token_data: Dict, user_id: Optional[str] = None) -> Dict:
        """
        Store encrypted OAuth tokens

        Args:
            token_data: Dict containing access_token, refresh_token, etc.
            user_id: Optional user ID to associate tokens with

        Returns:
            Stored token record
        """
        try:
            # Encrypt tokens
            encrypted_access = token_encryption.encrypt_token(token_data["access_token"])
            encrypted_refresh = token_encryption.encrypt_token(token_data["refresh_token"])

            # If user_id provided, deactivate only that user's tokens
            # Otherwise deactivate all tokens (backward compatibility)
            if user_id:
                self.db.table("oauth_tokens").update(
                    {"is_active": False}
                ).eq("is_active", True).eq("user_id", user_id).execute()
            else:
                self.db.table("oauth_tokens").update(
                    {"is_active": False}
                ).eq("is_active", True).execute()

            # Store new tokens
            data = {
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "token_type": token_data.get("token_type", "Bearer"),
                "expires_at": token_data["expires_at"],
                "scope": token_data["scope"],
                "is_active": True,
                "refresh_count": 0
            }

            # Add user_id if provided
            if user_id:
                data["user_id"] = user_id
            
            result = self.db.table("oauth_tokens").insert(data).execute()
            
            if result.data:
                token_record = result.data[0]
                logger.info("Stored new tokens", token_id=token_record["id"])
                
                # Log authentication event
                await self.log_auth_event(
                    "login",
                    "success",
                    token_id=token_record["id"]
                )
                
                return token_record
            
            raise DatabaseError("store_tokens", "No data returned from insert")
            
        except Exception as e:
            logger.error("Failed to store tokens", error=str(e))
            await self.log_auth_event("login", "failure", error_message=str(e))
            raise DatabaseError("store_tokens", str(e))
    
    async def get_active_token(self, user_id: Optional[str] = None) -> Optional[Dict]:
        """
        Get the active token record for a specific user

        Args:
            user_id: Optional user ID to filter tokens

        Returns:
            Active token record or None
        """
        try:
            # Build query for active tokens
            query = self.db.table("oauth_tokens").select("*").eq("is_active", True)

            # Add user filter if provided
            if user_id:
                query = query.eq("user_id", user_id)

            # Execute query
            result = query.execute()
            
            if not result.data:
                logger.debug("No active tokens found")
                return None
            
            if len(result.data) > 1:
                # Multiple active tokens found - this shouldn't happen but handle it gracefully
                logger.warning(
                    f"Multiple active tokens found ({len(result.data)}), using most recent",
                    count=len(result.data)
                )
                # Sort by created_at descending and return the most recent
                sorted_tokens = sorted(result.data, key=lambda x: x['created_at'], reverse=True)
                
                # Optionally, deactivate older tokens to clean up
                for old_token in sorted_tokens[1:]:
                    logger.info(f"Deactivating older active token", token_id=old_token['id'])
                    self.db.table("oauth_tokens").update(
                        {"is_active": False}
                    ).eq("id", old_token['id']).execute()
                
                return sorted_tokens[0]
            
            # Exactly one active token - the expected case
            return result.data[0]
            
        except Exception as e:
            logger.error("Error getting active token", error=str(e))
            return None
    
    async def get_decrypted_tokens(self) -> Optional[Dict]:
        """
        Get decrypted access and refresh tokens
        
        Returns:
            Dict with decrypted tokens or None
        """
        try:
            token_record = await self.get_active_token()
            
            if not token_record:
                return None
            
            # Decrypt tokens
            access_token = token_encryption.decrypt_token(token_record["access_token"])
            refresh_token = token_encryption.decrypt_token(token_record["refresh_token"])
            
            return {
                "id": token_record["id"],
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": token_record["expires_at"],
                "refresh_count": token_record.get("refresh_count", 0)
            }
            
        except Exception as e:
            logger.error("Failed to decrypt tokens", error=str(e))
            raise EncryptionError("decrypt_tokens")
    
    async def update_tokens(self, token_id: str, new_token_data: Dict) -> Dict:
        """
        Update tokens after refresh
        
        Args:
            token_id: ID of token record to update
            new_token_data: New token data from refresh
            
        Returns:
            Updated token record
        """
        try:
            # Encrypt new tokens
            encrypted_access = token_encryption.encrypt_token(new_token_data["access_token"])
            encrypted_refresh = token_encryption.encrypt_token(new_token_data["refresh_token"])
            
            # Get current refresh count
            current = self.db.table("oauth_tokens").select("refresh_count").eq(
                "id", token_id
            ).single().execute()
            
            current_count = current.data.get("refresh_count", 0) if current.data else 0
            
            # Update tokens
            update_data = {
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "expires_at": new_token_data["expires_at"],
                "last_refresh_at": datetime.now(timezone.utc).isoformat(),
                "refresh_count": current_count + 1,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.db.table("oauth_tokens").update(update_data).eq(
                "id", token_id
            ).execute()
            
            if result.data:
                logger.info("Updated tokens after refresh", token_id=token_id)
                
                # Log refresh event
                await self.log_auth_event(
                    "refresh",
                    "success",
                    token_id=token_id,
                    metadata={"refresh_count": current_count + 1}
                )
                
                return result.data[0]
            
            raise DatabaseError("update_tokens", "No data returned from update")
            
        except Exception as e:
            logger.error("Failed to update tokens", error=str(e))
            await self.log_auth_event("refresh", "failure", token_id=token_id, error_message=str(e))
            raise DatabaseError("update_tokens", str(e))
    
    async def revoke_tokens(self) -> bool:
        """
        Revoke all active tokens
        
        Returns:
            True if successful
        """
        try:
            result = self.db.table("oauth_tokens").update(
                {"is_active": False}
            ).eq("is_active", True).execute()
            
            if result.data:
                logger.info("Revoked active tokens")
                await self.log_auth_event("revoke", "success")
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to revoke tokens", error=str(e))
            await self.log_auth_event("revoke", "failure", error_message=str(e))
            raise DatabaseError("revoke_tokens", str(e))
    
    async def log_auth_event(
        self,
        event_type: str,
        event_status: str,
        token_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Log authentication event to audit log
        
        Args:
            event_type: Type of event (login, refresh, error, revoke)
            event_status: Status (success, failure)
            token_id: Associated token ID
            error_message: Error message if failed
            error_code: Error code if failed
            metadata: Additional event metadata
        """
        try:
            data = {
                "event_type": event_type,
                "event_status": event_status,
                "token_id": token_id,
                "error_message": error_message,
                "error_code": error_code,
                "metadata": metadata or {}
            }
            
            self.db.table("auth_audit_log").insert(data).execute()
            logger.debug("Logged auth event", event_type=event_type, status=event_status)
            
        except Exception as e:
            logger.error("Failed to log auth event", error=str(e))
            # Don't raise - logging failure shouldn't break auth flow
    
    async def get_audit_logs(self, limit: int = 50, offset: int = 0) -> Dict:
        """
        Get authentication audit logs
        
        Args:
            limit: Number of records to return
            offset: Pagination offset
            
        Returns:
            Audit log records
        """
        try:
            # Get total count
            count_result = self.db.table("auth_audit_log").select("*", count="exact").execute()
            total = count_result.count if hasattr(count_result, 'count') else 0
            
            # Get paginated results
            result = self.db.table("auth_audit_log").select("*").order(
                "created_at", desc=True
            ).limit(limit).offset(offset).execute()
            
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "events": result.data if result.data else []
            }
            
        except Exception as e:
            logger.error("Failed to get audit logs", error=str(e))
            raise DatabaseError("get_audit_logs", str(e))
    
    # Amazon Account Token Management
    
    async def store_amazon_tokens(
        self, 
        user_id: str, 
        profile_id: int, 
        tokens: Dict[str, Any]
    ) -> Dict:
        """
        Store Amazon tokens for a specific user and profile
        
        Args:
            user_id: Clerk user ID
            profile_id: Amazon profile ID
            tokens: Token data from Amazon OAuth
            
        Returns:
            Stored user account record
        """
        try:
            # Encrypt tokens
            encrypted_access = token_encryption.encrypt_token(tokens["access_token"])
            encrypted_refresh = token_encryption.encrypt_token(tokens["refresh_token"])
            
            # Calculate expiration
            expires_at = (
                datetime.now(timezone.utc) + 
                timedelta(seconds=tokens.get("expires_in", 3600))
            ).isoformat()
            
            # Store in user_accounts table
            data = {
                "user_id": user_id,
                "profile_id": str(profile_id),
                "platform": "amazon",
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "token_expires_at": expires_at,
                "scope": tokens.get("scope", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if account already exists (upsert)
            existing = self.db.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).eq("profile_id", str(profile_id)).eq("platform", "amazon").execute()
            
            if existing.data:
                # Update existing
                result = self.db.table("user_accounts").update({
                    "access_token": encrypted_access,
                    "refresh_token": encrypted_refresh,
                    "token_expires_at": expires_at,
                    "scope": tokens.get("scope", ""),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
                
                logger.info(
                    "Updated Amazon tokens", 
                    user_id=user_id, 
                    profile_id=profile_id
                )
                return result.data[0] if result.data else existing.data[0]
            else:
                # Insert new
                result = self.db.table("user_accounts").insert(data).execute()
                
                logger.info(
                    "Stored new Amazon tokens", 
                    user_id=user_id, 
                    profile_id=profile_id
                )
                return result.data[0] if result.data else data
                
        except Exception as e:
            logger.error("Failed to store Amazon tokens", user_id=user_id, error=str(e))
            raise DatabaseError("store_amazon_tokens", str(e))
    
    async def retrieve_amazon_tokens(
        self, 
        user_id: str, 
        profile_id: int
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve and decrypt Amazon tokens for a user and profile
        
        Args:
            user_id: Clerk user ID
            profile_id: Amazon profile ID
            
        Returns:
            Dict with decrypted tokens or None if not found
        """
        try:
            result = self.db.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).eq("profile_id", str(profile_id)).eq("platform", "amazon").execute()
            
            if not result.data:
                return None
            
            account = result.data[0]
            
            # Decrypt tokens
            try:
                access_token = token_encryption.decrypt_token(account["access_token"])
                refresh_token = token_encryption.decrypt_token(account["refresh_token"])
                
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": account["token_expires_at"],
                    "scope": account["scope"]
                }
            except Exception as decrypt_error:
                logger.error(
                    "Failed to decrypt Amazon tokens", 
                    user_id=user_id, 
                    profile_id=profile_id,
                    error=str(decrypt_error)
                )
                raise EncryptionError("decrypt_amazon_tokens", str(decrypt_error))
                
        except Exception as e:
            logger.error("Failed to retrieve Amazon tokens", user_id=user_id, error=str(e))
            return None
    
    async def check_token_expiry(self, user_id: str, profile_id: int) -> bool:
        """
        Check if Amazon tokens need refresh
        
        Args:
            user_id: Clerk user ID
            profile_id: Amazon profile ID
            
        Returns:
            True if tokens need refresh, False otherwise
        """
        try:
            result = self.db.table("user_accounts").select("token_expires_at").eq(
                "user_id", user_id
            ).eq("profile_id", str(profile_id)).eq("platform", "amazon").execute()
            
            if not result.data:
                return True  # No tokens found, needs auth
            
            expires_at = datetime.fromisoformat(
                result.data[0]["token_expires_at"].replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            
            # Refresh if expiring within 5 minutes
            return (expires_at - now).total_seconds() < 300
            
        except Exception as e:
            logger.error("Failed to check token expiry", user_id=user_id, error=str(e))
            return True  # Assume needs refresh on error
    
    async def get_user_amazon_accounts(self, user_id: str) -> list:
        """
        Get all Amazon accounts for a user
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            List of Amazon account records
        """
        try:
            result = self.db.table("user_accounts").select(
                "profile_id, token_expires_at, scope, created_at, updated_at"
            ).eq("user_id", user_id).eq("platform", "amazon").execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error("Failed to get user Amazon accounts", user_id=user_id, error=str(e))
            return []
    
    async def get_connection_status(self, user_id: str, profile_id: int) -> Dict:
        """
        Get Amazon connection status for a user and profile
        
        Args:
            user_id: Clerk user ID
            profile_id: Amazon profile ID
            
        Returns:
            Connection status dictionary
        """
        try:
            result = self.db.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).eq("profile_id", str(profile_id)).eq("platform", "amazon").execute()
            
            if not result.data:
                return {
                    "connected": False,
                    "profile_id": profile_id,
                    "needs_refresh": False,
                    "expires_at": None,
                    "last_updated": None,
                    "error": None
                }
            
            account = result.data[0]
            expires_at = datetime.fromisoformat(
                account["token_expires_at"].replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            needs_refresh = (expires_at - now).total_seconds() < 300
            
            return {
                "connected": True,
                "profile_id": profile_id,
                "needs_refresh": needs_refresh,
                "expires_at": account["token_expires_at"],
                "last_updated": account["updated_at"],
                "error": None
            }
            
        except Exception as e:
            logger.error("Failed to get connection status", user_id=user_id, error=str(e))
            return {
                "connected": False,
                "profile_id": profile_id,
                "needs_refresh": False,
                "expires_at": None,
                "last_updated": None,
                "error": str(e)
            }
    
    async def disconnect_amazon_account(self, user_id: str, profile_id: int) -> bool:
        """
        Disconnect Amazon account by removing tokens
        
        Args:
            user_id: Clerk user ID
            profile_id: Amazon profile ID
            
        Returns:
            True if successfully disconnected
        """
        try:
            result = self.db.table("user_accounts").delete().eq(
                "user_id", user_id
            ).eq("profile_id", str(profile_id)).eq("platform", "amazon").execute()
            
            success = bool(result.data)
            if success:
                logger.info("Disconnected Amazon account", user_id=user_id, profile_id=profile_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to disconnect Amazon account", user_id=user_id, error=str(e))
            return False
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a token for storage"""
        return token_encryption.encrypt_token(token)
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token from storage"""
        return token_encryption.decrypt_token(encrypted_token)


# Create singleton instance
token_service = TokenService()