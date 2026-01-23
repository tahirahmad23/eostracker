"""
Paystack Webhook Processing Module

Handles incoming webhook events from Paystack for:
- Subscription creation (upgrade to Pro)
- Subscription disable (downgrade to Free)
- Webhook signature validation (HMAC SHA-512)

All webhook events update user tier atomically.
"""

import os
import hmac
import hashlib
import json
from typing import Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models import User, Subscription
from database import UserTier


def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Validate Paystack webhook signature using HMAC SHA-512.
    
    Verifies that the webhook request came from Paystack and has not
    been tampered with. Uses PAYSTACK_WEBHOOK_SECRET from environment.
    
    Args:
        payload: Raw request body as bytes
        signature: X-Paystack-Signature header value
    
    Returns:
        True if signature is valid, False otherwise
    
    Example:
        is_valid = validate_webhook_signature(
            payload=request.body,
            signature=request.headers["X-Paystack-Signature"]
        )
        if not is_valid:
            return {"error": "Invalid signature"}
    """
    secret = os.getenv("PAYSTACK_WEBHOOK_SECRET")
    if not secret:
        raise ValueError("PAYSTACK_WEBHOOK_SECRET environment variable not set")
    
    # Compute HMAC SHA-512 hash
    computed_signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, signature)


def process_webhook(
    event_type: str,
    payload: Dict,
    signature: str,
    db: Session
) -> Dict:
    """
    Process incoming Paystack webhook event.
    
    Handles subscription lifecycle events and updates user tier accordingly.
    All database operations are atomic (within transaction).
    
    Supported events:
    - subscription.create: Upgrade user to Pro tier
    - subscription.disable: Downgrade user to Free tier
    
    Args:
        event_type: Webhook event type (e.g., "subscription.create")
        payload: Event payload as dictionary
        signature: Webhook signature for validation
        db: Database session
    
    Returns:
        Result indicating success (with no data) or error
    
    Example:
        result = process_webhook(
            event_type="subscription.create",
            payload={"data": {...}},
            signature="abc123...",
            db=db
        )
        if result["success"]:
            print("Webhook processed successfully")
    """
    try:
        # Validate webhook signature
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        if not validate_webhook_signature(payload_bytes, signature):
            return {
                "success": False,
                "error": "Invalid webhook signature"
            }
        
        # Route to appropriate handler
        if event_type == "subscription.create":
            return _handle_subscription_create(payload, db)
        elif event_type == "subscription.disable":
            return _handle_subscription_disable(payload, db)
        else:
            # Unknown event type - log but don't fail
            return {
                "success": True,
                "data": None
            }
    
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Malformed webhook payload"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Webhook processing error: {str(e)}"
        }


def _handle_subscription_create(payload: Dict, db: Session) -> Dict:
    """
    Handle subscription.create event.
    
    Upgrades user to Pro tier and creates Subscription record.
    Updates are atomic within a database transaction.
    
    Args:
        payload: Webhook event payload
        db: Database session
    
    Returns:
        Result indicating success or error
    """
    try:
        # Extract subscription data from payload
        data = payload.get("data", {})
        customer = data.get("customer", {})
        email = customer.get("email")
        
        if not email:
            return {
                "success": False,
                "error": "Customer email not found in webhook payload"
            }
        
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {
                "success": False,
                "error": f"User not found with email: {email}"
            }
        
        # Extract subscription details
        paystack_subscription_code= data.get("paystack_subscription_code")
        paystack_customer_code = customer.get("paystack_customer_code")
        plan_code = data.get("plan", {}).get("plan_code")
        
        # Calculate billing period
        current_period_start = datetime.utcnow()
        current_period_end = current_period_start + timedelta(days=30)  # Monthly subscription
        
        # Check if subscription already exists (idempotency)
        existing = db.query(Subscription).filter(
            Subscription.paystack_subscription_code == paystack_subscription_code
        ).first()
        
        if existing:
            # Webhook already processed
            return {
                "success": True,
                "data": None
            }
        
        # Create subscription record
        subscription = Subscription(
            user_id=user.id,
            paystack_subscription_code=paystack_subscription_code,
            paystack_customer_code=paystack_customer_code,
            plan_code=plan_code,
            status="active",
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )
        
        # Upgrade user to Pro tier
        user.tier = UserTier.PRO
        user.updated_at = datetime.utcnow()
        
        # Atomic commit
        db.add(subscription)
        db.commit()
        
        return {
            "success": True,
            "data": None
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
            "error": f"Error processing subscription.create: {str(e)}"
        }


def _handle_subscription_disable(payload: Dict, db: Session) -> Dict:
    """
    Handle subscription.disable event.
    
    Downgrades user to Free tier and updates Subscription status.
    Updates are atomic within a database transaction.
    
    Args:
        payload: Webhook event payload
        db: Database session
    
    Returns:
        Result indicating success or error
    """
    try:
        # Extract subscription data from payload
        data = payload.get("data", {})
        paystack_subscription_code = data.get("paystack_subscription_code")
        
        if not paystack_subscription_code:
            return {
                "success": False,
                "error": "Subscription code not found in webhook payload"
            }
        
        # Find subscription
        subscription = db.query(Subscription).filter(
            Subscription.paystack_subscription_code == paystack_subscription_code
        ).first()
        
        if not subscription:
            return {
                "success": False,
                "error": f"Subscription not found: {paystack_subscription_code}"
            }
        
        # Get associated user
        user = db.query(User).filter(User.id == subscription.user_id).first()
        if not user:
            return {
                "success": False,
                "error": f"User not found for subscription: {paystack_subscription_code}"
            }
        
        # Update subscription status
        subscription.status = "canceled"
        subscription.cancelled_at = datetime.utcnow()
        
        # Downgrade user to Free tier
        user.tier = UserTier.FREE
        user.updated_at = datetime.utcnow()
        
        # Atomic commit
        db.commit()
        
        return {
            "success": True,
            "data": None
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
            "error": f"Error processing subscription.disable: {str(e)}"
        }
