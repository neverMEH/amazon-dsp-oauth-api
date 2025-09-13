"""
Background token refresh service
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog

from app.config import settings
from app.core.oauth import oauth_client
from app.services.token_service import token_service

logger = structlog.get_logger()

# Global reference to the refresh task
refresh_task: Optional[asyncio.Task] = None


async def refresh_token_if_needed():
    """
    Check and refresh token if it's about to expire
    """
    try:
        # Get current tokens
        tokens = await token_service.get_decrypted_tokens()
        
        if not tokens:
            logger.debug("No active token to refresh")
            return
        
        # Check expiration
        expires_at = datetime.fromisoformat(
            tokens["expires_at"].replace("Z", "+00:00")
        )
        time_until_expiry = (expires_at - datetime.now(timezone.utc)).total_seconds()
        
        logger.debug(
            "Token status",
            expires_in_seconds=time_until_expiry,
            refresh_buffer=settings.token_refresh_buffer
        )
        
        # Refresh if within buffer time
        if time_until_expiry <= settings.token_refresh_buffer:
            logger.info(
                "Token expiring soon, refreshing",
                expires_in_seconds=time_until_expiry
            )
            
            # Attempt refresh with retries
            for attempt in range(settings.max_refresh_retries):
                try:
                    # Refresh the token
                    new_token_data = await oauth_client.refresh_access_token(
                        tokens["refresh_token"]
                    )
                    
                    # Update stored tokens
                    await token_service.update_tokens(tokens["id"], new_token_data)
                    
                    logger.info(
                        "Token refreshed successfully",
                        attempt=attempt + 1,
                        new_expiry=new_token_data["expires_at"]
                    )
                    break
                    
                except Exception as e:
                    logger.error(
                        "Token refresh attempt failed",
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    
                    if attempt < settings.max_refresh_retries - 1:
                        # Exponential backoff
                        wait_time = settings.retry_backoff_base ** attempt
                        logger.info(f"Retrying in {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("All refresh attempts failed")
                        # Log the failure but don't crash the service
                        await token_service.log_auth_event(
                            "refresh",
                            "failure",
                            token_id=tokens["id"],
                            error_message=str(e),
                            metadata={"attempts": settings.max_refresh_retries}
                        )
        else:
            logger.debug(
                "Token still valid",
                expires_in_seconds=time_until_expiry
            )
            
    except Exception as e:
        logger.error("Error in refresh service", error=str(e))
        # Don't crash the service on errors


async def refresh_service_loop():
    """
    Main loop for the background refresh service
    """
    logger.info(
        "Token refresh service started",
        interval_seconds=settings.token_refresh_interval
    )
    
    while True:
        try:
            await refresh_token_if_needed()
            await asyncio.sleep(settings.token_refresh_interval)
        except asyncio.CancelledError:
            logger.info("Token refresh service stopping")
            break
        except Exception as e:
            logger.error("Unexpected error in refresh loop", error=str(e))
            await asyncio.sleep(settings.token_refresh_interval)


async def start_refresh_service() -> asyncio.Task:
    """
    Start the background refresh service
    
    Returns:
        The asyncio task running the service
    """
    global refresh_task
    
    if refresh_task and not refresh_task.done():
        logger.warning("Refresh service already running")
        return refresh_task
    
    refresh_task = asyncio.create_task(refresh_service_loop())
    logger.info("Refresh service task created")
    return refresh_task


async def stop_refresh_service(task: Optional[asyncio.Task] = None):
    """
    Stop the background refresh service
    
    Args:
        task: The task to stop (uses global if not provided)
    """
    global refresh_task
    
    task_to_stop = task or refresh_task
    
    if task_to_stop and not task_to_stop.done():
        task_to_stop.cancel()
        try:
            await task_to_stop
        except asyncio.CancelledError:
            pass
        logger.info("Refresh service stopped")
    else:
        logger.debug("No refresh service to stop")
    
    refresh_task = None