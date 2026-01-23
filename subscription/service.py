"""
Subscription Service Module

Handles subscription lifecycle management including:
- Creating Paystack checkout sessions
- Retrieving subscription status
- Canceling subscriptions
- Managing tier upgrades/downgrades

All functions return Result<T> for consistent error handling.
"""

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models import User, Subscription
from database import UserTier
from subscription.paystack import PaystackClient


def create_checkout_session(
    user_id: int,
    success_url: str,
    cancel_url: str,
    db: Session
) -> Dict:
    """
    Initialize Paystack subscription checkout session.
    
    Creates a Paystack subscription checkout session for upgrading
    a user to Pro tier ($49/month). Returns authorization URL for
    redirect to Paystack payment page.
    
    Args:
        user_id: ID of user creating subscription
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment cancelled
        db: Database session
    
    Returns:
        Result containing:
        - authorization_url: Paystack checkout URL
        - reference: Transaction reference for tracking
        
        Or error if user not found or Paystack API fails
    
    Example:
        result = create_checkout_session(
            user_id=1,
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
            db=db
        )
        if result["success"]:
            redirect_to(result["data"]["authorization_url"])
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
        
        # Initialize Paystack client
        paystack = PaystackClient()
        
        # Create subscription on Paystack
        checkout_result = paystack.create_subscription(
            email=user.email,
            customer_name=user.full_name,
            callback_url=success_url
        )
        
        if not checkout_result["success"]:
            return checkout_result
        
        return {
            "success": True,
            "data": {
                "authorization_url": checkout_result["data"]["authorization_url"],
                "reference": checkout_result["data"]["reference"]
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
        - paystack_subscription_code: Paystack subscription code
        - paystack_customer_code: Paystack customer code
        - plan_code: Pro plan code
        - status: "active" or "cancelled"
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
                "paystack_subscription_code": subscription.paystack_subscription_code,
                "paystack_customer_code": subscription.paystack_customer_code,
                "plan_code": subscription.plan_code,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat(),
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
    
    Cancels the subscription both on Paystack and in the database.
    User will be downgraded to Free tier. Subscription remains active
    until the end of the current billing period.
    
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
        
        # Cancel on Paystack
        paystack = PaystackClient()
        cancel_result = paystack.cancel_subscription(
            paystack_subscription_code=subscription.paystack_subscription_code,
            email_token=subscription.paystack_customer_code
        )
        
        if not cancel_result["success"]:
            return cancel_result
        
        # Update database
        subscription.status = "canceled"
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
                "paystack_subscription_code": subscription.paystack_subscription_code,
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
