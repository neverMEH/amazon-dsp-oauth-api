"""
Account Addition Service - Simplified wrapper for account type specific operations
"""
from typing import Dict, Any, Optional
import structlog

from app.services.account_sync_service import account_sync_service

logger = structlog.get_logger()


class AccountService:
    """
    Service for handling account-type-specific addition operations.
    This is a simplified wrapper around account_sync_service methods
    for the new OAuth flow endpoints.
    """

    async def fetch_and_store_sponsored_ads(
        self,
        user_id: str,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch and store Sponsored Ads accounts

        Args:
            user_id: Database user ID
            access_token: Valid Amazon access token

        Returns:
            Dictionary with accounts and count
        """
        return await account_sync_service.fetch_and_store_sponsored_ads(
            user_id=user_id,
            access_token=access_token
        )

    async def fetch_and_store_dsp_advertisers(
        self,
        user_id: str,
        access_token: str,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch and store DSP advertisers

        Args:
            user_id: Database user ID
            access_token: Valid Amazon access token
            profile_id: Optional profile ID for scope

        Returns:
            Dictionary with advertisers and count
        """
        return await account_sync_service.fetch_and_store_dsp_advertisers(
            user_id=user_id,
            access_token=access_token,
            profile_id=profile_id
        )

    async def delete_account(
        self,
        user_id: str,
        account_id: str
    ) -> Dict[str, Any]:
        """
        Delete an account from the database

        Args:
            user_id: Database user ID
            account_id: Account ID to delete

        Returns:
            Dictionary with success status
        """
        return await account_sync_service.delete_account(
            user_id=user_id,
            account_id=account_id
        )


# Create singleton instance
account_service = AccountService()