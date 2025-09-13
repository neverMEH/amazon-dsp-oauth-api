"""
Amazon OAuth service for user-specific account connections
"""
import httpx
import secrets
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import structlog

from app.config import settings
from app.core.exceptions import TokenRefreshError, RateLimitError

# Define AmazonAuthError if not exists
class AmazonAuthError(Exception):
    """Amazon authentication specific error"""
    pass
from app.schemas.auth import AmazonTokenResponse, AmazonAccountInfo

logger = structlog.get_logger()


class AmazonOAuthService:
    """Handle Amazon OAuth 2.0 operations for user accounts"""
    
    def __init__(self):
        """Initialize Amazon OAuth service"""
        self.client_id = settings.amazon_client_id
        self.client_secret = settings.amazon_client_secret
        self.redirect_uri = settings.amazon_redirect_uri
        self.auth_url = settings.amazon_auth_url
        self.token_url = settings.amazon_token_url
        self.api_base_url = "https://advertising-api.amazon.com"
        
        # Required scopes for Amazon DSP Campaign Insights API
        self.scopes = [
            "advertising::campaign_management",
            "advertising::account_management", 
            "advertising::dsp_campaigns",
            "advertising::reporting"
        ]
        self.scope = " ".join(self.scopes)
    
    def generate_oauth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate Amazon OAuth authorization URL with state token
        
        Args:
            state: Optional custom state token, generates one if not provided
            
        Returns:
            Tuple of (authorization_url, state_token)
        """
        if not state:
            state = secrets.token_urlsafe(24)  # 24 bytes = 32 characters when base64 encoded
        
        params = {
            "client_id": self.client_id,
            "scope": self.scope,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state
        }
        
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{self.auth_url}?{param_str}"
        
        logger.info(
            "Generated Amazon OAuth URL",
            client_id=self.client_id[:10] + "...",
            scopes=self.scopes,
            state=state[:10] + "..."
        )
        
        return auth_url, state
    
    async def validate_state(self, provided_state: str, expected_state: str) -> bool:
        """
        Validate OAuth state token for CSRF protection
        
        Args:
            provided_state: State token from callback
            expected_state: Expected state token
            
        Returns:
            True if states match
            
        Raises:
            AmazonAuthError: If states don't match
        """
        if provided_state != expected_state:
            logger.warning(
                "State token mismatch",
                provided=provided_state[:10] + "...",
                expected=expected_state[:10] + "..."
            )
            raise AmazonAuthError("Invalid state token - possible CSRF attack")
        
        return True
    
    async def exchange_code_for_tokens(
        self, 
        authorization_code: str, 
        state: str
    ) -> AmazonTokenResponse:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            authorization_code: The authorization code from Amazon
            state: The state token for logging
            
        Returns:
            AmazonTokenResponse with token information
            
        Raises:
            AmazonAuthError: If token exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "AmazonDSPOAuthAPI/1.0"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit during token exchange", retry_after=retry_after)
                    raise AmazonAuthError(f"Rate limit exceeded. Retry after {retry_after} seconds.")
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error_description", "Unknown error")
                    error_code = error_data.get("error", "unknown_error")
                    
                    logger.error(
                        "Token exchange failed",
                        status_code=response.status_code,
                        error=error_data,
                        state=state[:10] + "..."
                    )
                    
                    # Use AmazonAuthError for invalid_grant and other auth errors
                    if error_code in ["invalid_grant", "invalid_request", "access_denied"]:
                        raise AmazonAuthError(f"Token exchange failed: {error_msg}")
                    else:
                        raise AmazonAuthError(f"Token exchange failed: {error_msg}")
                
                token_data = response.json()
                
                logger.info(
                    "Successfully exchanged authorization code for tokens",
                    expires_in=token_data.get("expires_in", 3600),
                    token_type=token_data.get("token_type", "bearer")
                )
                
                return AmazonTokenResponse(
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    token_type=token_data.get("token_type", "bearer"),
                    expires_in=token_data.get("expires_in", 3600),
                    scope=token_data.get("scope", self.scope)
                )
                
        except httpx.TimeoutException:
            logger.error("Token exchange timeout")
            raise AmazonAuthError("Request timeout during token exchange")
        except httpx.RequestError as e:
            logger.error("Token exchange network error", error=str(e))
            raise AmazonAuthError(f"Network error during token exchange: {str(e)}")
        except AmazonAuthError:
            # Re-raise AmazonAuthError as-is
            raise
        except Exception as e:
            logger.error("Unexpected error during token exchange", error=str(e))
            raise AmazonAuthError(f"Unexpected error: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> AmazonTokenResponse:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            AmazonTokenResponse with refreshed token information
            
        Raises:
            TokenRefreshError: If token refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "AmazonDSPOAuthAPI/1.0"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit during token refresh", retry_after=retry_after)
                    raise TokenRefreshError(f"Rate limit exceeded. Retry after {retry_after} seconds.")
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error_description", "Unknown error")
                    error_code = error_data.get("error", "unknown_error")
                    
                    logger.error(
                        "Token refresh failed",
                        status_code=response.status_code,
                        error=error_data
                    )
                    
                    # Include error code in the message for better debugging
                    raise TokenRefreshError(f"{error_code}: {error_msg}")
                
                token_data = response.json()
                
                logger.info("Successfully refreshed access token")
                
                return AmazonTokenResponse(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", refresh_token),
                    token_type=token_data.get("token_type", "bearer"),
                    expires_in=token_data.get("expires_in", 3600),
                    scope=token_data.get("scope", self.scope)
                )
                
        except httpx.TimeoutException:
            logger.error("Token refresh timeout")
            raise TokenRefreshError("Request timeout during token refresh")
        except httpx.RequestError as e:
            logger.error("Token refresh network error", error=str(e))
            raise TokenRefreshError(f"Network error during token refresh: {str(e)}")
        except TokenRefreshError:
            # Re-raise TokenRefreshError as-is
            raise
        except Exception as e:
            logger.error("Unexpected error during token refresh", error=str(e))
            raise TokenRefreshError(f"Unexpected error: {str(e)}")
    
    async def get_user_profiles(self, access_token: str) -> List[AmazonAccountInfo]:
        """
        Get user's Amazon advertising profiles
        
        Args:
            access_token: Valid Amazon access token
            
        Returns:
            List of AmazonAccountInfo objects
            
        Raises:
            AmazonAuthError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "AmazonDSPOAuthAPI/1.0",
            "Amazon-Advertising-API-ClientId": self.client_id
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base_url}/v2/profiles",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit during profile fetch", retry_after=retry_after)
                    raise AmazonAuthError(f"TOO_MANY_REQUESTS: Retry after {retry_after} seconds")
                
                if response.status_code == 401:
                    logger.error("Unauthorized access to profiles API")
                    raise AmazonAuthError("UNAUTHORIZED: Invalid or expired access token")
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Failed to fetch profiles",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise AmazonAuthError(f"API request failed: {error_data}")
                
                profiles_data = response.json()
                profiles = []
                
                for profile in profiles_data:
                    profiles.append(AmazonAccountInfo(
                        profile_id=profile["profileId"],
                        country_code=profile["countryCode"],
                        currency_code=profile["currencyCode"], 
                        timezone=profile.get("timezone", "UTC"),
                        account_info=profile.get("accountInfo", {})
                    ))
                
                logger.info(f"Successfully fetched {len(profiles)} profiles")
                return profiles
                
        except httpx.TimeoutException:
            logger.error("Profiles fetch timeout")
            raise AmazonAuthError("Request timeout during profiles fetch")
        except httpx.RequestError as e:
            logger.error("Profiles fetch network error", error=str(e))
            raise AmazonAuthError(f"Network error during profiles fetch: {str(e)}")
        except AmazonAuthError:
            # Re-raise AmazonAuthError as-is
            raise
        except Exception as e:
            logger.error("Unexpected error during profiles fetch", error=str(e))
            raise AmazonAuthError(f"Unexpected error: {str(e)}")


# Create singleton instance
amazon_oauth_service = AmazonOAuthService()