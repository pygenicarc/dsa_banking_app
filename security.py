"""
Security module for hashing and verifying PINs and passwords.
Uses standard library hashlib with PBKDF2-HMAC-SHA256 and unique per-account salt.
"""

import os
import hashlib
import secrets

def generate_salt(length: int = 16) -> str:
    """Generate a cryptographically secure random hexadecimal salt."""
    return secrets.token_hex(length)

def hash_pin(pin: str, salt: str | None = None) -> tuple[str, str]:
    """
    Hash a PIN using PBKDF2 with SHA-256 and a unique salt.
    Returns (hashed_pin_hex, salt_hex).
    """
    if salt is None:
        salt = generate_salt()
    
    # 100,000 iterations of PBKDF2 HMAC SHA-256
    pin_bytes = pin.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    key = hashlib.pbkdf2_hmac('sha256', pin_bytes, salt_bytes, 100_000)
    return key.hex(), salt

def verify_pin(pin: str, stored_hash: str, salt: str) -> bool:
    """
    Verify whether the provided PIN matches the stored hash using constant-time comparison.
    """
    calculated_hash, _ = hash_pin(pin, salt)
    return secrets.compare_digest(calculated_hash, stored_hash)

def validate_pin_format(pin: str) -> tuple[bool, str]:
    """
    Validate that PIN consists of 4 to 6 numeric digits.
    """
    if not pin.isdigit():
        return False, "PIN must contain only numbers."
    if len(pin) < 4 or len(pin) > 6:
        return False, "PIN must be between 4 and 6 digits long."
    return True, "Valid PIN"
