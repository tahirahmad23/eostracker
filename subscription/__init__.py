"""
Subscription Module (Lemon Squeezy)

Provides subscription management functionality including:
- Lemon Squeezy checkout session creation (USD globally)
- Subscription status retrieval
- Subscription cancellation
- Webhook event processing

All transactions processed in USD worldwide.
Lemon Squeezy acts as merchant of record, handling taxes and compliance.

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

from subscription.lemonsqueezy import LemonSqueezyClient


__all__ = [
    "create_checkout_session",
    "get_subscription",
    "cancel_subscription",
    "process_webhook",
    "validate_webhook_signature",
    "LemonSqueezyClient"
]
