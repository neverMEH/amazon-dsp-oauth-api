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
    
    async def store_tokens(self, token_data: Dict) -> Dict:
        """
        Store encrypted OAuth tokens
        
        Args:
            token_data: Dict containing access_token, refresh_token, etc.
            
        Returns:
            Stored token record
        """
        try:
            # Encrypt tokens
            encrypted_access = token_encryption.encrypt_token(token_data["access_token"])
            encrypted_refresh = token_encryption.encrypt_token(token_data["refresh_token"])
            
            # Deactivate any existing active tokens
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
    
    async def get_active_token(self) -> Optional[Dict]:
        """
        Get the active token record
        
        Returns:
            Active token record or None
        """
        try:
            result = self.db.table("oauth_tokens").select("*").eq(
                "is_active", True
            ).single().execute()
            
            if result.data:
                return result.data
            
            return None
            
        except Exception as e:
            logger.debug("No active token found", error=str(e))
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


# Create singleton instance
token_service = TokenService()