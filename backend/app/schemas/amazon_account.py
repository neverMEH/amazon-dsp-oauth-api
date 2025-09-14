"""
Amazon Account schemas for API validation
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime


class AmazonAccountBase(BaseModel):
    """Base Amazon account schema"""
    account_name: str = Field(..., description="Display name for the account")
    marketplace_id: Optional[str] = Field(None, description="Amazon marketplace ID")
    account_type: Literal["advertising", "vendor", "seller"] = Field(
        "advertising",
        description="Type of Amazon account"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional account metadata"
    )


class AmazonAccountCreate(AmazonAccountBase):
    """Schema for creating a new Amazon account connection"""
    user_id: str = Field(..., description="User ID who owns this account")
    amazon_account_id: str = Field(..., description="Amazon's account identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_name": "My Amazon Store",
                "amazon_account_id": "ENTITY123456",
                "marketplace_id": "ATVPDKIKX0DER",
                "account_type": "advertising",
                "metadata": {
                    "advertiser_id": "ADV123456",
                    "profile_ids": ["PROF1", "PROF2"]
                }
            }
        }


class AmazonAccountUpdate(BaseModel):
    """Schema for updating Amazon account information"""
    account_name: Optional[str] = None
    is_default: Optional[bool] = None
    status: Optional[Literal["active", "inactive", "suspended", "pending"]] = None
    metadata: Optional[Dict[str, Any]] = None
    last_synced_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "account_name": "Updated Store Name",
                "is_default": True,
                "status": "active"
            }
        }


class AmazonAccountResponse(AmazonAccountBase):
    """Schema for Amazon account response"""
    id: str = Field(..., description="Account UUID")
    user_id: str = Field(..., description="Owner user ID")
    amazon_account_id: str = Field(..., description="Amazon account identifier")
    is_default: bool = Field(False, description="Whether this is the default account")
    status: Literal["active", "inactive", "suspended", "pending"] = Field(
        "active",
        description="Account status"
    )
    connected_at: datetime = Field(..., description="When the account was connected")
    last_synced_at: Optional[datetime] = Field(None, description="Last successful sync")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_name": "My Amazon Store",
                "amazon_account_id": "ENTITY123456",
                "marketplace_id": "ATVPDKIKX0DER",
                "account_type": "advertising",
                "is_default": True,
                "status": "active",
                "connected_at": "2025-01-15T10:30:00Z",
                "last_synced_at": "2025-01-15T14:20:00Z",
                "metadata": {
                    "advertiser_id": "ADV123456"
                }
            }
        }


class AmazonAccountWithTokens(AmazonAccountResponse):
    """Amazon account with associated OAuth tokens"""
    has_valid_token: bool = Field(..., description="Whether account has valid OAuth token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    
    class Config:
        from_attributes = True


class AmazonAccountDetail(AmazonAccountResponse):
    """Detailed Amazon account information including profiles and health status"""
    profiles: Optional[list] = Field(default_factory=list, description="Associated advertising profiles")
    health_status: Optional[str] = Field(None, description="Account health status")
    last_refresh_time: Optional[str] = Field(None, description="Last token refresh time")
    token_expires_in: Optional[str] = Field(None, description="Time until token expiration")
    needs_reauth: bool = Field(False, description="Whether account needs re-authorization")
    
    class Config:
        from_attributes = True


class AccountHealthStatus(BaseModel):
    """Account health and token status"""
    account_id: str = Field(..., description="Account UUID")
    status: Literal["healthy", "warning", "expired", "error"] = Field(..., description="Health status")
    token_expires_in: str = Field(..., description="Time until token expiration")
    last_refresh: str = Field(..., description="Time since last refresh")
    needs_reauth: bool = Field(..., description="Whether re-authorization is needed")
    message: Optional[str] = Field(None, description="Additional status message")


class AccountDisconnectRequest(BaseModel):
    """Request to disconnect an Amazon account"""
    revoke_tokens: bool = Field(False, description="Whether to revoke OAuth tokens on disconnect")
    reason: Optional[str] = Field(None, description="Reason for disconnection")


class AccountReauthorizeRequest(BaseModel):
    """Request to re-authorize an Amazon account"""
    force: bool = Field(False, description="Force re-authorization even if token is valid")
    redirect_uri: Optional[str] = Field(None, description="Custom redirect URI after re-authorization")


class UserPreferences(BaseModel):
    """User preferences for account management"""
    notifications_enabled: bool = Field(True, description="Enable notifications")
    auto_refresh_tokens: bool = Field(True, description="Automatically refresh expiring tokens")
    default_account_id: Optional[str] = Field(None, description="Default account ID")
    dashboard_layout: Literal["grid", "list"] = Field("grid", description="Dashboard layout preference")
    timezone: str = Field("UTC", description="User timezone")


class UserSettings(BaseModel):
    """User settings response"""
    user_id: str = Field(..., description="User ID")
    preferences: UserPreferences = Field(..., description="User preferences")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")