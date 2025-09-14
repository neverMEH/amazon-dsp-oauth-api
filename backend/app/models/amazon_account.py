"""
Amazon Account model for managing connected Amazon Advertising accounts
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4


class AmazonAccount:
    """
    Model representing a connected Amazon Advertising account
    
    This model stores the relationship between users and their Amazon accounts,
    including OAuth tokens and account metadata.
    """
    
    TABLE_NAME = "user_accounts"
    
    def __init__(
        self,
        user_id: str,
        account_name: str,
        amazon_account_id: str,
        marketplace_id: Optional[str] = None,
        account_type: str = "advertising",
        is_default: bool = False,
        status: str = "active",
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        connected_at: Optional[datetime] = None,
        last_synced_at: Optional[datetime] = None
    ):
        """
        Initialize AmazonAccount model
        
        Args:
            user_id: Foreign key to users table
            account_name: Display name for the account
            amazon_account_id: Amazon's account identifier
            marketplace_id: Amazon marketplace ID (e.g., ATVPDKIKX0DER for US)
            account_type: Type of account (advertising, vendor, seller)
            is_default: Whether this is the user's default account
            status: Account status (active, inactive, suspended, pending)
            metadata: Additional account metadata (JSON)
            id: UUID for database record
            connected_at: When the account was first connected
            last_synced_at: Last successful sync timestamp
        """
        self.id = id or str(uuid4())
        self.user_id = user_id
        self.account_name = account_name
        self.amazon_account_id = amazon_account_id
        self.marketplace_id = marketplace_id
        self.account_type = account_type
        self.is_default = is_default
        self.status = status
        self.metadata = metadata or {}
        self.connected_at = connected_at or datetime.now(timezone.utc)
        self.last_synced_at = last_synced_at
    
    @property
    def is_active(self) -> bool:
        """Check if account is active"""
        return self.status == "active"
    
    @property
    def marketplace_name(self) -> str:
        """Get human-readable marketplace name"""
        marketplace_map = {
            "ATVPDKIKX0DER": "United States",
            "A2EUQ1WTGCTBG2": "Canada",
            "A1AM78C64UM0Y8": "Mexico",
            "A2Q3Y263D00KWC": "Brazil",
            "A1RKKUPIHCS9HS": "Spain",
            "A1F83G8C2ARO7P": "United Kingdom",
            "A13V1IB3VIYZZH": "France",
            "APJ6JRA9NG5V4": "Italy",
            "A1PA6795UKMFR9": "Germany",
            "A1805IZSGTT6HS": "Netherlands",
            "A2NODRKZP88ZB9": "Sweden",
            "A1C3SOZRARQ6R3": "Poland",
            "ARBP9OOSHTCHU": "Egypt",
            "A33AVAJ2PDY3EV": "Turkey",
            "A39IBJ37TRP1C6": "Australia",
            "A21TJRUUN4KGV": "India",
            "A19VAU5U5O7RUS": "Singapore",
            "A2VIGQ35RCS4UG": "United Arab Emirates",
            "AAHKV2X7AFYLW": "China",
            "A1VC38T7YXB528": "Japan"
        }
        return marketplace_map.get(self.marketplace_id, "Unknown")
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for database operations"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_name": self.account_name,
            "amazon_account_id": self.amazon_account_id,
            "marketplace_id": self.marketplace_id,
            "account_type": self.account_type,
            "is_default": self.is_default,
            "status": self.status,
            "metadata": self.metadata,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AmazonAccount":
        """Create AmazonAccount instance from dictionary"""
        # Handle datetime conversion
        for field in ["connected_at", "last_synced_at"]:
            if data.get(field) and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            account_name=data["account_name"],
            amazon_account_id=data["amazon_account_id"],
            marketplace_id=data.get("marketplace_id"),
            account_type=data.get("account_type", "advertising"),
            is_default=data.get("is_default", False),
            status=data.get("status", "active"),
            metadata=data.get("metadata", {}),
            connected_at=data.get("connected_at"),
            last_synced_at=data.get("last_synced_at")
        )
    
    @classmethod
    def create_table_sql(cls) -> str:
        """SQL to create user_accounts table"""
        return """
        CREATE TABLE IF NOT EXISTS user_accounts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            account_name VARCHAR(255) NOT NULL,
            amazon_account_id VARCHAR(255) NOT NULL,
            marketplace_id VARCHAR(50),
            account_type VARCHAR(50) DEFAULT 'advertising',
            is_default BOOLEAN DEFAULT FALSE,
            status VARCHAR(50) DEFAULT 'active',
            connected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_synced_at TIMESTAMP WITH TIME ZONE,
            metadata JSONB DEFAULT '{}',
            UNIQUE(user_id, amazon_account_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_accounts_user_id ON user_accounts(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_accounts_status ON user_accounts(status);
        """
    
    def __repr__(self) -> str:
        return f"<AmazonAccount {self.account_name} ({self.amazon_account_id})>"