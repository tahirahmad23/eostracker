"""
Authentication module for EOS Tracker.

This module provides complete authentication and authorization functionality:
- User registration with email validation
- Login with JWT token generation
- Token validation and refresh
- Password hashing with bcrypt
- FastAPI dependencies for route protection

Example usage:
    from auth import register, login, get_current_user
    
    # In service layer
    result = register("user@example.com", "Pass123!", "John Doe", db)
    
    # In FastAPI routes
    @app.get("/protected")
    async def protected(user: User = Depends(get_current_user)):
        return {"user_id": user.id}
"""

from auth.service import (
    register,
    login,
    validate_token,
    refresh_tokens
)

from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)

from auth.dependencies import (
    get_current_user,
    get_current_active_user,
    require_pro_tier,
    get_current_user_optional
)


__all__ = [
    # Service functions
    "register",
    "login",
    "validate_token",
    "refresh_tokens",
    # Security functions
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    # FastAPI dependencies
    "get_current_user",
    "get_current_active_user",
    "require_pro_tier",
    "get_current_user_optional"
]
