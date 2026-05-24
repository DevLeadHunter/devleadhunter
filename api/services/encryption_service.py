"""
Encryption service for securing sensitive data like OAuth tokens.
"""
from cryptography.fernet import Fernet
import base64
import os
from typing import Optional


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.
    
    Uses Fernet (symmetric encryption) from cryptography library.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, uses environment variable
                          ENCRYPTION_KEY or generates a new one (not recommended for production).
        """
        if encryption_key:
            self.key = encryption_key.encode()
        else:
            # Try to get from settings first, then environment
            try:
                from core.config import settings
                env_key = settings.encryption_key
            except:
                env_key = os.getenv('ENCRYPTION_KEY')
            
            if env_key:
                self.key = env_key.encode()
            else:
                # Generate new key (WARNING: This should only be used in development)
                # In production, you must set ENCRYPTION_KEY in environment
                print("WARNING: No ENCRYPTION_KEY found in environment. Generating new key.")
                print("This key will be lost when the server restarts!")
                self.key = Fernet.generate_key()
                print(f"Generated key: {self.key.decode()}")
                print("Save this key in your .env file as ENCRYPTION_KEY")
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: String to encrypt
            
        Returns:
            Encrypted string (base64-encoded)
        """
        if not data:
            return ""
        
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted_data: Encrypted string (base64-encoded)
            
        Returns:
            Decrypted string
        """
        if not encrypted_data:
            return ""
        
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            Base64-encoded Fernet key
        """
        key = Fernet.generate_key()
        return key.decode()


# Singleton instance
encryption_service = EncryptionService()

