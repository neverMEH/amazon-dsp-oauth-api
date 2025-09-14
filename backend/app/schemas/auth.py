"""
Authentication schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class LoginResponse(BaseModel):
    """OAuth login initiation response"""
    auth_url: str = Field(..., description="Amazon OAuth authorization URL")
    state: str = Field(..., description="CSRF state token")
    expires_in: int = Field(default=600, description="State token expiration in seconds")


class CallbackRequest(BaseModel):
    """OAuth callback request parameters"""
    code: str = Field(..., description="Authorization code from Amazon")
    state: str = Field(..., description="CSRF state token for validation")
    error: Optional[str] = Field(None, description="Error code if authorization failed")
    error_description: Optional[str] = Field(None, description="Error description")


class TokenInfo(BaseModel):
    """Token information"""
    token_id: str = Field(..., description="Token record ID")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    scope: str = Field(..., description="OAuth scope")
    refresh_count: Optional[int] = Field(0, description="Number of times token has been refreshed")


class CallbackResponse(BaseModel):
    """OAuth callback success response"""
    status: str = Field(default="success", description="Operation status")
    message: str = Field(default="Authentication successful", description="Success message")
    token_info: TokenInfo = Field(..., description="Token information")


class AuthStatus(BaseModel):
    """Current authentication status"""
    authenticated: bool = Field(..., description="Whether user is authenticated")
    token_valid: bool = Field(..., description="Whether token is valid")
    expires_at: Optional[datetime] = Field(None, description="Token expiration")
    refresh_count: int = Field(default=0, description="Number of refreshes")
    last_refresh: Optional[datetime] = Field(None, description="Last refresh timestamp")
    scope: str = Field(..., description="OAuth scope")


class RefreshResponse(BaseModel):
    """Token refresh response"""
    status: str = Field(default="success", description="Operation status")
    message: str = Field(default="Token refreshed successfully", description="Success message")
    new_expiry: datetime = Field(..., description="New token expiration")
    refresh_count: int = Field(..., description="Total refresh count")


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: dict = Field(..., description="Error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "INVALID_STATE_TOKEN",
                    "message": "The state token is invalid or has expired",
                    "details": {
                        "provided_state": "xyz789",
                        "timestamp": "2025-01-01T12:00:00Z"
                    }
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy", description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    version: str = Field(..., description="API version")
    services: dict = Field(..., description="Service statuses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-01T12:00:00Z",
                "version": "1.0.0",
                "services": {
                    "database": "connected",
                    "token_refresh": "running",
                    "last_refresh": "2025-01-01T11:55:00Z"
                }
            }
        }


class AmazonTokenResponse(BaseModel):
    """Amazon OAuth token response"""
    access_token: str = Field(..., description="Amazon access token")
    refresh_token: str = Field(..., description="Amazon refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    scope: str = Field(..., description="Granted OAuth scopes")


class AmazonAccountInfo(BaseModel):
    """Amazon advertising account information"""
    profile_id: int = Field(..., description="Amazon profile ID")
    country_code: str = Field(..., description="Account country code")
    currency_code: str = Field(..., description="Account currency code")
    timezone: str = Field(default="UTC", description="Account timezone")
    account_info: Dict[str, Any] = Field(default={}, description="Additional account metadata")


class AmazonConnectionRequest(BaseModel):
    """Amazon account connection request"""
    user_id: str = Field(..., description="Clerk user ID")
    profile_id: int = Field(..., description="Amazon profile ID to connect")


class AmazonConnectionStatus(BaseModel):
    """Amazon account connection status"""
    connected: bool = Field(..., description="Whether account is connected")
    profile_id: Optional[int] = Field(None, description="Amazon profile ID")
    needs_refresh: bool = Field(default=False, description="Whether token needs refresh")
    expires_at: Optional[datetime] = Field(None, description="Token expiration")
    last_updated: Optional[datetime] = Field(None, description="Last connection update")
    error: Optional[str] = Field(None, description="Connection error message")


class AmazonDisconnectionRequest(BaseModel):
    """Amazon account disconnection request"""
    user_id: str = Field(..., description="Clerk user ID") 
    profile_id: int = Field(..., description="Amazon profile ID to disconnect")