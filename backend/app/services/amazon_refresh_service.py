"""
Amazon token refresh background service
"""
import asyncio
from typing import List, Dict
from datetime import datetime, timezone
import structlog

from app.services.token_service import token_service
from app.services.amazon_oauth_service import amazon_oauth_service
from app.core.exceptions import TokenRefreshError

logger = structlog.get_logger()


class AmazonRefreshService:
    """Background service for automatic Amazon token refresh"""
    
    def __init__(self):
        """Initialize refresh service"""
        self.running = False
        self.refresh_interval = 300  # Check every 5 minutes
        self.refresh_buffer = 300   # Refresh tokens expiring within 5 minutes
    
    async def start(self):
        """Start the background refresh service"""
        if self.running:
            logger.warning("Amazon refresh service already running")
            return
        
        self.running = True
        logger.info("Starting Amazon token refresh service")
        
        while self.running:
            try:
                await self._refresh_expiring_tokens()
            except Exception as e:
                logger.error("Error in refresh service", error=str(e))
            
            # Wait for next check
            await asyncio.sleep(self.refresh_interval)
        
        logger.info("Amazon token refresh service stopped")
    
    def stop(self):
        """Stop the background refresh service"""
        self.running = False
        logger.info("Stopping Amazon token refresh service")
    
    async def _refresh_expiring_tokens(self):
        """Check and refresh expiring tokens for all users"""
        try:
            # Get all Amazon accounts that need refresh
            accounts_to_refresh = await self._get_accounts_needing_refresh()
            
            if not accounts_to_refresh:
                logger.debug("No Amazon tokens need refresh")
                return
            
            logger.info(f"Found {len(accounts_to_refresh)} Amazon accounts needing refresh")
            
            # Refresh tokens for each account
            for account in accounts_to_refresh:
                try:
                    await self._refresh_account_tokens(
                        account["user_id"], 
                        int(account["profile_id"])
                    )
                except Exception as refresh_error:
                    logger.error(
                        "Failed to refresh tokens for account",
                        user_id=account["user_id"],
                        profile_id=account["profile_id"],
                        error=str(refresh_error)
                    )
                    # Continue with next account even if one fails
                    continue
            
        except Exception as e:
            logger.error("Failed to refresh expiring tokens", error=str(e))
    
    async def _get_accounts_needing_refresh(self) -> List[Dict]:
        """Get all Amazon accounts that need token refresh"""
        try:
            # Query user_accounts for Amazon accounts with expiring tokens
            result = token_service.db.table("user_accounts").select(
                "user_id, profile_id, token_expires_at"
            ).eq("platform", "amazon").execute()
            
            if not result.data:
                return []
            
            accounts_needing_refresh = []
            now = datetime.now(timezone.utc)
            
            for account in result.data:
                expires_at = datetime.fromisoformat(
                    account["token_expires_at"].replace("Z", "+00:00")
                )
                
                # Check if expires within buffer time
                seconds_until_expiry = (expires_at - now).total_seconds()
                if seconds_until_expiry <= self.refresh_buffer:
                    accounts_needing_refresh.append(account)
            
            return accounts_needing_refresh
            
        except Exception as e:
            logger.error("Failed to get accounts needing refresh", error=str(e))
            return []
    
    async def _refresh_account_tokens(self, user_id: str, profile_id: int):
        """Refresh tokens for a specific user account"""
        try:
            # Get current tokens
            current_tokens = await token_service.retrieve_amazon_tokens(user_id, profile_id)
            
            if not current_tokens:
                logger.warning(
                    "No tokens found for refresh",
                    user_id=user_id,
                    profile_id=profile_id
                )
                return
            
            # Refresh using the refresh token
            new_token_response = await amazon_oauth_service.refresh_access_token(
                current_tokens["refresh_token"]
            )
            
            # Store the refreshed tokens
            await token_service.store_amazon_tokens(
                user_id=user_id,
                profile_id=profile_id,
                tokens=new_token_response.dict()
            )
            
            logger.info(
                "Successfully refreshed Amazon tokens",
                user_id=user_id,
                profile_id=profile_id,
                new_expires_in=new_token_response.expires_in
            )
            
        except TokenRefreshError as e:
            # Token refresh failed - might need re-authentication
            logger.error(
                "Token refresh failed - may need re-authentication",
                user_id=user_id,
                profile_id=profile_id,
                error=str(e)
            )
            # Don't raise - let other accounts continue refreshing
            
        except Exception as e:
            logger.error(
                "Unexpected error refreshing tokens",
                user_id=user_id,
                profile_id=profile_id,
                error=str(e)
            )
            raise
    
    async def refresh_user_tokens(self, user_id: str) -> Dict[str, any]:
        """
        Manually refresh all Amazon tokens for a specific user
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            Dict with refresh results
        """
        try:
            # Get user's Amazon accounts
            user_accounts = await token_service.get_user_amazon_accounts(user_id)
            
            if not user_accounts:
                return {
                    "status": "no_accounts",
                    "message": "No Amazon accounts found for user",
                    "refreshed": 0,
                    "failed": 0
                }
            
            refreshed_count = 0
            failed_count = 0
            errors = []
            
            for account in user_accounts:
                try:
                    await self._refresh_account_tokens(user_id, int(account["profile_id"]))
                    refreshed_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append({
                        "profile_id": account["profile_id"],
                        "error": str(e)
                    })
            
            return {
                "status": "completed",
                "message": f"Refreshed {refreshed_count} accounts, {failed_count} failed",
                "refreshed": refreshed_count,
                "failed": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error("Failed to refresh user tokens", user_id=user_id, error=str(e))
            return {
                "status": "error",
                "message": f"Failed to refresh tokens: {str(e)}",
                "refreshed": 0,
                "failed": 0,
                "errors": [{"error": str(e)}]
            }


# Create singleton instance
amazon_refresh_service = AmazonRefreshService()