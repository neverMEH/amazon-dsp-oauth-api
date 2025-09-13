"""
User service for database operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog
from supabase import Client

from app.models.user import User
from app.models.amazon_account import AmazonAccount
from app.db.base import get_supabase_client
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.amazon_account import AmazonAccountCreate, AmazonAccountUpdate

logger = structlog.get_logger()


class UserService:
    """Service for managing user operations"""
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """Initialize user service"""
        self.client = supabase_client or get_supabase_client()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user in the database
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user instance
        """
        try:
            user = User(
                clerk_user_id=user_data.clerk_user_id,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                profile_image_url=user_data.profile_image_url
            )
            
            result = self.client.table("users").insert(user.to_dict()).execute()
            
            if result.data:
                created_user = User.from_dict(result.data[0])
                logger.info("User created", user_id=created_user.id, email=created_user.email)
                return created_user
            else:
                raise Exception("Failed to create user")
                
        except Exception as e:
            logger.error("Error creating user", error=str(e), clerk_id=user_data.clerk_user_id)
            raise
    
    async def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """
        Get user by Clerk ID
        
        Args:
            clerk_user_id: Clerk user identifier
            
        Returns:
            User instance or None
        """
        try:
            result = self.client.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute()
            
            if result.data and len(result.data) > 0:
                return User.from_dict(result.data[0])
            return None
            
        except Exception as e:
            logger.error("Error fetching user", error=str(e), clerk_id=clerk_user_id)
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by database ID
        
        Args:
            user_id: User UUID
            
        Returns:
            User instance or None
        """
        try:
            result = self.client.table("users").select("*").eq("id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return User.from_dict(result.data[0])
            return None
            
        except Exception as e:
            logger.error("Error fetching user", error=str(e), user_id=user_id)
            return None
    
    async def update_user(self, user_id: str, update_data: UserUpdate) -> Optional[User]:
        """
        Update user information
        
        Args:
            user_id: User UUID
            update_data: Fields to update
            
        Returns:
            Updated user instance
        """
        try:
            # Filter out None values
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            
            if not update_dict:
                return await self.get_user_by_id(user_id)
            
            # Add updated_at timestamp
            update_dict["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("users").update(update_dict).eq("id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                updated_user = User.from_dict(result.data[0])
                logger.info("User updated", user_id=user_id)
                return updated_user
            return None
            
        except Exception as e:
            logger.error("Error updating user", error=str(e), user_id=user_id)
            return None
    
    async def update_last_login(self, clerk_user_id: str) -> Optional[User]:
        """
        Update user's last login timestamp
        
        Args:
            clerk_user_id: Clerk user identifier
            
        Returns:
            Updated user instance
        """
        try:
            update_data = {
                "last_login_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("users").update(update_data).eq("clerk_user_id", clerk_user_id).execute()
            
            if result.data and len(result.data) > 0:
                return User.from_dict(result.data[0])
            return None
            
        except Exception as e:
            logger.error("Error updating last login", error=str(e), clerk_id=clerk_user_id)
            return None
    
    async def get_or_create_user(self, user_data: UserCreate) -> User:
        """
        Get existing user or create new one
        
        Args:
            user_data: User data for creation
            
        Returns:
            User instance
        """
        # Try to get existing user
        existing_user = await self.get_user_by_clerk_id(user_data.clerk_user_id)
        
        if existing_user:
            # Update last login
            await self.update_last_login(user_data.clerk_user_id)
            return existing_user
        
        # Create new user
        return await self.create_user(user_data)


class AmazonAccountService:
    """Service for managing Amazon account connections"""
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """Initialize account service"""
        self.client = supabase_client or get_supabase_client()
    
    async def create_account(self, account_data: AmazonAccountCreate) -> AmazonAccount:
        """
        Create a new Amazon account connection
        
        Args:
            account_data: Account creation data
            
        Returns:
            Created account instance
        """
        try:
            account = AmazonAccount(
                user_id=account_data.user_id,
                account_name=account_data.account_name,
                amazon_account_id=account_data.amazon_account_id,
                marketplace_id=account_data.marketplace_id,
                account_type=account_data.account_type,
                metadata=account_data.metadata
            )
            
            # Check if this is the first account for the user
            existing_accounts = await self.get_user_accounts(account_data.user_id)
            if not existing_accounts:
                account.is_default = True
            
            result = self.client.table("user_accounts").insert(account.to_dict()).execute()
            
            if result.data:
                created_account = AmazonAccount.from_dict(result.data[0])
                logger.info("Amazon account created", 
                           account_id=created_account.id,
                           user_id=created_account.user_id)
                return created_account
            else:
                raise Exception("Failed to create Amazon account")
                
        except Exception as e:
            logger.error("Error creating Amazon account", error=str(e))
            raise
    
    async def get_user_accounts(self, user_id: str) -> List[AmazonAccount]:
        """
        Get all Amazon accounts for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            List of Amazon accounts
        """
        try:
            result = self.client.table("user_accounts").select("*").eq("user_id", user_id).execute()
            
            if result.data:
                return [AmazonAccount.from_dict(acc) for acc in result.data]
            return []
            
        except Exception as e:
            logger.error("Error fetching user accounts", error=str(e), user_id=user_id)
            return []
    
    async def get_account_by_id(self, account_id: str) -> Optional[AmazonAccount]:
        """
        Get Amazon account by ID
        
        Args:
            account_id: Account UUID
            
        Returns:
            Account instance or None
        """
        try:
            result = self.client.table("user_accounts").select("*").eq("id", account_id).execute()
            
            if result.data and len(result.data) > 0:
                return AmazonAccount.from_dict(result.data[0])
            return None
            
        except Exception as e:
            logger.error("Error fetching account", error=str(e), account_id=account_id)
            return None
    
    async def update_account(self, account_id: str, update_data: AmazonAccountUpdate) -> Optional[AmazonAccount]:
        """
        Update Amazon account information
        
        Args:
            account_id: Account UUID
            update_data: Fields to update
            
        Returns:
            Updated account instance
        """
        try:
            # Filter out None values
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            
            if not update_dict:
                return await self.get_account_by_id(account_id)
            
            # Handle is_default flag
            if update_dict.get("is_default") is True:
                # Get the account to find user_id
                account = await self.get_account_by_id(account_id)
                if account:
                    # Reset other accounts to non-default
                    self.client.table("user_accounts").update({"is_default": False}).eq("user_id", account.user_id).execute()
            
            result = self.client.table("user_accounts").update(update_dict).eq("id", account_id).execute()
            
            if result.data and len(result.data) > 0:
                updated_account = AmazonAccount.from_dict(result.data[0])
                logger.info("Amazon account updated", account_id=account_id)
                return updated_account
            return None
            
        except Exception as e:
            logger.error("Error updating account", error=str(e), account_id=account_id)
            return None
    
    async def set_default_account(self, user_id: str, account_id: str) -> bool:
        """
        Set an account as the user's default
        
        Args:
            user_id: User UUID
            account_id: Account UUID to set as default
            
        Returns:
            Success status
        """
        try:
            # Reset all accounts to non-default
            self.client.table("user_accounts").update({"is_default": False}).eq("user_id", user_id).execute()
            
            # Set selected account as default
            result = self.client.table("user_accounts").update({"is_default": True}).eq("id", account_id).eq("user_id", user_id).execute()
            
            if result.data:
                logger.info("Default account set", user_id=user_id, account_id=account_id)
                return True
            return False
            
        except Exception as e:
            logger.error("Error setting default account", error=str(e))
            return False
    
    async def delete_account(self, account_id: str) -> bool:
        """
        Delete an Amazon account connection
        
        Args:
            account_id: Account UUID
            
        Returns:
            Success status
        """
        try:
            result = self.client.table("user_accounts").delete().eq("id", account_id).execute()
            
            if result.data:
                logger.info("Amazon account deleted", account_id=account_id)
                return True
            return False
            
        except Exception as e:
            logger.error("Error deleting account", error=str(e), account_id=account_id)
            return False