"""
FastAPI dependencies for authentication and authorization.

This module provides dependency injection functions for protecting routes:
- get_current_user: Extracts and validates JWT token from Authorization header
- get_current_active_user: Ensures user is active

Use these in FastAPI route handlers to require authentication.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from auth.service import validate_token


# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate user from JWT token in Authorization header.
    
    This dependency function:
    1. Extracts Bearer token from Authorization header
    2. Validates the JWT token
    3. Retrieves the user from database
    4. Raises HTTPException if authentication fails
    
    Use in FastAPI routes to require authentication:
    
    Args:
        credentials: HTTP Bearer credentials (auto-extracted by FastAPI)
        db: Database session (auto-injected)
    
    Returns:
        Authenticated User object
    
    Raises:
        HTTPException: 401 if token is invalid or user not found
    
    Example:
        @app.get("/protected")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            return {"message": f"Hello {current_user.full_name}"}
    """
    token = credentials.credentials
    
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


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure the current user is active.
    
    This is a convenience dependency that chains get_current_user
    and adds an additional check for active status.
    
    Args:
        current_user: User from get_current_user dependency
    
    Returns:
        Active User object
    
    Raises:
        HTTPException: 403 if user account is disabled
    
    Example:
        @app.get("/active-only")
        async def active_route(
            user: User = Depends(get_current_active_user)
        ):
            return {"message": "Active user only"}
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
    
    Use this dependency for routes that require Pro features.
    
    Args:
        current_user: User from get_current_active_user dependency
    
    Returns:
        Pro tier User object
    
    Raises:
        HTTPException: 403 if user is not Pro tier
    
    Example:
        @app.post("/pro-feature")
        async def pro_only(
            user: User = Depends(require_pro_tier)
        ):
            return {"message": "Pro feature accessed"}
    """
    from database.models import UserTier
    
    if current_user.tier != UserTier.PRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires Pro tier subscription"
        )
    
    return current_user
