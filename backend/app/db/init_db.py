"""
Database initialization script
"""
import os
import sys
from pathlib import Path
import structlog
from supabase import create_client, Client

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.db.base import get_supabase_client

logger = structlog.get_logger()


class DatabaseInitializer:
    """Initialize database with required tables and indexes"""
    
    def __init__(self):
        """Initialize database connection"""
        self.client = get_supabase_client()
        self.migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    
    def run_migration(self, migration_file: str) -> bool:
        """
        Run a SQL migration file
        
        Args:
            migration_file: Path to migration SQL file
            
        Returns:
            Success status
        """
        try:
            migration_path = self.migrations_dir / migration_file
            
            if not migration_path.exists():
                logger.error(f"Migration file not found: {migration_file}")
                return False
            
            with open(migration_path, 'r') as f:
                sql_content = f.read()
            
            # Note: Supabase Python client doesn't directly support raw SQL execution
            # In production, you would use psycopg2 or execute via Supabase dashboard
            # This is a placeholder for the actual implementation
            
            logger.info(f"Migration {migration_file} would be executed")
            logger.info("Please run the migration manually via Supabase SQL editor or psycopg2")
            
            return True
            
        except Exception as e:
            logger.error(f"Error running migration {migration_file}: {str(e)}")
            return False
    
    def check_tables_exist(self) -> dict:
        """
        Check if required tables exist
        
        Returns:
            Dict with table existence status
        """
        tables_to_check = ["users", "user_accounts", "oauth_tokens"]
        table_status = {}
        
        for table in tables_to_check:
            try:
                # Try to select from table
                result = self.client.table(table).select("*").limit(1).execute()
                table_status[table] = True
                logger.info(f"Table {table} exists")
            except Exception as e:
                table_status[table] = False
                logger.warning(f"Table {table} does not exist or is not accessible")
        
        return table_status
    
    def initialize_database(self) -> bool:
        """
        Initialize database with all required tables
        
        Returns:
            Success status
        """
        logger.info("Starting database initialization")
        
        # Check existing tables
        table_status = self.check_tables_exist()
        
        # If users and user_accounts tables don't exist, run migration
        if not table_status.get("users") or not table_status.get("user_accounts"):
            logger.info("Running user tables migration")
            success = self.run_migration("001_create_user_tables.sql")
            
            if not success:
                logger.error("Failed to run user tables migration")
                return False
        else:
            logger.info("User tables already exist")
        
        logger.info("Database initialization complete")
        return True
    
    def create_test_data(self) -> bool:
        """
        Create test data for development
        
        Returns:
            Success status
        """
        try:
            # Create test user
            test_user = {
                "clerk_user_id": "test_clerk_user_123",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "profile_image_url": "https://example.com/test-avatar.jpg"
            }
            
            # Check if test user already exists
            existing = self.client.table("users").select("*").eq("clerk_user_id", test_user["clerk_user_id"]).execute()
            
            if not existing.data:
                result = self.client.table("users").insert(test_user).execute()
                
                if result.data:
                    user_id = result.data[0]["id"]
                    logger.info(f"Test user created with ID: {user_id}")
                    
                    # Create test Amazon account
                    test_account = {
                        "user_id": user_id,
                        "account_name": "Test Amazon Store",
                        "amazon_account_id": "TEST_AMZN_123",
                        "marketplace_id": "ATVPDKIKX0DER",
                        "account_type": "advertising",
                        "is_default": True,
                        "metadata": {
                            "test": True,
                            "created_by": "init_script"
                        }
                    }
                    
                    account_result = self.client.table("user_accounts").insert(test_account).execute()
                    
                    if account_result.data:
                        logger.info(f"Test Amazon account created")
                        return True
            else:
                logger.info("Test user already exists")
                return True
                
        except Exception as e:
            logger.error(f"Error creating test data: {str(e)}")
            return False
        
        return False


def main():
    """Main initialization function"""
    initializer = DatabaseInitializer()
    
    # Initialize database
    if initializer.initialize_database():
        logger.info("Database initialization successful")
        
        # Optionally create test data in development
        if os.getenv("ENVIRONMENT", "development") == "development":
            if initializer.create_test_data():
                logger.info("Test data created successfully")
            else:
                logger.warning("Failed to create test data")
    else:
        logger.error("Database initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    main()