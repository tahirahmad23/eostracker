"""
Subscription Routes (Lemon Squeezy)
Checkout, webhooks, and subscription management
"""

from fastapi import APIRouter, Request, Depends, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, User

from auth import get_current_user_optional
from subscription import (
    create_checkout_session,
    get_subscription,
    cancel_subscription,
    process_webhook
)
from web.routes.auth import set_flash_message, get_flash_messages

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/subscription", response_class=HTMLResponse)
def subscription_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Subscription management page
    Shows current tier, subscription status, and upgrade/cancel options
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Get subscription details
    sub_result = get_subscription(current_user.id, db)
    subscription = sub_result["data"] if sub_result["success"] else None
    
    return templates.TemplateResponse(
        "subscription.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request),
            "subscription": subscription
        }
    )


@router.post("/subscription/checkout")
def create_checkout(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Initialize Lemon Squeezy checkout session
    Redirects user to Lemon Squeezy payment page
    All transactions in USD globally
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Create checkout session
    success_url = str(request.url_for("subscription_success"))
    cancel_url = str(request.url_for("subscription_page"))
    
    result = create_checkout_session(current_user.id, success_url, cancel_url, db)
    
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
        return RedirectResponse(url="/subscription", status_code=303)
    
    # Redirect to Lemon Squeezy checkout URL
    return RedirectResponse(url=result["data"]["checkout_url"], status_code=303)


@router.get("/subscription/success", response_class=HTMLResponse)
def subscription_success(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Subscription success callback from Lemon Squeezy
    
    NOTE: The actual upgrade happens via webhook (subscription_created event).
    This page just shows a success message. The webhook will upgrade the user to Pro.
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    set_flash_message(
        request,
        "Thank you for upgrading to Pro! Your subscription will be activated shortly.",
        "success"
    )
    
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/subscription/cancel")
def cancel_user_subscription(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Cancel user's subscription
    Downgrades to free tier immediately
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    result = cancel_subscription(current_user.id, db)
    
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
    else:
        set_flash_message(
            request,
            "Your subscription has been cancelled successfully.",
            "success"
        )
    
    return RedirectResponse(url="/subscription", status_code=303)


@router.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Lemon Squeezy webhook handler
    Processes subscription events (creation, updates, payments, etc.)
    
    Important webhook events for subscriptions:
    - subscription_created: Sent when subscription is successfully created
    - subscription_updated: Sent when subscription status changes
    - subscription_payment_success: Sent when recurring payment succeeds
    
    NOTE: Lemon Squeezy sends the signature in the X-Signature header.
    We validate this to ensure the webhook came from Lemon Squeezy.
    """
    # Get raw body for signature validation (IMPORTANT: must be raw bytes)
    raw_body = await request.body()
    
    # Parse JSON payload
    import json
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid JSON payload"}
        )
    
    # Get event name from meta
    meta = payload.get("meta", {})
    event_name = meta.get("event_name")
    
    if not event_name:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Missing event_name in meta"}
        )
    
    # Validate signature
    if not x_signature:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Missing X-Signature header"}
        )
    
    # Process webhook (passes raw body for signature validation)
    result = process_webhook(
        event_name=event_name,
        payload=payload,
        raw_payload=raw_body,
        signature=x_signature,
        db=db
    )
    
    if result["success"]:
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Webhook processed successfully"}
        )
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.get("/pricing", response_class=HTMLResponse)
def pricing_page_redirect(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Pricing page (can be accessed with or without auth)
    """
    return templates.TemplateResponse(
        "pricing.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request) if current_user else []
        }
    )
