"""
Account Synchronization Service for batch operations with Amazon Ads API v3.0
"""
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import structlog
from uuid import uuid4

from app.models.amazon_account import AmazonAccount
from app.services.account_service import account_service
from app.services.token_service import token_service
from app.db.base import get_supabase_client
from app.core.exceptions import TokenRefreshError, RateLimitError

logger = structlog.get_logger()


class AccountSyncService:
    """
    Service for synchronizing Amazon Advertising accounts with local database

    Handles:
    - Batch account retrieval from Amazon API
    - Conflict resolution for existing accounts
    - Account creation and updates
    - Sync status tracking
    - Error handling and recovery
    """

    def __init__(self):
        """Initialize the sync service"""
        self.supabase = None
        self._sync_in_progress = {}  # Track active syncs per user

    async def sync_user_accounts(
        self,
        user_id: str,
        access_token: str,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronize all accounts for a user from Amazon Ads API

        Args:
            user_id: Database user ID
            access_token: Valid Amazon access token
            force_update: Force update even if recently synced

        Returns:
            Dictionary with sync results and statistics
        """
        # Check if sync is already in progress for this user
        if user_id in self._sync_in_progress:
            logger.warning("Sync already in progress for user", user_id=user_id)
            return {
                "status": "in_progress",
                "message": "Sync already in progress for this user"
            }

        self._sync_in_progress[user_id] = True
        sync_start = datetime.now(timezone.utc)

        try:
            # Initialize Supabase client if needed
            if not self.supabase:
                self.supabase = get_supabase_client()

            # Check if we need to sync (unless forced)
            if not force_update:
                should_sync = await self._should_sync_accounts(user_id)
                if not should_sync:
                    return {
                        "status": "skipped",
                        "message": "Accounts recently synced",
                        "last_sync": await self._get_last_sync_time(user_id)
                    }

            # Fetch all accounts from Amazon API (with pagination)
            all_accounts = await self._fetch_all_accounts(access_token)

            # Process and store accounts
            sync_results = await self._process_accounts(user_id, all_accounts)

            # Record sync history
            await self._record_sync_history(
                user_id=user_id,
                sync_type="manual" if force_update else "scheduled",
                sync_results=sync_results,
                sync_start=sync_start
            )

            logger.info(
                "Account sync completed",
                user_id=user_id,
                total_accounts=sync_results["total"],
                created=sync_results["created"],
                updated=sync_results["updated"],
                failed=sync_results["failed"]
            )

            return {
                "status": "success",
                "results": sync_results,
                "sync_time": (datetime.now(timezone.utc) - sync_start).total_seconds()
            }

        except TokenRefreshError as e:
            logger.error("Token refresh error during sync", user_id=user_id, error=str(e))
            return {
                "status": "error",
                "error": "authentication_failed",
                "message": "Token expired. Please re-authenticate."
            }

        except RateLimitError as e:
            logger.warning("Rate limit hit during sync", user_id=user_id, retry_after=e.retry_after)
            return {
                "status": "error",
                "error": "rate_limited",
                "message": f"Rate limit exceeded. Retry after {e.retry_after} seconds",
                "retry_after": e.retry_after
            }

        except Exception as e:
            logger.error("Unexpected error during sync", user_id=user_id, error=str(e))
            return {
                "status": "error",
                "error": "sync_failed",
                "message": str(e)
            }

        finally:
            # Clear sync lock
            self._sync_in_progress.pop(user_id, None)

    async def _fetch_all_accounts(self, access_token: str) -> List[Dict]:
        """
        Fetch all accounts from Amazon API with pagination

        Args:
            access_token: Valid access token

        Returns:
            List of all account dictionaries
        """
        all_accounts = []
        next_token = None
        page_count = 0
        max_pages = 10  # Safety limit

        while page_count < max_pages:
            try:
                response = await account_service.list_ads_accounts(
                    access_token=access_token,
                    next_token=next_token
                )

                accounts = response.get("adsAccounts", [])
                all_accounts.extend(accounts)

                next_token = response.get("nextToken")
                page_count += 1

                logger.debug(
                    "Fetched account page",
                    page=page_count,
                    accounts_in_page=len(accounts),
                    has_next=bool(next_token)
                )

                # If no next token, we've fetched all accounts
                if not next_token:
                    break

                # Small delay between pages to avoid rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching accounts page {page_count}", error=str(e))
                # If we have some accounts, return what we got
                if all_accounts:
                    break
                raise

        logger.info(f"Fetched {len(all_accounts)} total accounts across {page_count} pages")
        return all_accounts

    async def _process_accounts(
        self,
        user_id: str,
        accounts: List[Dict]
    ) -> Dict[str, Any]:
        """
        Process and store accounts in database

        Args:
            user_id: Database user ID
            accounts: List of account data from API

        Returns:
            Dictionary with processing statistics
        """
        created = 0
        updated = 0
        failed = 0
        errors = []

        for account_data in accounts:
            try:
                success, was_created = await self._upsert_account(user_id, account_data)

                if success:
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                errors.append({
                    "account_id": account_data.get("adsAccountId"),
                    "error": str(e)
                })
                logger.error(
                    "Failed to process account",
                    account_id=account_data.get("adsAccountId"),
                    error=str(e)
                )

        return {
            "total": len(accounts),
            "created": created,
            "updated": updated,
            "failed": failed,
            "errors": errors if errors else None
        }

    async def _upsert_account(
        self,
        user_id: str,
        account_data: Dict
    ) -> Tuple[bool, bool]:
        """
        Create or update a single account

        Args:
            user_id: Database user ID
            account_data: Account data from API

        Returns:
            Tuple of (success, was_created)
        """
        # Extract data for v3.0 format
        amazon_account_id = account_data.get("adsAccountId")
        alternate_ids = account_data.get("alternateIds", [])
        first_alternate = alternate_ids[0] if alternate_ids else {}

        # Map API status to database status
        status_map = {
            "CREATED": "active",
            "PARTIALLY_CREATED": "partial",
            "PENDING": "pending",
            "DISABLED": "disabled"
        }
        api_status = account_data.get("status", "CREATED")

        # Check if account exists
        existing = self.supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "amazon_account_id", amazon_account_id
        ).execute()

        account_dict = {
            "user_id": user_id,
            "account_name": account_data.get("accountName", "Unknown"),
            "amazon_account_id": amazon_account_id,
            "marketplace_id": first_alternate.get("entityId"),
            "account_type": "advertiser",
            "status": status_map.get(api_status, "active"),
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "alternate_ids": alternate_ids,
                "country_codes": account_data.get("countryCodes", []),
                "errors": account_data.get("errors", {}),
                "profile_id": first_alternate.get("profileId"),
                "country_code": first_alternate.get("countryCode"),
                "api_status": api_status
            }
        }

        if not existing.data:
            # Create new account
            account_dict["id"] = str(uuid4())
            account_dict["connected_at"] = datetime.now(timezone.utc).isoformat()

            result = self.supabase.table("user_accounts").insert(account_dict).execute()
            return (bool(result.data), True)
        else:
            # Update existing account
            # Preserve existing metadata and merge with new
            existing_metadata = existing.data[0].get("metadata", {})
            account_dict["metadata"] = {**existing_metadata, **account_dict["metadata"]}

            result = self.supabase.table("user_accounts").update(
                account_dict
            ).eq("id", existing.data[0]["id"]).execute()

            return (bool(result.data), False)

    async def _should_sync_accounts(self, user_id: str) -> bool:
        """
        Check if accounts should be synced based on last sync time

        Args:
            user_id: Database user ID

        Returns:
            True if sync should proceed, False if recently synced
        """
        # Check last sync time
        last_sync = await self._get_last_sync_time(user_id)

        if not last_sync:
            return True  # Never synced

        # Sync if last sync was more than 1 hour ago
        sync_threshold = timedelta(hours=1)
        time_since_sync = datetime.now(timezone.utc) - last_sync

        return time_since_sync > sync_threshold

    async def _get_last_sync_time(self, user_id: str) -> Optional[datetime]:
        """
        Get the last successful sync time for a user

        Args:
            user_id: Database user ID

        Returns:
            Last sync datetime or None
        """
        result = self.supabase.table("user_accounts").select(
            "last_synced_at"
        ).eq(
            "user_id", user_id
        ).order(
            "last_synced_at", desc=True
        ).limit(1).execute()

        if result.data and result.data[0].get("last_synced_at"):
            return datetime.fromisoformat(
                result.data[0]["last_synced_at"].replace('Z', '+00:00')
            )

        return None

    async def _record_sync_history(
        self,
        user_id: str,
        sync_type: str,
        sync_results: Dict,
        sync_start: datetime
    ) -> None:
        """
        Record sync operation in history table

        Args:
            user_id: Database user ID
            sync_type: Type of sync (manual, scheduled, webhook)
            sync_results: Results from sync operation
            sync_start: When sync started
        """
        try:
            # Get the first account to link the sync history
            accounts_result = self.supabase.table("user_accounts").select("id").eq(
                "user_id", user_id
            ).limit(1).execute()

            user_account_id = accounts_result.data[0]["id"] if accounts_result.data else None

            history_record = {
                "id": str(uuid4()),
                "user_account_id": user_account_id,
                "sync_type": sync_type,
                "sync_status": "success" if sync_results.get("failed", 0) == 0 else "partial",
                "started_at": sync_start.isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "accounts_synced": sync_results.get("created", 0) + sync_results.get("updated", 0),
                "accounts_failed": sync_results.get("failed", 0),
                "error_details": sync_results.get("errors"),
                "metadata": {
                    "total_accounts": sync_results.get("total", 0),
                    "created": sync_results.get("created", 0),
                    "updated": sync_results.get("updated", 0)
                }
            }

            self.supabase.table("account_sync_history").insert(history_record).execute()

        except Exception as e:
            logger.error("Failed to record sync history", user_id=user_id, error=str(e))

    async def get_sync_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get current sync status for a user

        Args:
            user_id: Database user ID

        Returns:
            Dictionary with sync status information
        """
        is_syncing = user_id in self._sync_in_progress
        last_sync = await self._get_last_sync_time(user_id)

        # Get account statistics
        accounts_result = self.supabase.table("user_accounts").select(
            "status"
        ).eq("user_id", user_id).execute()

        account_stats = {
            "total": len(accounts_result.data) if accounts_result.data else 0,
            "active": sum(1 for a in accounts_result.data if a["status"] == "active"),
            "partial": sum(1 for a in accounts_result.data if a["status"] == "partial"),
            "disabled": sum(1 for a in accounts_result.data if a["status"] == "disabled"),
            "pending": sum(1 for a in accounts_result.data if a["status"] == "pending")
        }

        return {
            "is_syncing": is_syncing,
            "last_sync": last_sync.isoformat() if last_sync else None,
            "next_sync": (last_sync + timedelta(hours=1)).isoformat() if last_sync else None,
            "account_statistics": account_stats
        }


# Create singleton instance
account_sync_service = AccountSyncService()