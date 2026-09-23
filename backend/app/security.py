"""Encryption of Canvas tokens at rest + opaque session tokens."""

from __future__ import annotations

import base64
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken

from .config import APP_SECRET_KEY

# Derive a stable Fernet key from the app secret.
_fernet = Fernet(
    base64.urlsafe_b64encode(hashlib.sha256(APP_SECRET_KEY.encode()).digest())
)


def encrypt_token(token: str) -> str:
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return ""


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Store only a hash of the session token in the DB."""
    return hashlib.sha256(token.encode()).hexdigest()
