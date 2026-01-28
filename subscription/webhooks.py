"""
Lemon Squeezy Webhook Processing Module

Handles incoming webhook events from Lemon Squeezy for:
- Subscription creation (upgrade to Pro)
- Subscription updates (renewals, status changes)
- Subscription cancellation/expiration (downgrade to Free)
- Webhook signature validation (HMAC SHA-256)

All webhook events update user tier atomically.
"""

import os
import hmac
import hashlib
import json
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from database.models import User, Subscription
from database import UserTier

logger = logging.getLogger(__name__)

def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Validate Lemon Squeezy webhook signature using HMAC SHA-256.
    
    Verifies that the webhook request came from Lemon Squeezy and has not
    been tampered with. Uses LEMONSQUEEZY_WEBHOOK_SECRET from environment.
    
    Args:
        payload: Raw request body as bytes
        signature: X-Signature header value
    
    Returns:
        True if signature is valid, False otherwise
    
    Example:
        is_valid = validate_webhook_signature(
            payload=request.body,
            signature=request.headers["X-Signature"]
        )
        if not is_valid:
            return {"error": "Invalid signature"}
    """
    secret = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
    if not secret:
        raise ValueError("LEMONSQUEEZY_WEBHOOK_SECRET environment variable not set")
    
    # Compute HMAC SHA-256 hash
    computed_signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, signature)


def process_webhook(
    event_name: str,
    payload: Dict,
    raw_payload: bytes,
    signature: str,
    db: Session
) -> Dict:
    """
    Process incoming Lemon Squeezy webhook event.
    
    Handles subscription lifecycle events and updates user tier accordingly.
    All database operations are atomic (within transaction).
    
    Supported events:
    - subscription_created: Upgrade user to Pro tier
    - subscription_updated: Handle status changes (active, cancelled, expired, etc.)
    - subscription_payment_success: Handle successful recurring payments
    
    Args:
        event_name: Webhook event name (e.g., "subscription_created")
        payload: Event payload as dictionary
        raw_payload: Raw request body as bytes (for signature validation)
        signature: Webhook signature for validation
        db: Database session
    
    Returns:
        Result indicating success (with no data) or error
    
    Example:
        result = process_webhook(
            event_name="subscription_created",
            payload={"data": {...}},
            raw_payload=b'...',
            signature="abc123...",
            db=db
        )
        if result["success"]:
            print("Webhook processed successfully")
    """
    try:
        # Validate webhook signature using raw payload
        if not validate_webhook_signature(raw_payload, signature):
            logger.warning("Webhook signature invalid")
            return {
                "success": False,
                "error": "Invalid webhook signature"
            }
        
        # Route to appropriate handler
        if event_name == "subscription_created":
            return _handle_subscription_created(payload, db)
        elif event_name == "subscription_updated":
            return _handle_subscription_updated(payload, db)
        elif event_name == "subscription_payment_success":
            return _handle_payment_success(payload, db)
        else:
            # Unknown event type - acknowledge but don't process
            logger.info("Unhandled webhook event received", extra={"event_name": str(event_name)})
            return {
                "success": True,
                "data": None
            }
    
    except Exception as e:
        logger.exception("Webhook processing error")
        return {
            "success": False,
            "error": f"Webhook processing error: {str(e)}"
        }


def _handle_subscription_created(payload: Dict, db: Session) -> Dict:
    """
    Handle subscription_created event.
    
    This event is sent when a subscription is successfully created.
    Upgrades user to Pro tier and creates subscription record.
    """
    try:
        # Extract subscription data from payload
        data = payload.get("data", {})
        attributes = data.get("attributes", {})
        
        # Get subscription details
        subscription_id = data.get("id")
        customer_id = attributes.get("customer_id")
        order_id = attributes.get("order_id")
        product_id = attributes.get("product_id")
        variant_id = attributes.get("variant_id")
        status = attributes.get("status")
        user_email = attributes.get("user_email")
        
        # Get custom data (contains our user_id)
        meta = payload.get("meta", {})
        custom_data = meta.get("custom_data", {})
        user_id_str = custom_data.get("user_id")
        
        if not subscription_id:
            return {
                "success": False,
                "error": "Subscription ID not found in webhook payload"
            }
        
        # Find user - try by custom user_id first, then by email
        user = None
        if user_id_str:
            try:
                user_id = int(user_id_str)
                user = db.query(User).filter(User.id == user_id).first()
            except (ValueError, TypeError):
                pass
        
        if not user and user_email:
            user = db.query(User).filter(User.email == user_email).first()
        
        if not user:
            return {
                "success": False,
                "error": f"User not found with email: {user_email}"
            }
        
        # Calculate billing period from attributes
        renews_at = attributes.get("renews_at")
        current_period_end = datetime.fromisoformat(renews_at.replace('Z', '+00:00')) if renews_at else None
        current_period_start = datetime.utcnow()
        
        # Check if subscription already exists (idempotency)
        existing = db.query(Subscription).filter(
            Subscription.lemonsqueezy_subscription_id == subscription_id
        ).first()
        
        if existing:
            logger.info("Subscription already exists, skipping creation")
            return {"success": True, "data": None}
        
        # Create subscription record
        subscription = Subscription(
            user_id=user.id,
            lemonsqueezy_subscription_id=subscription_id,
            lemonsqueezy_customer_id=str(customer_id) if customer_id else None,
            lemonsqueezy_order_id=str(order_id) if order_id else None,
            lemonsqueezy_product_id=str(product_id) if product_id else None,
            lemonsqueezy_variant_id=str(variant_id) if variant_id else None,
            status=status or "active",
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )
        
        # Upgrade user to Pro tier
        user.tier = UserTier.PRO
        user.updated_at = datetime.utcnow()
        
        # Atomic commit
        db.add(subscription)
        db.commit()

        logger.info("Subscription created via webhook (user upgraded)")
        
        return {"success": True, "data": None}
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Database error in subscription_created")
        return {"success": False, "error": f"Database error: {str(e)}"}
    except Exception as e:
        db.rollback()
        logger.exception("Error processing subscription_created")
        return {"success": False, "error": f"Error processing subscription_created: {str(e)}"}


def _handle_subscription_updated(payload: Dict, db: Session) -> Dict:
    """
    Handle subscription_updated event.
    
    This event is sent whenever a subscription changes status.
    Updates subscription status and user tier accordingly.
    """
    try:
        # Extract subscription data from payload
        data = payload.get("data", {})
        attributes = data.get("attributes", {})
        
        subscription_id = data.get("id")
        status = attributes.get("status")
        cancelled = attributes.get("cancelled", False)
        
        if not subscription_id:
            return {
                "success": False,
                "error": "Subscription ID not found in webhook payload"
            }
        
        # Find subscription
        subscription = db.query(Subscription).filter(
            Subscription.lemonsqueezy_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            # Subscription might not exist yet if this event fired before subscription_created
            # Just acknowledge it
            logger.info("Subscription not found for update; may be out of order")
            return {"success": True, "data": None}
        
        # Get associated user
        user = db.query(User).filter(User.id == subscription.user_id).first()
        if not user:
            return {
                "success": False,
                "error": f"User not found for subscription: {subscription_id}"
            }
        
        # Update subscription status
        old_status = subscription.status
        subscription.status = status
        
        # Update billing period if available
        renews_at = attributes.get("renews_at")
        if renews_at:
            subscription.current_period_end = datetime.fromisoformat(renews_at.replace('Z', '+00:00'))
        
        # Handle tier changes based on status
        if status == "active" and not cancelled:
            # Subscription is active - ensure user is Pro
            if user.tier != UserTier.PRO:
                user.tier = UserTier.PRO
                logger.info("User upgraded to PRO via webhook", extra={"status": str(status)})
        
        elif status in ["cancelled", "expired", "past_due", "unpaid"]:
            # Subscription ended or has issues - downgrade to Free
            if cancelled or status in ["expired"]:
                subscription.cancelled_at = datetime.utcnow()
            
            if user.tier == UserTier.PRO:
                user.tier = UserTier.FREE
                logger.info("User downgraded to FREE via webhook", extra={"status": str(status)})
        
        user.updated_at = datetime.utcnow()
        
        # Atomic commit
        db.commit()

        logger.info(
            "Subscription updated via webhook",
            extra={"old_status": str(old_status), "new_status": str(status)},
        )
        
        return {"success": True, "data": None}
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Database error in subscription_updated")
        return {"success": False, "error": f"Database error: {str(e)}"}
    except Exception as e:
        db.rollback()
        logger.exception("Error processing subscription_updated")
        return {"success": False, "error": f"Error processing subscription_updated: {str(e)}"}


def _handle_payment_success(payload: Dict, db: Session) -> Dict:
    """
    Handle subscription_payment_success event.
    
    This is sent when a recurring payment succeeds.
    Updates the billing period.
    """
    try:
        data = payload.get("data", {})
        attributes = data.get("attributes", {})
        
        subscription_id = data.get("id")
        
        if subscription_id:
            # Update subscription's billing period
            subscription = db.query(Subscription).filter(
                Subscription.lemonsqueezy_subscription_id == subscription_id
            ).first()
            
            if subscription:
                # Update billing period
                renews_at = attributes.get("renews_at")
                if renews_at:
                    subscription.current_period_start = datetime.utcnow()
                    subscription.current_period_end = datetime.fromisoformat(renews_at.replace('Z', '+00:00'))
                    db.commit()

                logger.info("Recurring payment processed via webhook")
        
        return {"success": True, "data": None}
    
    except Exception as e:
        db.rollback()
        logger.exception("Error processing subscription_payment_success")
        return {"success": True, "data": None}  # Don't fail on update errors
