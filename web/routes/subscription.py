"""
Subscription Routes
Paystack checkout, webhooks, and subscription management
"""

from fastapi import APIRouter, Request, Depends, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db,User

from auth import get_current_user
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Subscription management page
    Shows current tier, subscription status, and upgrade/cancel options
    """
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initialize Paystack checkout session
    Redirects user to Paystack payment page
    """
    # Create checkout session
    success_url = str(request.url_for("subscription_success"))
    cancel_url = str(request.url_for("subscription_page"))
    
    result = create_checkout_session(current_user.id, success_url, cancel_url, db)
    
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
        return RedirectResponse(url="/subscription", status_code=303)
    
    # Redirect to Paystack authorization URL
    return RedirectResponse(url=result["data"]["authorization_url"], status_code=303)


@router.get("/subscription/success", response_class=HTMLResponse)
def subscription_success(
    request: Request,
    reference: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Subscription success callback from Paystack
    """
    set_flash_message(
        request,
        "Thank you for upgrading to Pro! Your subscription is now active.",
        "success"
    )
    
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/subscription/cancel")
def cancel_user_subscription(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel user's subscription
    Downgrades to free tier at end of billing period
    """
    result = cancel_subscription(current_user.id, db)
    
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
    else:
        set_flash_message(
            request,
            "Your subscription has been cancelled. You'll retain Pro access until the end of your billing period.",
            "success"
        )
    
    return RedirectResponse(url="/subscription", status_code=303)


@router.post("/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Paystack webhook handler
    Processes subscription events (payment success, cancellation, etc.)
    
    Webhook events:
    - subscription.create
    - subscription.disable
    - charge.success
    """
    # Get raw body for signature validation
    body = await request.body()
    
    # Parse JSON payload
    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid JSON payload"}
        )
    
    # Get event type
    event_type = payload.get("event")
    if not event_type:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Missing event type"}
        )
    
    # Process webhook
    result = process_webhook(event_type, payload, x_paystack_signature or "", db)
    
    if result["success"]:
        return {"success": True, "message": "Webhook processed"}
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.get("/pricing", response_class=HTMLResponse)
def pricing_page_redirect(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
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
