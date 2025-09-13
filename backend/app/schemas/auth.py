"""
Authentication schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
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