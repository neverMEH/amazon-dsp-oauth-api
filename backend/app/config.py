"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings"""
    
    # Amazon OAuth
    amazon_security_profile_id: str
    amazon_client_id: str
    amazon_client_secret: str
    amazon_oauth_redirect_uri: Optional[str] = None
    amazon_scope: str = "advertising::campaign_management advertising::account_management advertising::dsp_campaigns advertising::reporting"
    
    # Encryption
    fernet_key: str
    
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # Clerk Authentication
    clerk_publishable_key: Optional[str] = None
    clerk_secret_key: Optional[str] = None
    clerk_webhook_secret: Optional[str] = None
    clerk_api_url: str = "https://api.clerk.com/v1"
    
    # Application
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    
    @property
    def amazon_redirect_uri(self) -> str:
        """Get the redirect URI, defaulting to backend_url if not set"""
        if self.amazon_oauth_redirect_uri:
            return self.amazon_oauth_redirect_uri
        return f"{self.backend_url}/api/v1/auth/amazon/callback"
    admin_key: str = "dev_admin_key"
    
    # Server
    port: int = 8000
    
    # OAuth URLs
    amazon_auth_url: str = "https://www.amazon.com/ap/oa"
    amazon_token_url: str = "https://api.amazon.com/auth/o2/token"
    
    # Token settings
    token_refresh_interval: int = 60  # seconds
    token_refresh_buffer: int = 300  # seconds before expiry to trigger refresh
    max_refresh_retries: int = 5
    retry_backoff_base: int = 2
    
    # API Version
    api_version: str = "1.0.1"
    
    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Create settings instance
settings = Settings()