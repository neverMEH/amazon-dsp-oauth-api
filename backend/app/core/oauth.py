"""
Amazon OAuth client implementation
"""
import httpx
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode
import structlog

from app.config import settings
from app.core.security import generate_state_token
from app.core.exceptions import TokenExchangeError, TokenRefreshError, RateLimitError

logger = structlog.get_logger()


class AmazonOAuthClient:
    """Handle Amazon OAuth 2.0 operations"""
    
    def __init__(self):
        """Initialize OAuth client"""
        self.client_id = settings.amazon_client_id
        self.client_secret = settings.amazon_client_secret
        self.redirect_uri = settings.amazon_redirect_uri
        self.scope = settings.amazon_scope
        self.auth_url = settings.amazon_auth_url
        self.token_url = settings.amazon_token_url
    
    def generate_authorization_url(self) -> Tuple[str, str]:
        """
        Generate Amazon OAuth authorization URL with state token
        
        Returns:
            Tuple of (authorization_url, state_token)
        """
        state_token = generate_state_token()
        
        params = {
            "client_id": self.client_id,
            "scope": self.scope,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state_token
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        logger.info(
            "Generated authorization URL",
            client_id=self.client_id[:10] + "...",
            scope=self.scope,
            state=state_token[:10] + "..."
        )
        
        return auth_url, state_token
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            authorization_code: The authorization code from Amazon
            
        Returns:
            Dict containing access_token, refresh_token, expires_in
            
        Raises:
            TokenExchangeError: If token exchange fails
            RateLimitError: If rate limit is exceeded
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
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit exceeded", retry_after=retry_after)
                    raise RateLimitError(retry_after)
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Token exchange failed",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise TokenExchangeError(
                        error_data.get("error_description", "Unknown error")
                    )
                
                token_data = response.json()
                
                # Calculate expiration timestamp
                expires_at = datetime.utcnow() + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
                
                logger.info("Successfully exchanged code for tokens")
                
                return {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data["refresh_token"],
                    "token_type": token_data.get("token_type", "Bearer"),
                    "expires_at": expires_at.isoformat(),
                    "scope": self.scope
                }
                
        except httpx.TimeoutException:
            logger.error("Token exchange timeout")
            raise TokenExchangeError("Request timeout")
        except httpx.RequestError as e:
            logger.error("Token exchange network error", error=str(e))
            raise TokenExchangeError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error during token exchange", error=str(e))
            raise TokenExchangeError(f"Unexpected error: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Dict containing new access_token, refresh_token, expires_in
            
        Raises:
            TokenRefreshError: If token refresh fails
            RateLimitError: If rate limit is exceeded
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
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit exceeded during refresh", retry_after=retry_after)
                    raise RateLimitError(retry_after)
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "Token refresh failed",
                        status_code=response.status_code,
                        error=error_data
                    )
                    raise TokenRefreshError(
                        error_data.get("error_description", "Unknown error")
                    )
                
                token_data = response.json()
                
                # Calculate expiration timestamp
                expires_at = datetime.utcnow() + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
                
                logger.info("Successfully refreshed access token")
                
                return {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token", refresh_token),
                    "token_type": token_data.get("token_type", "Bearer"),
                    "expires_at": expires_at.isoformat(),
                    "scope": self.scope
                }
                
        except httpx.TimeoutException:
            logger.error("Token refresh timeout")
            raise TokenRefreshError("Request timeout")
        except httpx.RequestError as e:
            logger.error("Token refresh network error", error=str(e))
            raise TokenRefreshError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error during token refresh", error=str(e))
            raise TokenRefreshError(f"Unexpected error: {str(e)}")


# Create singleton instance
oauth_client = AmazonOAuthClient()