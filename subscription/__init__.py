"""
Subscription Module

Provides subscription management functionality including:
- Paystack checkout session creation
- Subscription status retrieval
- Subscription cancellation
- Webhook event processing

Usage:
    from subscription import (
        create_checkout_session,
        get_subscription,
        cancel_subscription,
        process_webhook,
        validate_webhook_signature
    )
"""

from subscription.service import (
    create_checkout_session,
    get_subscription,
    cancel_subscription
)

from subscription.webhooks import (
    process_webhook,
    validate_webhook_signature
)

from subscription.paystack import PaystackClient


__all__ = [
    "create_checkout_session",
    "get_subscription",
    "cancel_subscription",
    "process_webhook",
    "validate_webhook_signature",
    "PaystackClient"
]