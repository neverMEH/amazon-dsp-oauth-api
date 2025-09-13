"""
Amazon Advertising Account Management Service
"""
import httpx
from typing import Dict, List, Optional
import structlog
from datetime import datetime, timezone

from app.config import settings
from app.core.exceptions import TokenRefreshError, RateLimitError

logger = structlog.get_logger()


class AmazonAccountService:
    """Handle Amazon Advertising Account Management API operations"""
    
    def __init__(self):
        """Initialize account service"""
        self.base_url = "https://advertising-api.amazon.com"
        self.api_version = "v2"
        
    async def list_profiles(self, access_token: str) -> List[Dict]:
        """
        List advertising profiles (accounts) available to the user
        
        Endpoint Details:
        - URL: GET /v2/profiles
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId
        
        Args:
            access_token: Valid access token
            
        Returns:
            List of profile dictionaries containing account information
            
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
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    raise RateLimitError(retry_after)
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to list profiles",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise Exception(f"API Error: {response.status_code}")
                
                profiles = response.json()
                
                logger.info(
                    "Successfully retrieved profiles",
                    profile_count=len(profiles)
                )
                
                return profiles
                
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
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    raise RateLimitError(retry_after)
                
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