"""
Amazon DSP and AMC Account Management Service
"""
import httpx
from typing import Dict, List, Optional
import structlog
from datetime import datetime, timezone

from app.config import settings
from app.core.exceptions import TokenRefreshError, RateLimitError
from app.core.rate_limiter import ExponentialBackoffRateLimiter

logger = structlog.get_logger()


class DSPAMCService:
    """Handle Amazon DSP and AMC account operations"""

    def __init__(self):
        """Initialize DSP/AMC service"""
        self.base_url = "https://advertising-api.amazon.com"
        self.rate_limiter = ExponentialBackoffRateLimiter()

    async def list_dsp_advertisers(
        self,
        access_token: str,
        profile_id: Optional[str] = None
    ) -> List[Dict]:
        """
        List all DSP advertisers accessible to the user

        **Endpoint Details:**
        - URL: GET https://advertising-api.amazon.com/dsp/advertisers
        - Method: GET
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId
        - Optional: Amazon-Advertising-API-Scope (for profile-specific filtering)

        **Response Structure:**
        Returns advertisers array with:
        - advertiserId: Unique DSP entity ID
        - advertiserName: Display name
        - advertiserType: AGENCY or ADVERTISER
        - advertiserStatus: ACTIVE, SUSPENDED, etc.
        - countryCode: Two-letter country code
        - currency: Three-letter currency code
        - timeZone: IANA timezone

        Args:
            access_token: Valid access token with dsp_campaigns scope
            profile_id: Optional profile ID to filter advertisers

        Returns:
            List of DSP advertiser dictionaries

        Raises:
            TokenRefreshError: If token is invalid
            RateLimitError: If rate limit exceeded
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Accept": "application/json"
        }

        # Add profile scope if provided
        if profile_id:
            headers["Amazon-Advertising-API-Scope"] = profile_id

        url = f"{self.base_url}/dsp/advertisers"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 401:
                    logger.error("Unauthorized - token may be expired")
                    raise TokenRefreshError("Access token expired or invalid")

                if response.status_code == 403:
                    logger.warning(
                        "User lacks DSP permissions - this is normal for non-DSP accounts",
                        profile_id=profile_id
                    )
                    # Return empty list but indicate it's due to permissions
                    return []  # User doesn't have DSP access

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    raise RateLimitError(int(retry_after))

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to list DSP advertisers",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")

                data = response.json()
                advertisers = data.get("advertisers", [])

                logger.info(
                    "Successfully retrieved DSP advertisers",
                    advertiser_count=len(advertisers),
                    profile_id=profile_id
                )

                return advertisers

        except httpx.TimeoutException:
            logger.error("DSP advertisers request timeout")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("DSP advertisers request error", error=str(e))
            raise Exception(f"Network error: {str(e)}")

    async def list_amc_instances(self, access_token: str) -> List[Dict]:
        """
        List all AMC instances accessible to the user

        **Endpoint Details:**
        - URL: GET https://advertising-api.amazon.com/amc/instances
        - Method: GET
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId
        - Required Scope: advertising::amc:read

        **Response Structure:**
        Returns instances array with:
        - instanceId: Unique AMC instance identifier
        - instanceName: Display name
        - instanceType: STANDARD or PREMIUM
        - status: ACTIVE, PROVISIONING, SUSPENDED
        - region: AWS region
        - createdDate: ISO 8601 timestamp
        - dataRetentionDays: Data retention period
        - advertisers: Array of linked advertisers

        **Common Issues:**
        - 403: User doesn't have AMC access (requires special provisioning)
        - 401: Token expired or missing amc:read scope

        Args:
            access_token: Valid access token with amc:read scope

        Returns:
            List of AMC instance dictionaries

        Raises:
            TokenRefreshError: If token is invalid
            RateLimitError: If rate limit exceeded
        """
        # AMC instances might require advertiser IDs, but let's try without first
        # If it fails with missing entityId, we'll need to get DSP advertisers first
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        url = f"{self.base_url}/amc/instances"

        try:
            async with httpx.AsyncClient() as client:
                # First try without parameters
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 401:
                    logger.error("Unauthorized - token may be expired or missing amc:read scope")
                    raise TokenRefreshError("Access token expired or missing AMC scope")

                if response.status_code == 403:
                    logger.warning(
                        "User lacks AMC permissions - AMC requires special provisioning"
                    )
                    # Return empty list but indicate it's due to permissions
                    return []  # User doesn't have AMC access

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    raise RateLimitError(int(retry_after))

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to list AMC instances",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")

                data = response.json()
                instances = data.get("instances", [])

                logger.info(
                    "Successfully retrieved AMC instances",
                    instance_count=len(instances)
                )

                return instances

        except httpx.TimeoutException:
            logger.error("AMC instances request timeout")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("AMC instances request error", error=str(e))
            raise Exception(f"Network error: {str(e)}")

    async def get_dsp_advertiser_details(
        self,
        access_token: str,
        advertiser_id: str
    ) -> Dict:
        """
        Get detailed information for a specific DSP advertiser

        **Endpoint Details:**
        - URL: GET https://advertising-api.amazon.com/dsp/advertisers/{advertiserId}
        - Method: GET

        Args:
            access_token: Valid access token
            advertiser_id: DSP advertiser ID

        Returns:
            Advertiser details dictionary
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Accept": "application/json"
        }

        url = f"{self.base_url}/dsp/advertisers/{advertiser_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 404:
                    logger.error("DSP advertiser not found", advertiser_id=advertiser_id)
                    raise Exception(f"Advertiser {advertiser_id} not found")

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to get DSP advertiser details",
                        advertiser_id=advertiser_id,
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")

                advertiser = response.json()

                logger.info(
                    "Successfully retrieved DSP advertiser details",
                    advertiser_id=advertiser_id
                )

                return advertiser

        except httpx.TimeoutException:
            logger.error("DSP advertiser details request timeout")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("DSP advertiser details request error", error=str(e))
            raise Exception(f"Network error: {str(e)}")

    async def list_advertiser_seats(
        self,
        access_token: str,
        advertiser_id: str,
        exchange_ids: Optional[List[str]] = None,
        max_results: int = 200,
        next_token: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> Dict:
        """
        List current seats for DSP advertisers by exchange

        **Endpoint Details:**
        - URL: POST /dsp/v1/seats/advertisers/current/list
        - Method: POST
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId, Amazon-Ads-AccountId
        - Optional: Amazon-Advertising-API-Scope (for profile filtering)

        **Response Structure:**
        {
            "advertiserSeats": [
                {
                    "advertiserId": "string",
                    "currentSeats": [
                        {
                            "exchangeId": "string",
                            "exchangeName": "string",
                            "dealCreationId": "string",  # Optional
                            "spendTrackingId": "string"  # Optional
                        }
                    ]
                }
            ],
            "nextToken": "string"  # For pagination
        }

        Args:
            access_token: Valid access token with dsp_campaigns scope
            advertiser_id: DSP Advertiser ID (required for Amazon-Ads-AccountId header)
            exchange_ids: Optional list of exchange IDs to filter
            max_results: Maximum results (1-200)
            next_token: Pagination token
            profile_id: Optional profile ID for additional filtering

        Returns:
            Dictionary containing advertiser seats information

        Raises:
            TokenRefreshError: If token is invalid
            RateLimitError: If rate limit exceeded
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Ads-AccountId": advertiser_id,  # REQUIRED
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Add optional profile scope
        if profile_id:
            headers["Amazon-Advertising-API-Scope"] = profile_id

        # Build request payload
        payload = {
            "maxResults": min(max_results, 200)  # Ensure within bounds
        }

        if exchange_ids:
            payload["exchangeIdFilter"] = exchange_ids

        if next_token:
            payload["nextToken"] = next_token

        url = f"{self.base_url}/dsp/v1/seats/advertisers/current/list"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 401:
                    logger.error("Unauthorized - token may be expired")
                    raise TokenRefreshError("Access token expired or invalid")

                if response.status_code == 403:
                    logger.warning(
                        "User lacks DSP Seats API permissions",
                        advertiser_id=advertiser_id
                    )
                    # Return empty result indicating permission issue
                    return {
                        "advertiserSeats": [],
                        "error": "Insufficient permissions for DSP Seats API"
                    }

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    raise RateLimitError(int(retry_after))

                if response.status_code == 400:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Bad request - check advertiser ID and parameters",
                        advertiser_id=advertiser_id,
                        error=error_data
                    )
                    raise ValueError(f"Invalid request: {error_data}")

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to list advertiser seats",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")

                data = response.json()

                logger.info(
                    "Successfully retrieved advertiser seats",
                    advertiser_id=advertiser_id,
                    seat_count=len(data.get("advertiserSeats", [])),
                    has_more=bool(data.get("nextToken"))
                )

                return data

        except httpx.TimeoutException:
            logger.error("Advertiser seats request timeout")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("Advertiser seats request error", error=str(e))
            raise Exception(f"Network error: {str(e)}")

    async def list_all_account_types(
        self,
        access_token: str,
        include_regular: bool = True,
        include_dsp: bool = True,
        include_amc: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve all account types in parallel

        This method fetches regular advertising accounts, DSP advertisers,
        and AMC instances in parallel for optimal performance.

        Args:
            access_token: Valid access token
            include_regular: Include regular advertising accounts
            include_dsp: Include DSP advertisers
            include_amc: Include AMC instances

        Returns:
            Dictionary with keys:
            - advertising_accounts: Regular accounts
            - dsp_advertisers: DSP advertisers
            - amc_instances: AMC instances
        """
        import asyncio
        from app.services.account_service import account_service

        tasks = []
        task_names = []

        if include_regular:
            tasks.append(account_service.list_ads_accounts(access_token))
            task_names.append("advertising_accounts")

        if include_dsp:
            tasks.append(self.list_dsp_advertisers(access_token))
            task_names.append("dsp_advertisers")

        if include_amc:
            tasks.append(self.list_amc_instances(access_token))
            task_names.append("amc_instances")

        # Execute all requests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        account_data = {}
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {name}", error=str(result))
                account_data[name] = []
            else:
                if name == "advertising_accounts":
                    # Extract accounts from the response structure
                    account_data[name] = result.get("adsAccounts", [])
                else:
                    account_data[name] = result

        # Calculate totals
        total_accounts = sum(len(accounts) for accounts in account_data.values())

        logger.info(
            "Retrieved all account types",
            advertising_count=len(account_data.get("advertising_accounts", [])),
            dsp_count=len(account_data.get("dsp_advertisers", [])),
            amc_count=len(account_data.get("amc_instances", [])),
            total=total_accounts
        )

        return account_data


# Create singleton instance
dsp_amc_service = DSPAMCService()