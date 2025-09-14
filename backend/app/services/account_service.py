"""
Amazon Advertising Account Management Service
"""
import httpx
import asyncio
from typing import Dict, List, Optional
import structlog
from datetime import datetime, timezone

from app.config import settings
from app.core.exceptions import TokenRefreshError, RateLimitError
from app.core.rate_limiter import ExponentialBackoffRateLimiter, with_rate_limit

logger = structlog.get_logger()


class AmazonAccountService:
    """Handle Amazon Advertising Account Management API operations"""

    def __init__(self):
        """Initialize account service"""
        self.base_url = "https://advertising-api.amazon.com"
        self.api_version = "v2"
        self.rate_limiter = ExponentialBackoffRateLimiter()
        
    async def list_profiles(self, access_token: str, next_token: Optional[str] = None) -> Dict:
        """
        List advertising profiles (accounts) available to the user

        Endpoint Details:
        - URL: GET /v2/profiles
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId

        Args:
            access_token: Valid access token
            next_token: Pagination token for next page

        Returns:
            Dictionary with profiles and pagination info

        Raises:
            TokenRefreshError: If token is invalid
            RateLimitError: If rate limit exceeded
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}/{self.api_version}/profiles"

        # Add pagination parameters
        params = {"maxResults": 100}
        if next_token:
            params["nextToken"] = next_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    logger.error("Unauthorized - token may be expired")
                    raise TokenRefreshError("Access token expired or invalid")
                
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_after = int(retry_after) if retry_after else 60
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    from app.core.rate_limiter import RateLimitError as RLE
                    raise RLE(retry_after)
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to list profiles",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")
                
                data = response.json()

                # Handle both array response and paginated response
                if isinstance(data, list):
                    # Legacy response format
                    profiles = data
                    next_token_response = None
                else:
                    # Paginated response format
                    profiles = data.get("profiles", [])
                    next_token_response = data.get("nextToken")

                # Check for pagination token in headers as well
                if not next_token_response:
                    next_token_response = response.headers.get("X-Amz-Next-Token")

                logger.info(
                    "Successfully retrieved profiles",
                    profile_count=len(profiles),
                    has_next_page=bool(next_token_response)
                )

                return {
                    "profiles": profiles,
                    "nextToken": next_token_response
                }
                
        except httpx.TimeoutException:
            logger.error("Profiles request timeout")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("Profiles request network error", error=str(e))
            raise Exception(f"Network error: {str(e)}")
    
    async def get_profile(self, access_token: str, profile_id: str) -> Dict:
        """
        Get specific profile details
        
        Args:
            access_token: Valid access token
            profile_id: The profile ID to retrieve
            
        Returns:
            Profile dictionary with detailed information
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/{self.api_version}/profiles/{profile_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    logger.error("Unauthorized - token may be expired", profile_id=profile_id)
                    raise TokenRefreshError("Access token expired or invalid")
                
                if response.status_code == 404:
                    logger.error("Profile not found", profile_id=profile_id)
                    raise Exception(f"Profile {profile_id} not found")
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to get profile",
                        profile_id=profile_id,
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")
                
                profile = response.json()
                
                logger.info(
                    "Successfully retrieved profile",
                    profile_id=profile_id,
                    account_info=profile.get("accountInfo", {})
                )
                
                return profile
                
        except httpx.TimeoutException:
            logger.error("Profile request timeout", profile_id=profile_id)
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("Profile request network error", profile_id=profile_id, error=str(e))
            raise Exception(f"Network error: {str(e)}")
    
    async def _list_ads_accounts_raw(self, access_token: str, next_token: Optional[str] = None) -> Dict:
        """
        List all Amazon Advertising accounts using the Account Management API
        
        **Endpoint Details:**
        - URL: POST https://advertising-api.amazon.com/adsAccounts/list
        - Method: POST
        - Version: v1
        - Required Headers: 
            - Authorization: Bearer {access_token}
            - Amazon-Advertising-API-ClientId: {client_id}
            - Content-Type: application/json
        
        **Expected Response (API v3.0):**
        ```json
        {
            "adsAccounts": [
                {
                    "adsAccountId": "string",
                    "accountName": "string",
                    "status": "CREATED|DISABLED|PARTIALLY_CREATED|PENDING",
                    "alternateIds": [
                        {
                            "countryCode": "string",
                            "entityId": "string",
                            "profileId": number
                        }
                    ],
                    "countryCodes": ["US", "CA", "MX"],
                    "errors": {
                        "US": [
                            {
                                "errorId": number,
                                "errorCode": "string",
                                "errorMessage": "string"
                            }
                        ]
                    }
                }
            ],
            "nextToken": "string"
        }
        ```
        
        Args:
            access_token: Valid access token with advertising::account_management scope
            next_token: Optional pagination token

        Returns:
            Dictionary with accounts and pagination info
            
        Raises:
            TokenRefreshError: If token is invalid or expired
            RateLimitError: If rate limit exceeded (429)
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Content-Type": "application/vnd.listaccountsresource.v1+json",
            "Accept": "application/vnd.listaccountsresource.v1+json"  # Accept the correct response type
        }
        
        # Account Management API endpoint - POST /adsAccounts/list
        url = f"{self.base_url}/adsAccounts/list"
        
        # Create request body with pagination token if available
        request_body = {
            "maxResults": 100
        }
        if next_token:
            request_body["nextToken"] = next_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=request_body,
                    timeout=30.0
                )

                if response.status_code == 401:
                    logger.error("Unauthorized - token may be expired")
                    raise TokenRefreshError("Access token expired or invalid")

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_after = int(retry_after) if retry_after else 60
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    from app.core.rate_limiter import RateLimitError as RLE
                    raise RLE(retry_after)

                if response.status_code == 403:
                    logger.error("Forbidden - insufficient permissions")
                    raise Exception("Insufficient permissions for account management API")

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to list advertising accounts",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code} - {error_data}")

                data = response.json()

                # API v3.0 returns "adsAccounts" not "accounts"
                accounts = data.get("adsAccounts", [])
                next_token_response = data.get("nextToken")

                logger.info(
                    "Successfully retrieved advertising accounts",
                    account_count=len(accounts),
                    has_next_page=bool(next_token_response)
                )

                return {
                    "adsAccounts": accounts,  # Return correct field name
                    "nextToken": next_token_response
                }
            
        except httpx.TimeoutException:
            logger.error("Advertising accounts request timeout")
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("Advertising accounts request network error", error=str(e))
            raise Exception(f"Network error: {str(e)}")

    async def list_ads_accounts(self, access_token: str, next_token: Optional[str] = None) -> Dict:
        """
        List Amazon Advertising accounts with automatic retry on rate limits

        This is the public interface that includes rate limiting and retry logic.
        """
        async def _call():
            return await self._list_ads_accounts_raw(access_token, next_token)

        # Use rate limiter for automatic retry
        try:
            return await self.rate_limiter.execute_with_retry(_call)
        except Exception as e:
            # Re-raise the original exception
            if hasattr(e, '__cause__'):
                raise e.__cause__
            raise

    async def list_dsp_accounts(self, access_token: str, profile_id: str) -> List[Dict]:
        """
        List DSP accounts available under a profile
        
        Endpoint Details:
        - URL: GET /dsp/accounts
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId, Amazon-Advertising-API-Scope
        
        Args:
            access_token: Valid access token
            profile_id: The profile ID to scope the request
            
        Returns:
            List of DSP account dictionaries
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/dsp/accounts"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    logger.error("Unauthorized - token may be expired", profile_id=profile_id)
                    raise TokenRefreshError("Access token expired or invalid")
                
                if response.status_code == 403:
                    logger.error("Forbidden - insufficient permissions for DSP", profile_id=profile_id)
                    raise Exception("Insufficient permissions for DSP access")
                
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_after = int(retry_after) if retry_after else 60
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    from app.core.rate_limiter import RateLimitError as RLE
                    raise RLE(retry_after)
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to list DSP accounts",
                        profile_id=profile_id,
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")
                
                accounts = response.json()
                
                logger.info(
                    "Successfully retrieved DSP accounts",
                    profile_id=profile_id,
                    account_count=len(accounts)
                )
                
                return accounts
                
        except httpx.TimeoutException:
            logger.error("DSP accounts request timeout", profile_id=profile_id)
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("DSP accounts request network error", profile_id=profile_id, error=str(e))
            raise Exception(f"Network error: {str(e)}")


# Create singleton instance
account_service = AmazonAccountService()