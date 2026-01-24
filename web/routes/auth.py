"""
Authentication Routes
User registration, login, and logout
"""

from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, User
from auth import register, login,get_current_user_optional
from alerts import send_welcome_email


router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


def set_flash_message(request: Request, message: str, category: str = "info"):
    """
    Set a flash message in session
    
    Args:
        request: FastAPI request object
        message: Message to display
        category: Message category (success, error, warning, info)
    """
    if not hasattr(request.session, "flash_messages"):
        request.session["flash_messages"] = []
    request.session["flash_messages"].append({"message": message, "category": category})


def get_flash_messages(request: Request) -> list:
    """
    Get and clear flash messages from session
    
    Args:
        request: FastAPI request object
    
    Returns:
        List of flash messages
    """
    messages = request.session.pop("flash_messages", [])
    return messages


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Login page
    Redirects to dashboard if already logged in
    """
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "current_user": None,
            "flash_messages": get_flash_messages(request)
        }
    )


@router.post("/login")
def login_user(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Process login form
    Sets JWT token in cookie and redirects to dashboard
    """
    # Authenticate user
    result = login(email, password, db)
    
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
        return RedirectResponse(url="/login", status_code=303)
    
    # Set access token in cookie
    access_token = result["data"]["access_token"]
    
    redirect = RedirectResponse(url="/dashboard", status_code=303)
    redirect.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60 if remember_me else 30 * 60,  # 7 days or 30 min
        samesite="lax"
    )
    
    set_flash_message(request, f"Welcome back, {result['data']['user']['full_name']}!", "success")
    
    return redirect


@router.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Registration page
    Redirects to dashboard if already logged in
    """
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "current_user": None,
            "flash_messages": get_flash_messages(request)
        }
    )


@router.post("/register")
def register_user(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    full_name: str = Form(...),
    agree_terms: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Process registration form
    Creates user, sends welcome email, auto-login, redirect to dashboard
    """
    # Validate password confirmation
    if password != password_confirm:
        set_flash_message(request, "Passwords do not match", "error")
        return RedirectResponse(url="/register", status_code=303)
    
    # Validate terms acceptance
    if not agree_terms:
        set_flash_message(request, "You must agree to the terms and conditions", "error")
        return RedirectResponse(url="/register", status_code=303)
   
    # Register user
    result = register(email, password, full_name, db)
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
        return RedirectResponse(url="/register", status_code=303)
    
    # Send welcome email (fire and forget)
    try:
        email_result = send_welcome_email(email, full_name)
        if not email_result["success"]:
            # Log error but don't fail registration
            print(f"Failed to send welcome email: {email_result['error']}")
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
    
    # Set access token in cookie (auto-login)
    access_token = result["data"]["access_token"]
    
    redirect = RedirectResponse(url="/dashboard", status_code=303)
    redirect.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=30 * 60,  # 30 minutes
        samesite="lax"
    )
    
    set_flash_message(request, f"Welcome to EOS Tracker, {full_name}! Your account has been created.", "success")
    
    return redirect


@router.post("/logout")
def logout_user(request: Request):
    """
    Logout user by clearing session and cookie
    """
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.delete_cookie("access_token")
    
    set_flash_message(request, "You have been logged out successfully", "success")
    
    return redirect


# Template filter to get flash messages
templates.env.globals["get_flash_messages"] = get_flash_messages
