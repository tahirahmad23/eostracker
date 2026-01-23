"""
Subscription Module Tests

Comprehensive test suite covering:
- Checkout session creation
- Subscription retrieval and cancellation
- Webhook processing and signature validation
- Tier upgrades and downgrades
- Edge cases and error handling
"""

import pytest
import os
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import UserTier
from database.models import Base, User, UserTier,Subscription
from subscription import (
    create_checkout_session,
    get_subscription,
    cancel_subscription,
    process_webhook,
    validate_webhook_signature
)


# ============================================================================
# FIXTURES
# ============================================================================
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        tier=UserTier.FREE
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def pro_user(db_session):
    """Create a Pro tier user with active subscription"""
    user = User(
        email="pro@example.com",
        hashed_password="hashed_password",
        full_name="Pro User",
        tier=UserTier.PRO
    )
    db_session.add(user)
    db_session.commit()
    
    subscription = Subscription(
        user_id=user.id,
        paystack_subscription_code="SUB_test123",
        paystack_customer_code="CUS_test123",
        plan_code="PLN_pro",
        status="active",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def mock_paystack_success():
    """Mock successful Paystack API responses"""
    with patch("subscription.service.PaystackClient") as mock:
        instance = mock.return_value
        instance.create_subscription.return_value = {
            "success": True,
            "data": {
                "authorization_url": "https://paystack.com/checkout/abc123",
                "reference": "TRX_test123",
                "access_code": "access_123"
            }
        }
        instance.cancel_subscription.return_value = {
            "success": True,
            "data": {"message": "Subscription cancelled"}
        }
        yield instance


@pytest.fixture
def webhook_secret():
    """Set webhook secret for tests"""
    secret = "test_webhook_secret_key_12345"
    os.environ["PAYSTACK_WEBHOOK_SECRET"] = secret
    yield secret
    del os.environ["PAYSTACK_WEBHOOK_SECRET"]


# ============================================================================
# SERVICE TESTS - CHECKOUT SESSION
# ============================================================================

def test_create_checkout_session_success(test_user, db_session, mock_paystack_success):
    """Test successful checkout session creation"""
    result = create_checkout_session(
        user_id=test_user.id,
        success_url="https://app.com/success",
        cancel_url="https://app.com/cancel",
        db=db_session
    )
    
    assert result["success"] is True
    assert "authorization_url" in result["data"]
    assert "reference" in result["data"]
    assert result["data"]["authorization_url"] == "https://paystack.com/checkout/abc123"
    
    # Verify Paystack client was called correctly
    mock_paystack_success.create_subscription.assert_called_once_with(
        email=test_user.email,
        customer_name=test_user.full_name,
        callback_url="https://app.com/success"
    )


def test_create_checkout_invalid_user(db_session, mock_paystack_success):
    """Test checkout session fails for non-existent user"""
    result = create_checkout_session(
        user_id=99999,
        success_url="https://app.com/success",
        cancel_url="https://app.com/cancel",
        db=db_session
    )
    
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_create_checkout_already_subscribed(pro_user, db_session, mock_paystack_success):
    """Test checkout fails if user already has active subscription"""
    result = create_checkout_session(
        user_id=pro_user.id,
        success_url="https://app.com/success",
        cancel_url="https://app.com/cancel",
        db=db_session
    )
    
    assert result["success"] is False
    assert "already has an active subscription" in result["error"]


def test_create_checkout_returns_authorization_url(test_user, db_session, mock_paystack_success):
    """Test checkout session returns valid authorization URL format"""
    result = create_checkout_session(
        user_id=test_user.id,
        success_url="https://app.com/success",
        cancel_url="https://app.com/cancel",
        db=db_session
    )
    
    assert result["success"] is True
    assert result["data"]["authorization_url"].startswith("https://")
    assert len(result["data"]["reference"]) > 0


def test_create_checkout_paystack_api_error(test_user, db_session):
    """Test checkout handles Paystack API errors gracefully"""
    with patch("subscription.service.PaystackClient") as mock:
        instance = mock.return_value
        instance.create_subscription.return_value = {
            "success": False,
            "error": "Paystack API error: Invalid plan code"
        }
        
        result = create_checkout_session(
            user_id=test_user.id,
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
            db=db_session
        )
        
        assert result["success"] is False
        assert "Paystack API error" in result["error"]


# ============================================================================
# SERVICE TESTS - GET SUBSCRIPTION
# ============================================================================

def test_get_subscription_exists(pro_user, db_session):
    """Test retrieving existing subscription"""
    result = get_subscription(user_id=pro_user.id, db=db_session)
    
    assert result["success"] is True
    assert result["data"] is not None
    assert result["data"]["paystack_subscription_code"] == "SUB_test123"
    assert result["data"]["status"] == "active"
    assert result["data"]["plan_code"] == "PLN_pro"


def test_get_subscription_none(test_user, db_session):
    """Test retrieving subscription for user with no subscription"""
    result = get_subscription(user_id=test_user.id, db=db_session)
    
    assert result["success"] is True
    assert result["data"] is None


def test_get_subscription_invalid_user(db_session):
    """Test get subscription fails for non-existent user"""
    result = get_subscription(user_id=99999, db=db_session)
    
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_get_subscription_includes_all_fields(pro_user, db_session):
    """Test subscription data includes all required fields"""
    result = get_subscription(user_id=pro_user.id, db=db_session)
    
    assert result["success"] is True
    data = result["data"]
    assert "id" in data
    assert "paystack_subscription_code" in data
    assert "paystack_customer_code" in data
    assert "plan_code" in data
    assert "status" in data
    assert "current_period_start" in data
    assert "current_period_end" in data
    assert "created_at" in data
    assert "cancelled_at" in data


# ============================================================================
# SERVICE TESTS - CANCEL SUBSCRIPTION
# ============================================================================

def test_cancel_subscription_success(pro_user, db_session, mock_paystack_success):
    """Test successful subscription cancellation"""
    result = cancel_subscription(user_id=pro_user.id, db=db_session)
    
    assert result["success"] is True
    assert result["data"]["status"] == "canceled"
    assert "cancelled_at" in result["data"]
    
    # Verify user downgraded to Free tier
    db_session.refresh(pro_user)
    assert pro_user.tier == UserTier.FREE
    
    # Verify Paystack API was called
    mock_paystack_success.cancel_subscription.assert_called_once()


def test_cancel_subscription_none(test_user, db_session):
    """Test cancel fails when no active subscription exists"""
    result = cancel_subscription(user_id=test_user.id, db=db_session)
    
    assert result["success"] is False
    assert "No active subscription" in result["error"]


def test_cancel_subscription_invalid_user(db_session):
    """Test cancel fails for non-existent user"""
    result = cancel_subscription(user_id=99999, db=db_session)
    
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_cancel_subscription_updates_tier(pro_user, db_session, mock_paystack_success):
    """Test cancellation downgrades user tier to Free"""
    # Verify user is Pro before cancellation
    assert pro_user.tier == UserTier.PRO
    
    result = cancel_subscription(user_id=pro_user.id, db=db_session)
    assert result["success"] is True
    
    # Verify tier updated
    db_session.refresh(pro_user)
    assert pro_user.tier == UserTier.FREE


def test_cancel_subscription_paystack_error(pro_user, db_session):
    """Test cancel handles Paystack API errors"""
    with patch("subscription.service.PaystackClient") as mock:
        instance = mock.return_value
        instance.cancel_subscription.return_value = {
            "success": False,
            "error": "Paystack API error: Subscription not found"
        }
        
        result = cancel_subscription(user_id=pro_user.id, db=db_session)
        
        assert result["success"] is False
        assert "Paystack API error" in result["error"]


# ============================================================================
# WEBHOOK TESTS - SIGNATURE VALIDATION
# ============================================================================

def test_webhook_signature_validation(webhook_secret):
    """Test HMAC SHA-512 signature validation works correctly"""
    payload = b'{"event": "subscription.create", "data": {}}'
    
    # Generate valid signature
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    assert validate_webhook_signature(payload, signature) is True


def test_webhook_invalid_signature(webhook_secret):
    """Test invalid signature is rejected"""
    payload = b'{"event": "subscription.create", "data": {}}'
    invalid_signature = "invalid_signature_12345"
    
    assert validate_webhook_signature(payload, invalid_signature) is False


def test_webhook_tampered_payload(webhook_secret):
    """Test signature fails for tampered payload"""
    original_payload = b'{"event": "subscription.create", "data": {}}'
    tampered_payload = b'{"event": "subscription.create", "data": {"amount": 0}}'
    
    # Generate signature for original
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=original_payload,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    # Validation should fail for tampered payload
    assert validate_webhook_signature(tampered_payload, signature) is False


# ============================================================================
# WEBHOOK TESTS - EVENT PROCESSING
# ============================================================================

def test_webhook_subscription_create(test_user, db_session, webhook_secret):
    """Test subscription.create webhook upgrades user to Pro"""
    payload = {
        "event": "subscription.create",
        "data": {
            "paystack_subscription_code": "SUB_webhook123",
            "customer": {
                "email": test_user.email,
                "paystack_customer_code": "CUS_webhook123"
            },
            "plan": {
                "plan_code": "PLN_pro"
            }
        }
    }
    
    # Generate valid signature
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    result = process_webhook(
        event_type="subscription.create",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    assert result["success"] is True
    
    # Verify user upgraded to Pro
    db_session.refresh(test_user)
    assert test_user.tier == UserTier.PRO
    
    # Verify subscription record created
    subscription = db_session.query(Subscription).filter(
        Subscription.user_id == test_user.id
    ).first()
    assert subscription is not None
    assert subscription.paystack_subscription_code == "SUB_webhook123"
    assert subscription.status == "active"


def test_webhook_subscription_disable(pro_user, db_session, webhook_secret):
    """Test subscription.disable webhook downgrades user to Free"""
    # Get existing subscription
    subscription = db_session.query(Subscription).filter(
        Subscription.user_id == pro_user.id
    ).first()
    
    payload = {
        "event": "subscription.disable",
        "data": {
            "paystack_subscription_code": subscription.paystack_subscription_code
        }
    }
    
    # Generate valid signature
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    result = process_webhook(
        event_type="subscription.disable",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    assert result["success"] is True
    
    # Verify user downgraded to Free
    db_session.refresh(pro_user)
    assert pro_user.tier == UserTier.FREE
    
    # Verify subscription cancelled
    db_session.refresh(subscription)
    assert subscription.status == "canceled"
    assert subscription.cancelled_at is not None


def test_webhook_invalid_signature_rejected(test_user, db_session, webhook_secret):
    """Test webhook with invalid signature is rejected"""
    payload = {
        "event": "subscription.create",
        "data": {
            "customer": {"email": test_user.email}
        }
    }
    
    invalid_signature = "totally_invalid_signature"
    
    result = process_webhook(
        event_type="subscription.create",
        payload=payload,
        signature=invalid_signature,
        db=db_session
    )
    
    assert result["success"] is False
    assert "Invalid webhook signature" in result["error"]


def test_webhook_unknown_event_type(test_user, db_session, webhook_secret):
    """Test unknown event type is handled gracefully"""
    payload = {
        "event": "unknown.event.type",
        "data": {}
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    result = process_webhook(
        event_type="unknown.event.type",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    # Should succeed but do nothing
    assert result["success"] is True


def test_webhook_malformed_payload(db_session, webhook_secret):
    """Test malformed JSON payload is handled"""
    # This would normally be caught before reaching process_webhook
    # but we test the error handling anyway
    payload = {
        "event": "subscription.create",
        "data": {}  # Missing required fields
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    result = process_webhook(
        event_type="subscription.create",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    assert result["success"] is False
    assert "email not found" in result["error"].lower()


# ============================================================================
# WEBHOOK TESTS - TIER UPDATES
# ============================================================================

def test_tier_update_after_create(test_user, db_session, webhook_secret):
    """Test user tier is updated correctly after subscription.create"""
    # Verify user starts as Free
    assert test_user.tier == UserTier.FREE
    
    payload = {
        "event": "subscription.create",
        "data": {
            "paystack_subscription_code": "SUB_tier_test",
            "customer": {
                "email": test_user.email,
                "paystack_customer_code": "CUS_tier_test"
            },
            "plan": {
                "plan_code": "PLN_pro"
            }
        }
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    result = process_webhook(
        event_type="subscription.create",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    assert result["success"] is True
    
    # Verify tier updated
    db_session.refresh(test_user)
    assert test_user.tier == UserTier.PRO


def test_tier_update_after_disable(pro_user, db_session, webhook_secret):
    """Test user tier is reverted after subscription.disable"""
    # Verify user starts as Pro
    assert pro_user.tier == UserTier.PRO
    
    subscription = db_session.query(Subscription).filter(
        Subscription.user_id == pro_user.id
    ).first()
    
    payload = {
        "event": "subscription.disable",
        "data": {
            "paystack_subscription_code": subscription.paystack_subscription_code
        }
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    result = process_webhook(
        event_type="subscription.disable",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    assert result["success"] is True
    
    # Verify tier reverted to Free
    db_session.refresh(pro_user)
    assert pro_user.tier == UserTier.FREE


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_subscription_record_created_correctly(test_user, db_session, webhook_secret):
    """Test subscription record has all required fields"""
    payload = {
        "event": "subscription.create",
        "data": {
            "paystack_subscription_code": "SUB_record_test",
            "customer": {
                "email": test_user.email,
                "paystack_customer_code": "CUS_record_test"
            },
            "plan": {
                "plan_code": "PLN_pro_monthly"
            }
        }
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    process_webhook(
        event_type="subscription.create",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    subscription = db_session.query(Subscription).filter(
        Subscription.user_id == test_user.id
    ).first()
    print(subscription.cancelled_at)
    assert subscription is not None
    assert subscription.paystack_subscription_code == "SUB_record_test"
    assert subscription.paystack_customer_code == "CUS_record_test"
    assert subscription.plan_code == "PLN_pro_monthly"
    assert subscription.status == "active"
    assert subscription.current_period_start is not None
    assert subscription.current_period_end is not None
    assert subscription.cancelled_at is None


def test_subscription_cancellation_updates_status(pro_user, db_session, mock_paystack_success):
    """Test cancellation updates subscription status in database"""
    subscription_before = db_session.query(Subscription).filter(
        Subscription.user_id == pro_user.id
    ).first()
    
    assert subscription_before.status == "active"
    assert subscription_before.cancelled_at is None
    
    cancel_subscription(user_id=pro_user.id, db=db_session)
    
    db_session.refresh(subscription_before)
    assert subscription_before.status == "canceled"
    assert subscription_before.cancelled_at is not None


def test_idempotent_webhook_processing(test_user, db_session, webhook_secret):
    """Test webhook can be processed multiple times safely (idempotency)"""
    payload = {
        "event": "subscription.create",
        "data": {
            "paystack_subscription_code": "SUB_idempotent",
            "customer": {
                "email": test_user.email,
                "paystack_customer_code": "CUS_idempotent"
            },
            "plan": {
                "plan_code": "PLN_pro"
            }
        }
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    # Process webhook twice
    result1 = process_webhook(
        event_type="subscription.create",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    result2 = process_webhook(
        event_type="subscription.create",
        payload=payload,
        signature=signature,
        db=db_session
    )
    
    assert result1["success"] is True
    assert result2["success"] is True
    
    # Verify only one subscription created
    count = db_session.query(Subscription).filter(
        Subscription.paystack_subscription_code == "SUB_idempotent"
    ).count()
    assert count == 1
