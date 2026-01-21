"""
Authentication service with user registration, login, and token management.

This module implements the core authentication business logic:
- User registration with email validation
- Login with credential verification
- JWT token validation
- Refresh token flow

All functions follow the Result<T> pattern for consistent error handling.
"""

import re
from typing import Dict, Any

from sqlalchemy.orm import Session
from email_validator import validate_email, EmailNotValidError

from database.models import User, UserTier
from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    extract_user_id,
    decode_token
)


# Type alias for Result pattern
Result = Dict[str, Any]


def _validate_email_format(email: str) -> bool:
    """
    Validate email format using email-validator library.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email is valid, False otherwise
    """
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def _validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 number
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least 1 uppercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least 1 number"
    
    return True, ""


def register(
    email: str,
    password: str,
    full_name: str,
    db: Session
) -> Result:
    """
    Register a new user account.
    
    Creates a new user with validated email and strong password.
    New users start on the free tier. Returns user data and JWT tokens.
    
    Args:
        email: User's email address (must be valid format)
        password: User's password (min 8 chars, 1 uppercase, 1 number)
        full_name: User's full name
        db: Database session
    
    Returns:
        Result containing user data and tokens, or error message
    
    Example:
        >>> result = register(
        ...     "user@example.com",
        ...     "SecurePass123!",
        ...     "John Doe",
        ...     db
        ... )
        >>> if result["success"]:
        ...     user = result["data"]["user"]
        ...     token = result["data"]["access_token"]
    """
    try:
        # Validate email format
        if not _validate_email_format(email):
            return {
                "success": False,
                "error": "Invalid email format"
            }
        
        # Normalize email to lowercase
        email = email.lower().strip()
        
        # Check for duplicate email
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return {
                "success": False,
                "error": "Email already registered"
            }
        
        # Validate password strength
        is_valid, error_msg = _validate_password_strength(password)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create user
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name.strip(),
            tier=UserTier.FREE,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "tier": user.tier.value,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat()
                },
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        }
    
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Registration failed: {str(e)}"
        }


def login(
    email: str,
    password: str,
    db: Session
) -> Result:
    """
    Authenticate user and return JWT tokens.
    
    Verifies email and password, then returns user data and fresh tokens.
    
    Args:
        email: User's email address
        password: User's password
        db: Database session
    
    Returns:
        Result containing user data and tokens, or error message
    
    Example:
        >>> result = login("user@example.com", "SecurePass123!", db)
        >>> if result["success"]:
        ...     token = result["data"]["access_token"]
    """
    try:
        # Normalize email
        email = email.lower().strip()
        
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {
                "success": False,
                "error": "Invalid email or password"
            }
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            return {
                "success": False,
                "error": "Invalid email or password"
            }
        
        # Check if user is active
        if not user.is_active:
            return {
                "success": False,
                "error": "Account is disabled"
            }
        
        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "tier": user.tier.value,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat()
                },
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Login failed: {str(e)}"
        }


def validate_token(token: str, db: Session) -> Result:
    """
    Validate a JWT access token and return user ID.
    
    Args:
        token: JWT access token to validate
        db: Database session
    
    Returns:
        Result containing user_id if valid, or error message
    
    Example:
        >>> result = validate_token(access_token, db)
        >>> if result["success"]:
        ...     user_id = result["data"]
    """
    try:
        # Decode token
        payload = decode_token(token)
        if not payload:
            return {
                "success": False,
                "error": "Invalid or expired token"
            }
        
        # Verify token type
        if payload.get("type") != "access":
            return {
                "success": False,
                "error": "Invalid token type"
            }
        
        # Extract user ID
        user_id = extract_user_id(token)
        if not user_id:
            return {
                "success": False,
                "error": "Invalid token payload"
            }
        
        # Verify user exists and is active
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        if not user.is_active:
            return {
                "success": False,
                "error": "User account is disabled"
            }
        
        return {
            "success": True,
            "data": user_id
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Token validation failed: {str(e)}"
        }


def refresh_tokens(refresh_token: str, db: Session) -> Result:
    """
    Generate new access and refresh tokens from a valid refresh token.
    
    Args:
        refresh_token: Valid JWT refresh token
        db: Database session
    
    Returns:
        Result containing new tokens, or error message
    
    Example:
        >>> result = refresh_tokens(old_refresh_token, db)
        >>> if result["success"]:
        ...     new_access = result["data"]["access_token"]
        ...     new_refresh = result["data"]["refresh_token"]
    """
    try:
        # Decode token
        payload = decode_token(refresh_token)
        if not payload:
            return {
                "success": False,
                "error": "Invalid or expired refresh token"
            }
        
        # Verify token type
        if payload.get("type") != "refresh":
            return {
                "success": False,
                "error": "Invalid token type"
            }
        
        # Extract user ID
        user_id = extract_user_id(refresh_token)
        if not user_id:
            return {
                "success": False,
                "error": "Invalid token payload"
            }
        
        # Verify user exists and is active
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        if not user.is_active:
            return {
                "success": False,
                "error": "User account is disabled"
            }
        
        # Generate new tokens
        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)
        
        return {
            "success": True,
            "data": {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Token refresh failed: {str(e)}"
        }
