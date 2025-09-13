"""
Webhook endpoints for Clerk integration
"""
from fastapi import APIRouter, HTTPException, status, Request, Response
from typing import Dict, Any
import json
import structlog

from app.services.clerk_service import ClerkWebhookHandler
from app.middleware.clerk_auth import verify_clerk_webhook

logger = structlog.get_logger()
router = APIRouter()

# Initialize webhook handler
webhook_handler = ClerkWebhookHandler()


@router.post("/clerk")
async def handle_clerk_webhook(request: Request):
    """
    Handle Clerk webhook events
    
    This endpoint receives webhook events from Clerk for user lifecycle management:
    - user.created: When a new user signs up
    - user.updated: When user profile is updated
    - user.deleted: When user is deleted
    - session.created: When user logs in
    - session.ended: When user logs out
    
    Returns:
        Success response
    """
    try:
        # Get raw body and headers
        body = await request.body()
        headers = dict(request.headers)
        
        logger.info("Received Clerk webhook", headers=headers)
        
        # Verify webhook signature
        if not webhook_handler.verify_webhook(body.decode(), headers):
            logger.error("Webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse event data
        try:
            event_data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook payload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Handle the event
        success = await webhook_handler.handle_event(event_data)
        
        if not success:
            logger.error(f"Failed to handle event: {event_data.get('type')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process webhook event"
            )
        
        logger.info(f"Successfully processed webhook event: {event_data.get('type')}")
        
        return {
            "status": "success",
            "message": "Webhook processed successfully",
            "event_type": event_data.get("type")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/clerk/test")
async def test_clerk_webhook_endpoint():
    """
    Test endpoint to verify webhook configuration
    
    Returns:
        Configuration status
    """
    try:
        webhook_secret_configured = bool(webhook_handler.webhook_secret)
        
        return {
            "status": "ok",
            "webhook_secret_configured": webhook_secret_configured,
            "endpoint": "/api/v1/webhooks/clerk",
            "supported_events": [
                "user.created",
                "user.updated",
                "user.deleted",
                "session.created",
                "session.ended"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error checking webhook configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check webhook configuration"
        )


@router.post("/clerk/sync-user")
async def sync_user_from_clerk(request: Request, user_data: Dict[str, Any]):
    """
    Manual endpoint to sync a specific user from Clerk
    
    This is useful for testing or manual synchronization
    
    Args:
        user_data: Should contain clerk_user_id
        
    Returns:
        Sync result
    """
    try:
        clerk_user_id = user_data.get("clerk_user_id")
        
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="clerk_user_id is required"
            )
        
        # Use the webhook handler to sync user
        from app.services.clerk_service import ClerkService
        clerk_service = ClerkService()
        
        success = await clerk_service.sync_user_with_database(clerk_user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync user"
            )
        
        logger.info(f"Successfully synced user: {clerk_user_id}")
        
        return {
            "status": "success",
            "message": "User synced successfully",
            "clerk_user_id": clerk_user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/clerk/validate")
async def validate_clerk_webhook_payload(request: Request):
    """
    Validate a Clerk webhook payload without processing it
    
    Useful for testing webhook signature verification
    
    Returns:
        Validation result
    """
    try:
        # Get raw body and headers
        body = await request.body()
        headers = dict(request.headers)
        
        # Verify webhook signature
        is_valid = webhook_handler.verify_webhook(body.decode(), headers)
        
        if is_valid:
            # Try to parse the event
            try:
                event_data = json.loads(body)
                event_type = event_data.get("type", "unknown")
                
                return {
                    "status": "valid",
                    "signature_verified": True,
                    "event_type": event_type,
                    "message": "Webhook payload is valid"
                }
            except json.JSONDecodeError:
                return {
                    "status": "invalid",
                    "signature_verified": True,
                    "event_type": None,
                    "message": "Signature valid but invalid JSON"
                }
        else:
            return {
                "status": "invalid",
                "signature_verified": False,
                "event_type": None,
                "message": "Invalid webhook signature"
            }
            
    except Exception as e:
        logger.error(f"Error validating webhook: {str(e)}")
        return {
            "status": "error",
            "signature_verified": False,
            "event_type": None,
            "message": f"Validation error: {str(e)}"
        }