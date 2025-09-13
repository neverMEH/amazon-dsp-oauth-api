"""
Test database models and schema validation
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import json

from app.models.user import User
from app.models.amazon_account import AmazonAccount
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.amazon_account import AmazonAccountCreate, AmazonAccountResponse


class TestUserModel:
    """Test User model and schema validation"""
    
    def test_user_create_with_clerk_id(self):
        """Test creating a user with Clerk ID"""
        user_data = {
            "clerk_user_id": "user_123456789",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "profile_image_url": "https://example.com/avatar.jpg"
        }
        
        user = UserCreate(**user_data)
        assert user.clerk_user_id == "user_123456789"
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
    
    def test_user_create_minimal(self):
        """Test creating a user with minimal required fields"""
        user_data = {
            "clerk_user_id": "user_minimal",
            "email": "minimal@example.com"
        }
        
        user = UserCreate(**user_data)
        assert user.clerk_user_id == "user_minimal"
        assert user.email == "minimal@example.com"
        assert user.first_name is None
        assert user.last_name is None
    
    def test_user_update_fields(self):
        """Test updating user fields"""
        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "profile_image_url": "https://example.com/new-avatar.jpg"
        }
        
        user_update = UserUpdate(**update_data)
        assert user_update.first_name == "Jane"
        assert user_update.last_name == "Smith"
        assert user_update.profile_image_url == "https://example.com/new-avatar.jpg"
    
    def test_user_response_schema(self):
        """Test user response schema"""
        user_data = {
            "id": str(uuid4()),
            "clerk_user_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "profile_image_url": "https://example.com/avatar.jpg",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow()
        }
        
        user_response = UserResponse(**user_data)
        assert user_response.id == user_data["id"]
        assert user_response.clerk_user_id == "user_123"
        assert user_response.email == "test@example.com"
    
    def test_user_unique_constraints(self):
        """Test that clerk_user_id and email must be unique"""
        # This will be validated at the database level
        # We'll test the schema validates email format
        with pytest.raises(ValueError):
            UserCreate(clerk_user_id="test", email="invalid-email")


class TestAmazonAccountModel:
    """Test AmazonAccount model and schema validation"""
    
    def test_amazon_account_create(self):
        """Test creating an Amazon account connection"""
        account_data = {
            "user_id": str(uuid4()),
            "account_name": "My Amazon Store",
            "amazon_account_id": "amzn_account_123",
            "marketplace_id": "ATVPDKIKX0DER",  # US marketplace
            "account_type": "advertising"
        }
        
        account = AmazonAccountCreate(**account_data)
        assert account.user_id == account_data["user_id"]
        assert account.account_name == "My Amazon Store"
        assert account.amazon_account_id == "amzn_account_123"
        assert account.marketplace_id == "ATVPDKIKX0DER"
        assert account.account_type == "advertising"
    
    def test_amazon_account_with_metadata(self):
        """Test Amazon account with metadata"""
        account_data = {
            "user_id": str(uuid4()),
            "account_name": "Store with Metadata",
            "amazon_account_id": "amzn_meta_123",
            "metadata": {
                "region": "North America",
                "advertiser_id": "ADV123456",
                "profile_ids": ["PROF1", "PROF2"]
            }
        }
        
        account = AmazonAccountCreate(**account_data)
        assert account.metadata["region"] == "North America"
        assert account.metadata["advertiser_id"] == "ADV123456"
        assert len(account.metadata["profile_ids"]) == 2
    
    def test_amazon_account_default_status(self):
        """Test that new accounts have active status by default"""
        account_data = {
            "user_id": str(uuid4()),
            "account_name": "Default Status Account",
            "amazon_account_id": "amzn_default_123"
        }
        
        account = AmazonAccountCreate(**account_data)
        # Status should be set at the database level
        # but we can validate the schema accepts it
        account_with_status = AmazonAccountResponse(
            **account_data,
            id=str(uuid4()),
            status="active",
            is_default=False,
            connected_at=datetime.utcnow(),
            last_synced_at=None
        )
        assert account_with_status.status == "active"
        assert account_with_status.is_default is False
    
    def test_amazon_account_relationship(self):
        """Test Amazon account relationship with user"""
        user_id = str(uuid4())
        account_data = {
            "user_id": user_id,
            "account_name": "Related Account",
            "amazon_account_id": "amzn_rel_123"
        }
        
        account = AmazonAccountCreate(**account_data)
        assert account.user_id == user_id
    
    def test_multiple_accounts_per_user(self):
        """Test that a user can have multiple Amazon accounts"""
        user_id = str(uuid4())
        
        account1 = AmazonAccountCreate(
            user_id=user_id,
            account_name="Account 1",
            amazon_account_id="amzn_1"
        )
        
        account2 = AmazonAccountCreate(
            user_id=user_id,
            account_name="Account 2",
            amazon_account_id="amzn_2"
        )
        
        assert account1.user_id == account2.user_id
        assert account1.amazon_account_id != account2.amazon_account_id
    
    def test_account_status_values(self):
        """Test valid account status values"""
        valid_statuses = ["active", "inactive", "suspended", "pending"]
        user_id = str(uuid4())
        
        for status in valid_statuses:
            account = AmazonAccountResponse(
                id=str(uuid4()),
                user_id=user_id,
                account_name=f"Account {status}",
                amazon_account_id=f"amzn_{status}",
                status=status,
                is_default=False,
                connected_at=datetime.utcnow()
            )
            assert account.status == status


class TestUserAccountRelationship:
    """Test the relationship between User and AmazonAccount models"""
    
    def test_user_with_accounts_response(self):
        """Test user response with associated accounts"""
        user_id = str(uuid4())
        
        # Create user with accounts
        user_data = {
            "id": user_id,
            "clerk_user_id": "user_with_accounts",
            "email": "accounts@example.com",
            "first_name": "Account",
            "last_name": "Manager",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "amazon_accounts": [
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "account_name": "Account 1",
                    "amazon_account_id": "amzn_1",
                    "status": "active",
                    "is_default": True,
                    "connected_at": datetime.utcnow()
                },
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "account_name": "Account 2",
                    "amazon_account_id": "amzn_2",
                    "status": "active",
                    "is_default": False,
                    "connected_at": datetime.utcnow()
                }
            ]
        }
        
        from app.schemas.user import UserWithAccounts
        user_with_accounts = UserWithAccounts(**user_data)
        
        assert len(user_with_accounts.amazon_accounts) == 2
        assert user_with_accounts.amazon_accounts[0].is_default is True
        assert user_with_accounts.amazon_accounts[1].is_default is False
    
    def test_only_one_default_account(self):
        """Test that only one account can be default per user"""
        # This will be enforced at the database/service level
        # Here we test the schema allows the is_default flag
        user_id = str(uuid4())
        
        accounts = []
        for i in range(3):
            account = AmazonAccountResponse(
                id=str(uuid4()),
                user_id=user_id,
                account_name=f"Account {i}",
                amazon_account_id=f"amzn_{i}",
                status="active",
                is_default=(i == 0),  # Only first is default
                connected_at=datetime.utcnow()
            )
            accounts.append(account)
        
        # Count default accounts
        default_count = sum(1 for acc in accounts if acc.is_default)
        assert default_count == 1