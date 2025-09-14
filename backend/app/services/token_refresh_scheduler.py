"""
Token refresh scheduler for proactive OAuth token management
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from supabase import Client

from app.services.token_service import TokenService
from app.db.base import get_supabase_client

logger = structlog.get_logger()


class TokenRefreshScheduler:
    """
    Manages proactive token refresh for OAuth tokens

    Features:
    - Checks for expiring tokens every 5 minutes
    - Refreshes tokens 10 minutes before expiration
    - Tracks refresh failures and retries
    - Provides manual refresh capability
    """

    def __init__(self, supabase_client: Optional[Client] = None):
        self.supabase_client = supabase_client or get_supabase_client()
        self.token_service = TokenService(self.supabase_client)
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.refresh_tasks: Dict[str, asyncio.Task] = {}

    async def start(self):
        """Start the token refresh scheduler"""
        if self.is_running:
            logger.info("Token refresh scheduler is already running")
            return

        try:
            # Schedule token refresh checks every 5 minutes
            self.scheduler.add_job(
                self._check_and_refresh_tokens,
                IntervalTrigger(minutes=5),
                id="token_refresh_check",
                name="Check and refresh expiring tokens",
                replace_existing=True
            )

            # Schedule cleanup of old sync history every hour
            self.scheduler.add_job(
                self._cleanup_old_history,
                IntervalTrigger(hours=1),
                id="cleanup_old_history",
                name="Clean up old sync history",
                replace_existing=True
            )

            self.scheduler.start()
            self.is_running = True

            # Run initial check immediately
            await self._check_and_refresh_tokens()

            logger.info("Token refresh scheduler started successfully")

        except Exception as e:
            logger.error("Failed to start token refresh scheduler", error=str(e))
            raise

    async def stop(self):
        """Stop the token refresh scheduler"""
        if not self.is_running:
            return

        try:
            # Cancel all running refresh tasks
            for task_id, task in self.refresh_tasks.items():
                if not task.done():
                    task.cancel()

            self.refresh_tasks.clear()

            # Shutdown scheduler
            self.scheduler.shutdown(wait=False)
            self.is_running = False

            logger.info("Token refresh scheduler stopped")

        except Exception as e:
            logger.error("Error stopping token refresh scheduler", error=str(e))

    async def _check_and_refresh_tokens(self):
        """Check for expiring tokens and refresh them"""
        try:
            # Get tokens expiring in the next 10 minutes
            expiry_threshold = datetime.now(timezone.utc) + timedelta(minutes=10)

            response = self.supabase_client.table('oauth_tokens').select(
                'id, user_id, access_token, refresh_token, expires_at, refresh_failure_count, proactive_refresh_enabled'
            ).lte('expires_at', expiry_threshold.isoformat()).eq(
                'proactive_refresh_enabled', True
            ).lt('refresh_failure_count', 3).execute()  # Skip tokens that have failed 3+ times

            expiring_tokens = response.data

            if not expiring_tokens:
                logger.debug("No tokens need refreshing")
                return

            logger.info(f"Found {len(expiring_tokens)} tokens expiring soon")

            # Refresh each token
            refresh_tasks = []
            for token_data in expiring_tokens:
                task = asyncio.create_task(
                    self._refresh_single_token(token_data)
                )
                refresh_tasks.append(task)
                self.refresh_tasks[token_data['id']] = task

            # Wait for all refresh tasks to complete
            results = await asyncio.gather(*refresh_tasks, return_exceptions=True)

            # Log results
            success_count = sum(1 for r in results if r is True)
            failure_count = len(results) - success_count

            logger.info(
                "Token refresh batch completed",
                total=len(results),
                success=success_count,
                failure=failure_count
            )

        except Exception as e:
            logger.error("Error checking and refreshing tokens", error=str(e))

    async def _refresh_single_token(self, token_data: Dict) -> bool:
        """
        Refresh a single token

        Args:
            token_data: Token data from database

        Returns:
            True if refresh successful, False otherwise
        """
        user_id = token_data['user_id']
        token_id = token_data['id']

        try:
            logger.info(
                "Refreshing token",
                user_id=user_id,
                token_id=token_id,
                expires_at=token_data['expires_at']
            )

            # Use token service to refresh
            new_tokens = await self.token_service.refresh_oauth_token(
                user_id=user_id,
                refresh_token=token_data['refresh_token']
            )

            if new_tokens:
                # Update database with new tokens
                update_data = {
                    'access_token': new_tokens['access_token'],
                    'refresh_token': new_tokens.get('refresh_token', token_data['refresh_token']),
                    'expires_at': new_tokens['expires_at'],
                    'refresh_failure_count': 0,  # Reset failure count on success
                    'last_refresh_error': None,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }

                self.supabase_client.table('oauth_tokens').update(
                    update_data
                ).eq('id', token_id).execute()

                # Log refresh in sync history
                await self._log_refresh_history(
                    user_id=user_id,
                    token_id=token_id,
                    success=True
                )

                logger.info(
                    "Token refreshed successfully",
                    user_id=user_id,
                    token_id=token_id,
                    new_expiry=new_tokens['expires_at']
                )

                return True
            else:
                raise Exception("Token refresh returned no data")

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Failed to refresh token",
                user_id=user_id,
                token_id=token_id,
                error=error_msg
            )

            # Update failure count and error message
            try:
                current_count = token_data.get('refresh_failure_count', 0)

                update_data = {
                    'refresh_failure_count': current_count + 1,
                    'last_refresh_error': error_msg[:500],  # Limit error message length
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }

                # Disable proactive refresh after 3 failures
                if current_count + 1 >= 3:
                    update_data['proactive_refresh_enabled'] = False
                    logger.warning(
                        "Disabling proactive refresh after repeated failures",
                        user_id=user_id,
                        token_id=token_id,
                        failure_count=current_count + 1
                    )

                self.supabase_client.table('oauth_tokens').update(
                    update_data
                ).eq('id', token_id).execute()

                # Log failure in sync history
                await self._log_refresh_history(
                    user_id=user_id,
                    token_id=token_id,
                    success=False,
                    error=error_msg
                )

            except Exception as update_error:
                logger.error(
                    "Failed to update token failure status",
                    user_id=user_id,
                    token_id=token_id,
                    error=str(update_error)
                )

            return False

    async def _log_refresh_history(
        self,
        user_id: str,
        token_id: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Log token refresh attempt in sync history"""
        try:
            # Get user account ID
            account_response = self.supabase_client.table('user_accounts').select(
                'id'
            ).eq('user_id', user_id).limit(1).execute()

            if not account_response.data:
                return

            account_id = account_response.data[0]['id']

            # Create sync history entry
            history_data = {
                'user_account_id': account_id,
                'sync_type': 'scheduled',
                'sync_status': 'success' if success else 'failed',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'accounts_synced': 1 if success else 0,
                'accounts_failed': 0 if success else 1,
                'metadata': {
                    'token_id': token_id,
                    'refresh_type': 'proactive'
                }
            }

            if error:
                history_data['error_details'] = {'error': error[:500]}

            self.supabase_client.table('account_sync_history').insert(
                history_data
            ).execute()

        except Exception as e:
            logger.warning(
                "Failed to log refresh history",
                user_id=user_id,
                error=str(e)
            )

    async def _cleanup_old_history(self):
        """Clean up old sync history entries (older than 30 days)"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

            response = self.supabase_client.table('account_sync_history').delete().lt(
                'created_at', cutoff_date.isoformat()
            ).execute()

            if response.data:
                logger.info(f"Cleaned up {len(response.data)} old sync history entries")

        except Exception as e:
            logger.error("Failed to cleanup old history", error=str(e))

    async def manual_refresh(self, user_id: str) -> Dict:
        """
        Manually trigger token refresh for a user

        Args:
            user_id: User ID to refresh tokens for

        Returns:
            Dict with refresh results
        """
        try:
            # Get user's tokens
            response = self.supabase_client.table('oauth_tokens').select(
                'id, access_token, refresh_token, expires_at'
            ).eq('user_id', user_id).execute()

            if not response.data:
                return {
                    'success': False,
                    'error': 'No tokens found for user'
                }

            token_data = response.data[0]

            # Perform refresh
            success = await self._refresh_single_token({
                **token_data,
                'user_id': user_id,
                'refresh_failure_count': 0
            })

            return {
                'success': success,
                'token_id': token_data['id'],
                'message': 'Token refreshed successfully' if success else 'Token refresh failed'
            }

        except Exception as e:
            logger.error(
                "Manual token refresh failed",
                user_id=user_id,
                error=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }


# Global scheduler instance
token_refresh_scheduler: Optional[TokenRefreshScheduler] = None


def get_token_refresh_scheduler() -> TokenRefreshScheduler:
    """Get or create the global token refresh scheduler"""
    global token_refresh_scheduler
    if token_refresh_scheduler is None:
        token_refresh_scheduler = TokenRefreshScheduler()
    return token_refresh_scheduler