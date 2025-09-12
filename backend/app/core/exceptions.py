"""
Custom exception classes
"""
from typing import Optional, Dict, Any


class OAuthException(Exception):
    """Base exception for OAuth errors"""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class InvalidStateTokenError(OAuthException):
    """Raised when state token is invalid or expired"""
    
    def __init__(self, state: str):
        super().__init__(
            message="The state token is invalid or has expired",
            code="INVALID_STATE_TOKEN",
            status_code=400,
            details={"provided_state": state}
        )


class TokenExchangeError(OAuthException):
    """Raised when token exchange with Amazon fails"""
    
    def __init__(self, error_message: str):
        super().__init__(
            message=f"Failed to exchange authorization code: {error_message}",
            code="TOKEN_EXCHANGE_FAILED",
            status_code=401,
            details={"error": error_message}
        )


class TokenRefreshError(OAuthException):
    """Raised when token refresh fails"""
    
    def __init__(self, error_message: str):
        super().__init__(
            message=f"Failed to refresh token: {error_message}",
            code="REFRESH_FAILED",
            status_code=401,
            details={"error": error_message}
        )


class RateLimitError(OAuthException):
    """Raised when Amazon API rate limit is exceeded"""
    
    def __init__(self, retry_after: int):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            code="RATE_LIMITED",
            status_code=503,
            details={"retry_after": retry_after}
        )


class DatabaseError(OAuthException):
    """Raised when database operation fails"""
    
    def __init__(self, operation: str, error_message: str):
        super().__init__(
            message=f"Database operation failed: {operation}",
            code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation, "error": error_message}
        )


class EncryptionError(OAuthException):
    """Raised when token encryption/decryption fails"""
    
    def __init__(self, operation: str):
        super().__init__(
            message=f"Encryption operation failed: {operation}",
            code="ENCRYPTION_ERROR",
            status_code=500,
            details={"operation": operation}
        )