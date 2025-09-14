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
        self.retry_after = retry_after
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


class AccountAccessError(OAuthException):
    """Raised when account access fails"""
    
    def __init__(self, operation: str, account_id: Optional[str] = None):
        super().__init__(
            message=f"Account access failed: {operation}",
            code="ACCOUNT_ACCESS_ERROR",
            status_code=403,
            details={"operation": operation, "account_id": account_id}
        )


class DSPPermissionError(OAuthException):
    """Raised when DSP access is denied"""
    
    def __init__(self, profile_id: str):
        super().__init__(
            message=f"DSP access denied for profile {profile_id}. Ensure proper permissions.",
            code="DSP_PERMISSION_DENIED",
            status_code=403,
            details={"profile_id": profile_id}
        )


class APIQuotaExceededError(OAuthException):
    """Raised when API quota is exceeded"""
    
    def __init__(self, quota_type: str, reset_time: Optional[str] = None):
        super().__init__(
            message=f"API quota exceeded: {quota_type}",
            code="QUOTA_EXCEEDED",
            status_code=429,
            details={"quota_type": quota_type, "reset_time": reset_time}
        )

class AmazonAuthError(OAuthException):
    """Raised when Amazon authentication fails"""
    
    def __init__(self, error_message: str):
        super().__init__(
            message=f"Amazon authentication failed: {error_message}",
            code="AMAZON_AUTH_FAILED",
            status_code=401,
            details={"error": error_message}
        )
