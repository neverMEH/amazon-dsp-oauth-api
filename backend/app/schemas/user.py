"""
User schemas for API validation
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr = Field(..., description="User's email address")
    first_name: Optional[str] = Field(None, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User's last name")
    profile_image_url: Optional[str] = Field(None, description="URL to user's profile image")


class UserCreate(UserBase):
    """Schema for creating a new user"""
    clerk_user_id: str = Field(..., description="Unique identifier from Clerk")
    
    class Config:
        json_schema_extra = {
            "example": {
                "clerk_user_id": "user_2abc123def456",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "profile_image_url": "https://example.com/avatar.jpg"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    profile_image_url: Optional[str] = None
    last_login_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Jane",
                "last_name": "Smith",
                "profile_image_url": "https://example.com/new-avatar.jpg"
            }
        }


class UserResponse(UserBase):
    """Schema for user response"""
    id: str = Field(..., description="User's UUID")
    clerk_user_id: str = Field(..., description="Clerk user identifier")
    created_at: datetime = Field(..., description="When the user was created")
    updated_at: datetime = Field(..., description="When the user was last updated")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "clerk_user_id": "user_2abc123def456",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "profile_image_url": "https://example.com/avatar.jpg",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
                "last_login_at": "2025-01-15T14:20:00Z"
            }
        }


class UserWithAccounts(UserResponse):
    """User response with associated Amazon accounts"""
    amazon_accounts: List["AmazonAccountResponse"] = Field(
        default_factory=list,
        description="List of connected Amazon accounts"
    )
    
    class Config:
        from_attributes = True


# Import at the end to avoid circular dependency
from app.schemas.amazon_account import AmazonAccountResponse
UserWithAccounts.model_rebuild()