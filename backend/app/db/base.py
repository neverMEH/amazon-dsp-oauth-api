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
    _service_instance: Optional[Client] = None

    @classmethod
    def get_client(cls, use_service_role: bool = False) -> Client:
        """
        Get or create Supabase client instance

        Args:
            use_service_role: If True, use service role key for admin operations

        Returns:
            Supabase client
        """
        if use_service_role:
            # Use service role key for backend operations that need to bypass RLS
            if cls._service_instance is None:
                try:
                    # Use service role key if available, otherwise fall back to anon key
                    key = settings.supabase_service_role_key or settings.supabase_key
                    cls._service_instance = create_client(
                        settings.supabase_url,
                        key
                    )
                    logger.info(
                        "Supabase service client initialized",
                        using_service_role=bool(settings.supabase_service_role_key)
                    )
                except Exception as e:
                    logger.error("Failed to initialize Supabase service client", error=str(e))
                    raise
            return cls._service_instance
        else:
            # Use anon key for regular operations
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
        """Reset the client instances (useful for testing)"""
        cls._instance = None
        cls._service_instance = None


def get_supabase_client() -> Client:
    """
    Dependency to get Supabase client (anon key)

    Returns:
        Supabase client instance
    """
    return SupabaseClient.get_client(use_service_role=False)


def get_supabase_service_client() -> Client:
    """
    Get Supabase client with service role for backend operations

    Returns:
        Supabase client instance with service role
    """
    return SupabaseClient.get_client(use_service_role=True)