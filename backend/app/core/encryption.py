"""
Encryption utilities for sensitive data like API keys.

Uses Fernet symmetric encryption derived from the application's SECRET_KEY.
API keys are encrypted before storage and decrypted only when needed.
"""

import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet_key() -> bytes:
    """
    Derive a Fernet-compatible key from the application SECRET_KEY.

    Fernet requires a 32-byte base64-encoded key. We derive this from
    the SECRET_KEY using SHA-256 to ensure consistent key length.
    """
    secret = settings.SECRET_KEY.encode('utf-8')
    # SHA-256 produces 32 bytes, which is what Fernet needs
    key_bytes = hashlib.sha256(secret).digest()
    # Fernet expects base64-encoded key
    return base64.urlsafe_b64encode(key_bytes)


def _get_fernet() -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    return Fernet(_get_fernet_key())


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext string (e.g., API key) for secure storage.

    Args:
        plaintext: The sensitive value to encrypt

    Returns:
        Base64-encoded encrypted string safe for database storage
    """
    if not plaintext:
        return ""

    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(plaintext.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError("Failed to encrypt value")


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt an encrypted string back to plaintext.

    Args:
        ciphertext: The encrypted value from storage

    Returns:
        Original plaintext value

    Raises:
        ValueError: If decryption fails (invalid key or corrupted data)
    """
    if not ciphertext:
        return ""

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode('utf-8'))
        return decrypted.decode('utf-8')
    except InvalidToken:
        logger.error("Decryption failed: invalid token (wrong key or corrupted data)")
        raise ValueError("Failed to decrypt value - key may have changed")
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Failed to decrypt value")


def mask_api_key(key: Optional[str], visible_chars: int = 4) -> str:
    """
    Mask an API key for display, showing only the last few characters.

    Args:
        key: The API key to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked string like "••••••••abcd" or empty string if no key
    """
    if not key:
        return ""

    if len(key) <= visible_chars:
        return "•" * len(key)

    hidden_count = len(key) - visible_chars
    return "•" * min(hidden_count, 12) + key[-visible_chars:]


def is_key_set(encrypted_value: Optional[str]) -> bool:
    """
    Check if an encrypted API key value is set (non-empty).

    Args:
        encrypted_value: The encrypted value from storage

    Returns:
        True if a key is stored, False otherwise
    """
    return bool(encrypted_value and encrypted_value.strip())
