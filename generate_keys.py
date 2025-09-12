#!/usr/bin/env python3
"""
Generate encryption keys and admin key for the application
"""
from cryptography.fernet import Fernet
import secrets


def generate_fernet_key():
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key().decode()


def generate_admin_key():
    """Generate a secure admin key"""
    return secrets.token_urlsafe(32)


if __name__ == "__main__":
    print("🔐 Generating secure keys for your application...")
    print("\n" + "="*60)
    
    print("\n1. FERNET_KEY (for token encryption):")
    print(f"   {generate_fernet_key()}")
    
    print("\n2. ADMIN_KEY (for admin endpoints):")
    print(f"   {generate_admin_key()}")
    
    print("\n" + "="*60)
    print("\n⚠️  IMPORTANT:")
    print("   - Save these keys securely")
    print("   - Never commit them to version control")
    print("   - Use the same FERNET_KEY across deployments")
    print("   - Keep the ADMIN_KEY secret")
    print("\n✅ Add these to your .env file")