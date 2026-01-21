"""
Security functions for password hashing and JWT token management.

This module provides cryptographic functions for secure authentication:
- Password hashing with bcrypt (cost factor 12)
- JWT token creation and validation
- Token payload extraction

All tokens are signed with HS256 algorithm using a secret key from environment.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from uuid import uuid4
from datetime import datetime, timedelta, timezone
# Password hashing context - bcrypt with cost factor 12
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# JWT configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Uses bcrypt with cost factor 12 for secure password storage.
    Never store plain text passwords in the database.
    
    Args:
        password: Plain text password to hash
    
    Returns:
        Bcrypt hashed password string
    
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain text password against a bcrypt hash.
    
    Args:
        plain: Plain text password from user input
        hashed: Bcrypt hash from database
    
    Returns:
        True if password matches hash, False otherwise
    
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> verify_password("SecurePass123!", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """
    Create a JWT access token for authenticated user.
    
    Access tokens expire after 30 minutes and should be used for
    API authentication. Include in Authorization header as:
    "Bearer <token>"
    
    Args:
        user_id: Database ID of the user
    
    Returns:
        Signed JWT token string
    
    Example:
        >>> token = create_access_token(123)
        >>> len(token) > 50
        True
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token for token renewal.
    
    Refresh tokens expire after 7 days and can be used to obtain
    new access tokens without re-authentication.
    
    Args:
        user_id: Database ID of the user
    
    Returns:
        Signed JWT token string
    
    Example:
        >>> token = create_refresh_token(123)
        >>> len(token) > 50
        True
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
    
    Returns:
        Token payload dict if valid, None if invalid or expired
    
    Example:
        >>> token = create_access_token(123)
        >>> payload = decode_token(token)
        >>> payload["sub"]
        '123'
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def extract_user_id(token: str) -> Optional[int]:
    """
    Extract user ID from a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        User ID if token is valid, None otherwise
    
    Example:
        >>> token = create_access_token(123)
        >>> extract_user_id(token)
        123
    """
    payload = decode_token(token)
    if payload and "sub" in payload:
        try:
            return int(payload["sub"])
        except (ValueError, TypeError):
            return None
    return None
