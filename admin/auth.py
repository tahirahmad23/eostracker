"""
Admin authentication backend for SQLAdmin.

Provides secure authentication for the admin interface by integrating
with the existing JWT-based auth system. Only users with is_admin=True
can access the admin panel.
"""
import os
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
import logging

from database.connection import SessionLocal
from database.models import User
from auth.security import verify_password, create_access_token

logger = logging.getLogger(__name__)


class AdminAuth(AuthenticationBackend):
    """
    SQLAdmin authentication backend.
    
    Implements login, logout, and authentication verification
    for the admin interface. Uses session cookies for auth state.
    """

    async def login(self, request: Request) -> bool:
        """
        Handle admin login form submission.
        
        Validates email/password and creates a session if the user
        is an admin. Returns True on success, False on failure.
        """
        form = await request.form()
        email = form.get("username")  # SQLAdmin uses 'username' field
        password = form.get("password")

        if not email or not password:
            return False

        db: Session = SessionLocal()
        try:
            # Find user by email
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                logger.warning("Admin login failed: user not found")
                return False
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                logger.warning("Admin login failed: invalid credentials")
                return False
            
            # Check if user is admin
            if not user.is_admin:
                logger.warning("Admin login denied: user is not admin")
                return False
            
            # Check if user is active
            if not user.is_active:
                logger.warning("Admin login denied: user is inactive")
                return False
            
            # Create session token and store in session
            token = create_access_token(user.id)
            request.session.update({
                "admin_token": token,
                "admin_user_id": user.id
            })
            
            logger.info("Admin login successful")
            return True
            
        except Exception as e:
            logger.error(f"Admin login error: {e}")
            return False
        finally:
            db.close()

    async def logout(self, request: Request) -> bool:
        """
        Handle admin logout.
        
        Clears the admin session data.
        """
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """
        Check if the current request is authenticated.
        
        Verifies that a valid admin session exists.
        Returns True if authenticated, False otherwise.
        """
        admin_token = request.session.get("admin_token")
        admin_user_id = request.session.get("admin_user_id")
        
        if not admin_token or not admin_user_id:
            return False
        
        # Verify the user still exists and is still an admin
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == admin_user_id).first()
            
            if not user or not user.is_admin or not user.is_active:
                # Clear invalid session
                request.session.clear()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Admin auth check error: {e}")
            return False
        finally:
            db.close()


# Create singleton instance for use in main.py
authentication_backend = AdminAuth(secret_key=os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production"))
