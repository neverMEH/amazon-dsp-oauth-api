"""
User settings and preferences schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class UserPreferences(BaseModel):
    """User preference settings"""
    notifications_enabled: bool = Field(default=True, description="Enable all notifications")
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    auto_refresh_tokens: bool = Field(default=True, description="Automatically refresh expiring tokens")
    refresh_interval_hours: int = Field(default=6, ge=1, le=24, description="Token refresh check interval")
    default_account_id: Optional[str] = Field(default=None, description="Default Amazon account ID")
    dashboard_layout: Literal["grid", "list", "compact"] = Field(default="grid", description="Dashboard layout preference")
    items_per_page: int = Field(default=20, ge=5, le=100, description="Number of items per page")
    timezone: str = Field(default="UTC", description="User timezone")
    date_format: Literal["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"] = Field(default="MM/DD/YYYY", description="Date format preference")
    time_format: Literal["12h", "24h"] = Field(default="12h", description="Time format preference")
    theme: Literal["light", "dark", "system"] = Field(default="system", description="UI theme preference")
    show_expired_accounts: bool = Field(default=True, description="Show expired accounts in list")
    show_disconnected_accounts: bool = Field(default=False, description="Show disconnected accounts")
    auto_expand_details: bool = Field(default=False, description="Auto-expand account details")
    enable_keyboard_shortcuts: bool = Field(default=True, description="Enable keyboard shortcuts")


class UserSettingsResponse(BaseModel):
    """User settings response"""
    user_id: str = Field(..., description="User ID")
    preferences: UserPreferences = Field(..., description="User preferences")
    updated_at: str = Field(..., description="Last update timestamp")
    created_at: str = Field(..., description="Creation timestamp")


class UserSettingsUpdate(BaseModel):
    """User settings update request"""
    preferences: Optional[UserPreferences] = Field(None, description="Updated preferences")


class DefaultSettings(BaseModel):
    """Default settings configuration"""
    preferences: UserPreferences = Field(..., description="Default preferences")
    available_timezones: List[str] = Field(..., description="Available timezone options")
    available_layouts: List[str] = Field(..., description="Available layout options")
    available_themes: List[str] = Field(..., description="Available theme options")