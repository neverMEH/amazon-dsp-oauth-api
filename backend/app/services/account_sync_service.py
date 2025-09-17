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
            # Initialize Supabase client if needed - use service client to bypass RLS
            if not self.supabase:
                from app.db.base import get_supabase_service_client
                self.supabase = get_supabase_service_client()

            # Check if we need to sync (unless forced)
            if not force_update:
                should_sync = await self._should_sync_accounts(user_id)
                if not should_sync:
                    return {
                        "status": "skipped",
                        "message": "Accounts recently synced",
                        "last_sync": await self._get_last_sync_time(user_id)
                    }

            # Fetch ALL account types (SP, DSP, AMC) from Amazon APIs
            all_accounts = await self._fetch_all_account_types(access_token)

            # Process and store all account types
            sync_results = await self._process_all_account_types(user_id, all_accounts)

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

    async def _fetch_all_account_types(self, access_token: str) -> Dict[str, List[Dict]]:
        """
        Fetch all account types (SP, DSP, AMC) from Amazon APIs

        Args:
            access_token: Valid access token

        Returns:
            Dictionary with lists for each account type
        """
        from app.services.dsp_amc_service import dsp_amc_service

        try:
            # Fetch all account types in parallel
            account_data = await dsp_amc_service.list_all_account_types(
                access_token=access_token,
                include_regular=True,
                include_dsp=True,
                include_amc=True
            )

            logger.info(
                "Fetched all account types",
                advertising_count=len(account_data.get("advertising_accounts", [])),
                dsp_count=len(account_data.get("dsp_advertisers", [])),
                amc_count=len(account_data.get("amc_instances", []))
            )

            return account_data

        except Exception as e:
            logger.error(f"Error fetching account types", error=str(e))
            # Return structure with empty lists on error
            return {
                "advertising_accounts": [],
                "dsp_advertisers": [],
                "amc_instances": []
            }

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

    async def _process_all_account_types(
        self,
        user_id: str,
        account_data: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """
        Process and store all account types in database

        Args:
            user_id: Database user ID
            account_data: Dictionary with lists for each account type

        Returns:
            Dictionary with processing statistics
        """
        created = 0
        updated = 0
        failed = 0
        errors = []
        stats_by_type = {
            "advertising": {"created": 0, "updated": 0, "failed": 0},
            "dsp": {"created": 0, "updated": 0, "failed": 0},
            "amc": {"created": 0, "updated": 0, "failed": 0}
        }

        # Process advertising accounts
        for account in account_data.get("advertising_accounts", []):
            try:
                success, was_created = await self._upsert_advertising_account(user_id, account)
                if success:
                    if was_created:
                        created += 1
                        stats_by_type["advertising"]["created"] += 1
                    else:
                        updated += 1
                        stats_by_type["advertising"]["updated"] += 1
                else:
                    failed += 1
                    stats_by_type["advertising"]["failed"] += 1
            except Exception as e:
                failed += 1
                stats_by_type["advertising"]["failed"] += 1
                errors.append({
                    "account_id": account.get("adsAccountId"),
                    "type": "advertising",
                    "error": str(e)
                })
                logger.error(
                    "Failed to process advertising account",
                    account_id=account.get("adsAccountId"),
                    error=str(e)
                )

        # Process DSP advertisers
        for advertiser in account_data.get("dsp_advertisers", []):
            try:
                success, was_created = await self._upsert_dsp_account(user_id, advertiser)
                if success:
                    if was_created:
                        created += 1
                        stats_by_type["dsp"]["created"] += 1
                    else:
                        updated += 1
                        stats_by_type["dsp"]["updated"] += 1
                else:
                    failed += 1
                    stats_by_type["dsp"]["failed"] += 1
            except Exception as e:
                failed += 1
                stats_by_type["dsp"]["failed"] += 1
                errors.append({
                    "account_id": advertiser.get("advertiserId"),
                    "type": "dsp",
                    "error": str(e)
                })
                logger.error(
                    "Failed to process DSP advertiser",
                    advertiser_id=advertiser.get("advertiserId"),
                    error=str(e)
                )

        # Process AMC instances
        for instance in account_data.get("amc_instances", []):
            try:
                success, was_created = await self._upsert_amc_instance(user_id, instance)
                if success:
                    if was_created:
                        created += 1
                        stats_by_type["amc"]["created"] += 1
                    else:
                        updated += 1
                        stats_by_type["amc"]["updated"] += 1
                else:
                    failed += 1
                    stats_by_type["amc"]["failed"] += 1
            except Exception as e:
                failed += 1
                stats_by_type["amc"]["failed"] += 1
                errors.append({
                    "account_id": instance.get("instanceId"),
                    "type": "amc",
                    "error": str(e)
                })
                logger.error(
                    "Failed to process AMC instance",
                    instance_id=instance.get("instanceId"),
                    error=str(e)
                )

        total = len(account_data.get("advertising_accounts", [])) + \
                len(account_data.get("dsp_advertisers", [])) + \
                len(account_data.get("amc_instances", []))

        logger.info(
            "Processed all account types",
            total=total,
            created=created,
            updated=updated,
            failed=failed,
            stats_by_type=stats_by_type
        )

        return {
            "total": total,
            "created": created,
            "updated": updated,
            "failed": failed,
            "errors": errors if errors else None,
            "stats_by_type": stats_by_type
        }

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
                success, was_created = await self._upsert_advertising_account(user_id, account_data)

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

    async def _upsert_advertising_account(
        self,
        user_id: str,
        account_data: Dict
    ) -> Tuple[bool, bool]:
        """
        Create or update a single advertising account

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
            "account_type": "advertising",  # Correctly set to advertising
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

    async def _upsert_dsp_account(
        self,
        user_id: str,
        advertiser_data: Dict
    ) -> Tuple[bool, bool]:
        """
        Create or update a DSP advertiser account

        Args:
            user_id: Database user ID
            advertiser_data: DSP advertiser data from API

        Returns:
            Tuple of (success, was_created)
        """
        amazon_account_id = advertiser_data.get("advertiserId")

        # Handle both old and new response formats
        # New format: name, country, timezone
        # Old format: advertiserName, countryCode, timeZone
        advertiser_name = advertiser_data.get("name") or advertiser_data.get("advertiserName", "Unknown DSP")
        country = advertiser_data.get("country") or advertiser_data.get("countryCode")
        timezone = advertiser_data.get("timezone") or advertiser_data.get("timeZone")

        # Map DSP status to database status
        status_map = {
            "ACTIVE": "active",
            "SUSPENDED": "suspended",
            "INACTIVE": "inactive"
        }
        # Status might not be in new format, default to active
        api_status = advertiser_data.get("advertiserStatus", "ACTIVE")

        # Check if account exists
        existing = self.supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "amazon_account_id", amazon_account_id
        ).execute()

        account_dict = {
            "user_id": user_id,
            "account_name": advertiser_name,
            "amazon_account_id": amazon_account_id,
            "marketplace_id": country,
            "account_type": "dsp",  # Set type to DSP
            "status": status_map.get(api_status, "active"),
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                # Store all fields from the API response
                "advertiser_type": advertiser_data.get("advertiserType"),
                "country": country,
                "country_code": country,  # Keep for backward compatibility
                "currency": advertiser_data.get("currency"),
                "timezone": timezone,
                "url": advertiser_data.get("url"),
                "profile_id": advertiser_data.get("profileId"),  # Added by our fetch method
                "created_date": advertiser_data.get("createdDate"),
                "api_status": api_status,
                # Store original response for debugging
                "raw_response": advertiser_data
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
            existing_metadata = existing.data[0].get("metadata", {})
            account_dict["metadata"] = {**existing_metadata, **account_dict["metadata"]}

            result = self.supabase.table("user_accounts").update(
                account_dict
            ).eq("id", existing.data[0]["id"]).execute()

            return (bool(result.data), False)

    async def _upsert_amc_instance(
        self,
        user_id: str,
        instance_data: Dict
    ) -> Tuple[bool, bool]:
        """
        Create or update an AMC instance account

        Args:
            user_id: Database user ID
            instance_data: AMC instance data from API

        Returns:
            Tuple of (success, was_created)
        """
        amazon_account_id = instance_data.get("instanceId")

        # Map AMC status to database status
        status_map = {
            "ACTIVE": "active",
            "PROVISIONING": "provisioning",
            "SUSPENDED": "suspended"
        }
        api_status = instance_data.get("status", "ACTIVE")

        # Get first linked advertiser if available
        linked_advertisers = instance_data.get("advertisers", [])
        first_advertiser = linked_advertisers[0] if linked_advertisers else {}

        # Check if account exists
        existing = self.supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq(
            "amazon_account_id", amazon_account_id
        ).execute()

        account_dict = {
            "user_id": user_id,
            "account_name": instance_data.get("instanceName", "Unknown AMC"),
            "amazon_account_id": amazon_account_id,
            "marketplace_id": instance_data.get("region"),
            "account_type": "amc",  # Set type to AMC
            "status": status_map.get(api_status, "active"),
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "instance_type": instance_data.get("instanceType"),
                "region": instance_data.get("region"),
                "data_retention_days": instance_data.get("dataRetentionDays"),
                "created_date": instance_data.get("createdDate"),
                "linked_advertisers": linked_advertisers,
                "primary_advertiser_id": first_advertiser.get("advertiserId"),
                "primary_advertiser_name": first_advertiser.get("advertiserName"),
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