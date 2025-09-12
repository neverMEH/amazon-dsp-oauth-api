"""
Security and encryption utilities
"""
from cryptography.fernet import Fernet
from typing import Optional
import secrets
from app.config import settings


class TokenEncryption:
    """Handle token encryption and decryption"""
    
    def __init__(self):
        """Initialize with Fernet key from settings"""
        self.fernet = Fernet(settings.fernet_key.encode())
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token string
        
        Args:
            token: Plain text token to encrypt
            
        Returns:
            Encrypted token as string
        """
        if not token:
            raise ValueError("Token cannot be empty")
        
        encrypted = self.fernet.encrypt(token.encode())
        return encrypted.decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt an encrypted token
        
        Args:
            encrypted_token: Encrypted token string
            
        Returns:
            Decrypted plain text token
        """
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")
        
        decrypted = self.fernet.decrypt(encrypted_token.encode())
        return decrypted.decode()


def generate_state_token() -> str:
    """
    Generate a secure random state token for CSRF protection
    
    Returns:
        Random URL-safe token string
    """
    return secrets.token_urlsafe(32)


def generate_admin_key() -> str:
    """
    Generate a secure admin key
    
    Returns:
        Random admin key string
    """
    return secrets.token_urlsafe(32)


# Create singleton instance
token_encryption = TokenEncryption()