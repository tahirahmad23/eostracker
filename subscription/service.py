"""
Subscription Service Module (Lemon Squeezy)

Handles subscription lifecycle management including:
- Creating Lemon Squeezy checkout sessions
- Retrieving subscription status
- Canceling subscriptions
- Managing tier upgrades/downgrades

All functions return Result<T> for consistent error handling.
All transactions processed in USD globally.
"""

from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models import User, Subscription
from database import UserTier
from subscription.lemonsqueezy import LemonSqueezyClient


def create_checkout_session(
    user_id: int,
    success_url: str,
    cancel_url: str,
    db: Session
) -> Dict:
    """
    Initialize Lemon Squeezy subscription checkout session.
    
    Creates a Lemon Squeezy checkout (recurring billing in USD) for upgrading
    a user to Pro tier ($49/month). Returns checkout URL for redirect to 
    Lemon Squeezy payment page.
    
    All customers worldwide are charged in USD. Lemon Squeezy handles
    currency display and conversion at checkout.
    
    Args:
        user_id: ID of user creating subscription
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment cancelled
        db: Database session
    
    Returns:
        Result containing:
        - checkout_url: Lemon Squeezy checkout URL
        - checkout_id: Checkout ID for tracking
        
        Or error if user not found or API fails
    
    Example:
        result = create_checkout_session(
            user_id=1,
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
            db=db
        )
        if result["success"]:
            redirect_to(result["data"]["checkout_url"])
    """
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Check if user already has active subscription
        existing = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()
        
        if existing:
            return {
                "success": False,
                "error": "User already has an active subscription"
            }
        
        # Initialize Lemon Squeezy client
        lemonsqueezy = LemonSqueezyClient()
        
        # Create checkout on Lemon Squeezy
        checkout_result = lemonsqueezy.create_subscription(
            email=user.email,
            customer_name=user.full_name,
            callback_url=success_url,
            user_id=user.id
        )
        
        if not checkout_result["success"]:
            return checkout_result
        
        return {
            "success": True,
            "data": {
                "checkout_url": checkout_result["data"]["checkout_url"],
                "checkout_id": checkout_result["data"]["checkout_id"]
            }
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Database error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def get_subscription(user_id: int, db: Session) -> Dict:
    """
    Get user's current subscription status.
    
    Retrieves the active or most recent subscription for a user.
    Returns None if user has never subscribed.
    
    Args:
        user_id: ID of user to check
        db: Database session
    
    Returns:
        Result containing subscription details or None if no subscription exists
        
        Subscription details include:
        - id: Subscription record ID
        - lemonsqueezy_subscription_id: Lemon Squeezy subscription ID
        - lemonsqueezy_customer_id: Lemon Squeezy customer ID
        - lemonsqueezy_order_id: Original order ID
        - lemonsqueezy_product_id: Product ID
        - lemonsqueezy_variant_id: Variant ID
        - status: "active", "cancelled", "expired", etc.
        - current_period_start: Billing period start date
        - current_period_end: Billing period end date
        - created_at: Subscription creation date
        - cancelled_at: Cancellation date (if applicable)
    
    Example:
        result = get_subscription(user_id=1, db=db)
        if result["success"] and result["data"]:
            print(f"Status: {result['data']['status']}")
    """
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Get most recent subscription (active or cancelled)
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).order_by(Subscription.created_at.desc()).first()
        
        if not subscription:
            return {
                "success": True,
                "data": None
            }
        
        return {
            "success": True,
            "data": {
                "id": subscription.id,
                "lemonsqueezy_subscription_id": subscription.lemonsqueezy_subscription_id,
                "lemonsqueezy_customer_id": subscription.lemonsqueezy_customer_id,
                "lemonsqueezy_order_id": subscription.lemonsqueezy_order_id,
                "lemonsqueezy_product_id": subscription.lemonsqueezy_product_id,
                "lemonsqueezy_variant_id": subscription.lemonsqueezy_variant_id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "created_at": subscription.created_at.isoformat(),
                "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None
            }
        }
    
    except SQLAlchemyError as e:
        return {
            "success": False,
            "error": f"Database error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def cancel_subscription(user_id: int, db: Session) -> Dict:
    """
    Cancel user's active subscription.
    
    Cancels the subscription both on Lemon Squeezy and in the database.
    User will be downgraded to Free tier immediately, but subscription
    remains active until end of billing period.
    
    Args:
        user_id: ID of user canceling subscription
        db: Database session
    
    Returns:
        Result containing updated subscription details or error
    
    Example:
        result = cancel_subscription(user_id=1, db=db)
        if result["success"]:
            print(f"Cancelled at: {result['data']['cancelled_at']}")
    """
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Get active subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()
        
        if not subscription:
            return {
                "success": False,
                "error": "No active subscription found"
            }
        
        # Cancel on Lemon Squeezy first
        lemonsqueezy = LemonSqueezyClient()
        cancel_result = lemonsqueezy.cancel_subscription(
            subscription_id=subscription.lemonsqueezy_subscription_id
        )
        
        if not cancel_result["success"]:
            return cancel_result
        
        # Update database
        # Note: The webhook will also update this, but we do it here for immediate feedback
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.utcnow()
        
        # Downgrade user to free tier
        user.tier = UserTier.FREE
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(subscription)
        
        return {
            "success": True,
            "data": {
                "id": subscription.id,
                "lemonsqueezy_subscription_id": subscription.lemonsqueezy_subscription_id,
                "status": subscription.status,
                "cancelled_at": subscription.cancelled_at.isoformat()
            }
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Database error: {str(e)}"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
