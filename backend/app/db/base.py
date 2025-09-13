"""
Supabase database connection
"""
from supabase import create_client, Client
from typing import Optional
import structlog

from app.config import settings

logger = structlog.get_logger()


class SupabaseClient:
    """Manage Supabase connection"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance
        
        Returns:
            Supabase client
        """
        if cls._instance is None:
            try:
                cls._instance = create_client(
                    settings.supabase_url,
                    settings.supabase_key
                )
                logger.info("Supabase client initialized")
            except Exception as e:
                logger.error("Failed to initialize Supabase client", error=str(e))
                raise
        
        return cls._instance
    
    @classmethod
    def reset_client(cls):
        """Reset the client instance (useful for testing)"""
        cls._instance = None


def get_supabase_client() -> Client:
    """
    Dependency to get Supabase client
    
    Returns:
        Supabase client instance
    """
    return SupabaseClient.get_client()