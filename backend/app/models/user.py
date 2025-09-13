"""
User model for Clerk integration
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4


class User:
    """
    User model representing authenticated users via Clerk
    
    This model is designed to work with Supabase's PostgreSQL database
    and integrates with Clerk for authentication.
    """
    
    TABLE_NAME = "users"
    
    def __init__(
        self,
        clerk_user_id: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None
    ):
        """
        Initialize User model
        
        Args:
            clerk_user_id: Unique identifier from Clerk
            email: User's email address
            first_name: User's first name (optional)
            last_name: User's last name (optional)
            profile_image_url: URL to user's profile image (optional)
            id: UUID for database record (auto-generated if not provided)
            created_at: Timestamp when user was created
            updated_at: Timestamp when user was last updated
            last_login_at: Timestamp of last login
        """
        self.id = id or str(uuid4())
        self.clerk_user_id = clerk_user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.profile_image_url = profile_image_url
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_login_at = last_login_at
        self._amazon_accounts: List = []
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split('@')[0]
    
    @property
    def amazon_accounts(self) -> List:
        """Get associated Amazon accounts"""
        return self._amazon_accounts
    
    @amazon_accounts.setter
    def amazon_accounts(self, accounts: List):
        """Set associated Amazon accounts"""
        self._amazon_accounts = accounts
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for database operations"""
        return {
            "id": self.id,
            "clerk_user_id": self.clerk_user_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "profile_image_url": self.profile_image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User instance from dictionary"""
        # Handle datetime conversion
        for field in ["created_at", "updated_at", "last_login_at"]:
            if data.get(field) and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        
        return cls(
            id=data.get("id"),
            clerk_user_id=data["clerk_user_id"],
            email=data["email"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            profile_image_url=data.get("profile_image_url"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_login_at=data.get("last_login_at")
        )
    
    @classmethod
    def create_table_sql(cls) -> str:
        """SQL to create users table"""
        return """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            clerk_user_id VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            profile_image_url TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP WITH TIME ZONE
        );
        
        CREATE INDEX IF NOT EXISTS idx_users_clerk_user_id ON users(clerk_user_id);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.clerk_user_id})>"