"""
Account Query Service for efficient metadata queries
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog

from app.db.base import get_supabase_client
from app.models.amazon_account import AmazonAccount

logger = structlog.get_logger()


class AccountQueryService:
    """
    Service for querying account metadata efficiently

    Provides methods to:
    - Query accounts by country code
    - Get profile IDs for specific countries
    - Filter accounts by status
    - Find accounts with errors
    - Get account statistics
    """

    def __init__(self):
        """Initialize the query service"""
        self.supabase = None

    def _get_client(self):
        """Get or create Supabase client"""
        if not self.supabase:
            self.supabase = get_supabase_client()
        return self.supabase

    async def get_accounts_by_country(
        self,
        user_id: str,
        country_code: str
    ) -> List[Dict[str, Any]]:
        """
        Get all accounts that have profiles in a specific country

        Args:
            user_id: Database user ID
            country_code: Two-letter country code (e.g., 'US', 'CA')

        Returns:
            List of account dictionaries with profile information
        """
        try:
            client = self._get_client()

            # Query accounts with the country code in their alternateIds
            result = client.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).execute()

            matching_accounts = []

            for account_data in result.data:
                account = AmazonAccount.from_dict(account_data)
                alternate_ids = account.metadata.get("alternate_ids", [])

                # Find profiles for the specified country
                country_profiles = [
                    alt for alt in alternate_ids
                    if alt.get("countryCode") == country_code
                ]

                if country_profiles:
                    account_info = account.to_dict()
                    account_info["country_profiles"] = country_profiles
                    matching_accounts.append(account_info)

            logger.info(
                f"Found {len(matching_accounts)} accounts with {country_code} profiles",
                user_id=user_id
            )

            return matching_accounts

        except Exception as e:
            logger.error(f"Error querying accounts by country", error=str(e))
            raise

    async def get_profile_id_for_country(
        self,
        user_id: str,
        amazon_account_id: str,
        country_code: str
    ) -> Optional[int]:
        """
        Get the profile ID for a specific account and country

        Args:
            user_id: Database user ID
            amazon_account_id: Amazon account ID (adsAccountId)
            country_code: Two-letter country code

        Returns:
            Profile ID or None if not found
        """
        try:
            client = self._get_client()

            result = client.table("user_accounts").select("metadata").eq(
                "user_id", user_id
            ).eq(
                "amazon_account_id", amazon_account_id
            ).execute()

            if result.data:
                metadata = result.data[0].get("metadata", {})
                alternate_ids = metadata.get("alternate_ids", [])

                for alt in alternate_ids:
                    if alt.get("countryCode") == country_code:
                        return alt.get("profileId")

            return None

        except Exception as e:
            logger.error(f"Error getting profile ID", error=str(e))
            return None

    async def get_accounts_with_errors(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all accounts that have errors (PARTIALLY_CREATED status)

        Args:
            user_id: Database user ID

        Returns:
            List of accounts with error details
        """
        try:
            client = self._get_client()

            # Query accounts with partial status or errors in metadata
            result = client.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).in_("status", ["partial", "failed"]).execute()

            accounts_with_errors = []

            for account_data in result.data:
                account = AmazonAccount.from_dict(account_data)
                errors = account.metadata.get("errors", {})

                if errors:
                    error_summary = {
                        "account_id": account.id,
                        "account_name": account.account_name,
                        "amazon_account_id": account.amazon_account_id,
                        "status": account.status,
                        "error_countries": list(errors.keys()),
                        "error_details": errors
                    }
                    accounts_with_errors.append(error_summary)

            # Also check for accounts with errors in metadata regardless of status
            all_accounts = client.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).execute()

            for account_data in all_accounts.data:
                account = AmazonAccount.from_dict(account_data)
                errors = account.metadata.get("errors", {})

                if errors and account.id not in [a["account_id"] for a in accounts_with_errors]:
                    error_summary = {
                        "account_id": account.id,
                        "account_name": account.account_name,
                        "amazon_account_id": account.amazon_account_id,
                        "status": account.status,
                        "error_countries": list(errors.keys()),
                        "error_details": errors
                    }
                    accounts_with_errors.append(error_summary)

            logger.info(
                f"Found {len(accounts_with_errors)} accounts with errors",
                user_id=user_id
            )

            return accounts_with_errors

        except Exception as e:
            logger.error(f"Error querying accounts with errors", error=str(e))
            raise

    async def get_account_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics about user's accounts

        Args:
            user_id: Database user ID

        Returns:
            Dictionary with account statistics
        """
        try:
            client = self._get_client()

            result = client.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).execute()

            if not result.data:
                return {
                    "total_accounts": 0,
                    "status_breakdown": {},
                    "country_coverage": [],
                    "profiles_count": 0,
                    "accounts_with_errors": 0
                }

            accounts = [AmazonAccount.from_dict(d) for d in result.data]

            # Status breakdown
            status_breakdown = {}
            for account in accounts:
                status = account.status
                status_breakdown[status] = status_breakdown.get(status, 0) + 1

            # Country coverage
            all_countries = set()
            total_profiles = 0

            for account in accounts:
                country_codes = account.metadata.get("country_codes", [])
                all_countries.update(country_codes)

                alternate_ids = account.metadata.get("alternate_ids", [])
                total_profiles += len(alternate_ids)

            # Accounts with errors
            accounts_with_errors = sum(
                1 for account in accounts
                if account.metadata.get("errors", {})
            )

            # Last sync times
            sync_times = [
                account.last_synced_at for account in accounts
                if account.last_synced_at
            ]

            last_sync = max(sync_times) if sync_times else None
            oldest_sync = min(sync_times) if sync_times else None

            return {
                "total_accounts": len(accounts),
                "status_breakdown": status_breakdown,
                "country_coverage": sorted(list(all_countries)),
                "profiles_count": total_profiles,
                "accounts_with_errors": accounts_with_errors,
                "last_sync": last_sync.isoformat() if last_sync else None,
                "oldest_sync": oldest_sync.isoformat() if oldest_sync else None,
                "never_synced": len(accounts) - len(sync_times)
            }

        except Exception as e:
            logger.error(f"Error getting account statistics", error=str(e))
            raise

    async def search_accounts(
        self,
        user_id: str,
        search_term: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        country_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search accounts with multiple filters

        Args:
            user_id: Database user ID
            search_term: Search in account name or ID
            status_filter: List of statuses to filter by
            country_filter: Country code to filter by

        Returns:
            List of matching accounts
        """
        try:
            client = self._get_client()

            # Start with base query
            query = client.table("user_accounts").select("*").eq("user_id", user_id)

            # Apply status filter
            if status_filter:
                query = query.in_("status", status_filter)

            result = query.execute()
            accounts = [AmazonAccount.from_dict(d) for d in result.data]

            # Apply search term filter
            if search_term:
                search_lower = search_term.lower()
                accounts = [
                    acc for acc in accounts
                    if search_lower in acc.account_name.lower() or
                    search_lower in acc.amazon_account_id.lower()
                ]

            # Apply country filter
            if country_filter:
                filtered_accounts = []
                for account in accounts:
                    country_codes = account.metadata.get("country_codes", [])
                    if country_filter in country_codes:
                        filtered_accounts.append(account)
                accounts = filtered_accounts

            return [acc.to_dict() for acc in accounts]

        except Exception as e:
            logger.error(f"Error searching accounts", error=str(e))
            raise

    async def get_accounts_needing_refresh(
        self,
        user_id: str,
        hours_threshold: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get accounts that haven't been synced recently

        Args:
            user_id: Database user ID
            hours_threshold: Hours since last sync

        Returns:
            List of accounts needing refresh
        """
        try:
            client = self._get_client()

            result = client.table("user_accounts").select("*").eq(
                "user_id", user_id
            ).execute()

            accounts_needing_refresh = []
            current_time = datetime.now(timezone.utc)

            for account_data in result.data:
                account = AmazonAccount.from_dict(account_data)

                # Check if never synced
                if not account.last_synced_at:
                    accounts_needing_refresh.append(account.to_dict())
                    continue

                # Check if sync is old
                time_since_sync = current_time - account.last_synced_at
                hours_since_sync = time_since_sync.total_seconds() / 3600

                if hours_since_sync > hours_threshold:
                    account_dict = account.to_dict()
                    account_dict["hours_since_sync"] = round(hours_since_sync, 1)
                    accounts_needing_refresh.append(account_dict)

            logger.info(
                f"Found {len(accounts_needing_refresh)} accounts needing refresh",
                user_id=user_id
            )

            return accounts_needing_refresh

        except Exception as e:
            logger.error(f"Error finding accounts needing refresh", error=str(e))
            raise


# Create singleton instance
account_query_service = AccountQueryService()