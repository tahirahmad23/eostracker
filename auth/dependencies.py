"""
FastAPI dependencies for authentication and authorization.

This module provides dependency injection functions for protecting routes:
- get_current_user: Extracts and validates JWT token from Authorization header or Cookie
- get_current_active_user: Ensures user is active

Use these in FastAPI route handlers to require authentication.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from auth.service import validate_token


# HTTP Bearer token security scheme
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate user from JWT token in Authorization header or Cookie.
    
    This dependency function:
    1. Extracts Bearer token from Authorization header OR Cookie
    2. Validates the JWT token
    3. Retrieves the user from database
    4. Raises HTTPException if authentication fails
    
    Args:
        credentials: HTTP Bearer credentials (auto-extracted from header)
        access_token: Token from cookie (auto-extracted)
        db: Database session
    
    Returns:
        Authenticated User object
    """
    # Fix: Check Header first, then check Cookie
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token and get user ID
    result = validate_token(token, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["error"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = result["data"]
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    token: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    Now correctly allows unauthenticated users on public pages.
    """
    # Check Cookie first if credentials aren't in header
    raw_token = token
    if credentials:
        raw_token = credentials.credentials

    if not raw_token:
        return None

    try:
        # Manually validate rather than calling get_current_user (to avoid the 401 redirect)
        result = validate_token(raw_token, db)
        if not result["success"]:
            return None
        
        user_id = result["data"]
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None
    
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure the current user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return current_user


def require_pro_tier(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user to have Pro tier subscription.
    """
    from database.models import UserTier
    
    if current_user.tier != UserTier.PRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires Pro tier subscription"
        )
    
    return current_user