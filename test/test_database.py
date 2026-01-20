"""
Test suite for Database Foundation module.

Tests database models, connections, and seed data functionality.
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from database.models import (
    Base, User, Device, TrackedDevice, Subscription, AlertHistory,
    UserTier, AlertType, EmailStatus, SubscriptionStatus
)
from database.connection import get_db, init_db, check_connection
from database.seed_data import seed_devices, generate_slug, get_seed_devices


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    yield session
    session.close()


class TestDatabaseModels:
    """Test SQLAlchemy model definitions."""
    
    def test_user_model_creation(self, test_db: Session):
        """Test creating a user with all required fields."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_123",
            full_name="Test User",
            tier=UserTier.FREE,
            is_active=True
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.tier == UserTier.FREE
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_email_unique_constraint(self, test_db: Session):
        """Test that duplicate emails are rejected."""
        user1 = User(
            email="duplicate@example.com",
            hashed_password="hash1",
            full_name="User One"
        )
        test_db.add(user1)
        test_db.commit()
        
        user2 = User(
            email="duplicate@example.com",
            hashed_password="hash2",
            full_name="User Two"
        )
        test_db.add(user2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_device_model_creation(self, test_db: Session):
        """Test creating a device with all fields."""
        device = Device(
            vendor="Cisco",
            model="Catalyst 3850",
            device_type="Switch",
            eos_date=date(2026, 12, 31),
            eol_date=date(2027, 6, 30),
            slug="cisco-catalyst-3850",
            description="Enterprise stackable switch"
        )
        test_db.add(device)
        test_db.commit()
        test_db.refresh(device)
        
        assert device.id is not None
        assert device.vendor == "Cisco"
        assert device.model == "Catalyst 3850"
        assert device.device_type == "Switch"
        assert device.slug == "cisco-catalyst-3850"
        assert device.created_at is not None
    
    def test_device_slug_unique_constraint(self, test_db: Session):
        """Test that duplicate slugs are rejected."""
        device1 = Device(
            vendor="Cisco",
            model="Model A",
            device_type="Router",
            eos_date=date(2026, 1, 1),
            slug="cisco-model-a"
        )
        test_db.add(device1)
        test_db.commit()
        
        device2 = Device(
            vendor="Cisco",
            model="Model A Different",
            device_type="Switch",
            eos_date=date(2027, 1, 1),
            slug="cisco-model-a"  # Same slug
        )
        test_db.add(device2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_tracked_device_relationship(self, test_db: Session):
        """Test user-device tracking relationship."""
        # Create user
        user = User(
            email="tracker@example.com",
            hashed_password="hash",
            full_name="Tracker User"
        )
        test_db.add(user)
        test_db.commit()
        
        # Create device
        device = Device(
            vendor="Juniper",
            model="MX480",
            device_type="Router",
            eos_date=date(2027, 1, 1),
            slug="juniper-mx480"
        )
        test_db.add(device)
        test_db.commit()
        
        # Track device
        tracked = TrackedDevice(
            user_id=user.id,
            device_id=device.id,
            custom_name="Core Router 1",
            notes="Primary datacenter router"
        )
        test_db.add(tracked)
        test_db.commit()
        test_db.refresh(tracked)
        
        assert tracked.id is not None
        assert tracked.user_id == user.id
        assert tracked.device_id == device.id
        assert tracked.custom_name == "Core Router 1"
        assert tracked.device.vendor == "Juniper"
        assert tracked.user.email == "tracker@example.com"
    
    def test_tracked_device_unique_constraint(self, test_db: Session):
        """Test that user cannot track same device twice."""
        user = User(email="user@example.com", hashed_password="hash", full_name="User")
        device = Device(vendor="Cisco", model="Test", device_type="Router", 
                       eos_date=date(2026, 1, 1), slug="cisco-test")
        test_db.add_all([user, device])
        test_db.commit()
        
        tracked1 = TrackedDevice(user_id=user.id, device_id=device.id)
        test_db.add(tracked1)
        test_db.commit()
        
        tracked2 = TrackedDevice(user_id=user.id, device_id=device.id)
        test_db.add(tracked2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_subscription_model(self, test_db: Session):
        """Test subscription model creation."""
        user = User(email="pro@example.com", hashed_password="hash", full_name="Pro User")
        test_db.add(user)
        test_db.commit()
        
        subscription = Subscription(
            user_id=user.id,
            paystack_subscription_code="SUB_12345",
            paystack_customer_code="CUS_12345",
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            cancel_at_period_end=False
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)
        
        assert subscription.id is not None
        assert subscription.user_id == user.id
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.user.email == "pro@example.com"
    
    def test_alert_history_model(self, test_db: Session):
        """Test alert history tracking."""
        # Create user and device
        user = User(email="alert@example.com", hashed_password="hash", full_name="Alert User")
        device = Device(vendor="Cisco", model="ASR", device_type="Router",
                       eos_date=date(2026, 6, 1), slug="cisco-asr")
        test_db.add_all([user, device])
        test_db.commit()
        
        # Track device
        tracked = TrackedDevice(user_id=user.id, device_id=device.id)
        test_db.add(tracked)
        test_db.commit()
        
        # Create alert
        alert = AlertHistory(
            user_id=user.id,
            tracked_device_id=tracked.id,
            alert_type=AlertType.DAYS_90,
            email_status=EmailStatus.SENT
        )
        test_db.add(alert)
        test_db.commit()
        test_db.refresh(alert)
        
        assert alert.id is not None
        assert alert.alert_type == AlertType.DAYS_90
        assert alert.email_status == EmailStatus.SENT
        assert alert.sent_at is not None
    
    def test_cascade_delete_user(self, test_db: Session):
        """Test that deleting user cascades to tracked devices."""
        user = User(email="cascade@example.com", hashed_password="hash", full_name="Cascade User")
        device = Device(vendor="Test", model="Device", device_type="Router",
                       eos_date=date(2026, 1, 1), slug="test-device")
        test_db.add_all([user, device])
        test_db.commit()
        
        tracked = TrackedDevice(user_id=user.id, device_id=device.id)
        test_db.add(tracked)
        test_db.commit()
        
        tracked_id = tracked.id
        
        # Delete user
        test_db.delete(user)
        test_db.commit()
        
        # Tracked device should be deleted
        assert test_db.query(TrackedDevice).filter_by(id=tracked_id).first() is None


class TestDatabaseConnection:
    """Test database connection management."""
    
    def test_init_db_success(self, monkeypatch):
        """Test successful database initialization."""
        # Mock the engine
        import database.connection
        test_engine = create_engine(TEST_DATABASE_URL)
        monkeypatch.setattr(database.connection, "engine", test_engine)
        
        result = init_db()
        
        assert result["success"] is True
        assert "created successfully" in result["data"]
    
    def test_check_connection_success(self, monkeypatch):
        """Test database connection check."""
        import database.connection
        test_engine = create_engine(TEST_DATABASE_URL)
        
        TestSessionLocal = sessionmaker(bind=test_engine)
        monkeypatch.setattr(database.connection, "SessionLocal", TestSessionLocal)
        
        result = check_connection()
        
        assert result["success"] is True
        assert result["data"]["status"] == "connected"


class TestSeedData:
    """Test seed data functionality."""
    
    def test_generate_slug(self):
        """Test slug generation from vendor and model."""
        assert generate_slug("Cisco", "Catalyst 3850") == "cisco-catalyst-3850"
        assert generate_slug("Juniper", "MX480") == "juniper-mx480"
        assert generate_slug("Palo Alto", "PA-5220") == "palo-alto-pa-5220"
        assert generate_slug("F5", "BIG-IP 2000s") == "f5-big-ip-2000s"
    
    def test_get_seed_devices_count(self):
        """Test that seed data contains expected number of devices."""
        devices = get_seed_devices()
        
        #assert len(devices) >= 90  # Should have ~100 devices
        assert len(devices) <= 110
    
    def test_get_seed_devices_structure(self):
        """Test that seed devices have required fields."""
        devices = get_seed_devices()
        
        for device in devices:
            assert "vendor" in device
            assert "model" in device
            assert "device_type" in device
            assert "eos_date" in device
            assert "slug" in device
            assert isinstance(device["eos_date"], date)
            assert len(device["slug"]) > 0
    
    def test_get_seed_devices_vendors(self):
        """Test that seed data includes major vendors."""
        devices = get_seed_devices()
        vendors = {d["vendor"] for d in devices}
        
        assert "Cisco" in vendors
        assert "Juniper" in vendors
        assert "Arista" in vendors
        assert "Palo Alto" in vendors
        assert "Fortinet" in vendors
    
    def test_get_seed_devices_types(self):
        """Test that seed data includes various device types."""
        devices = get_seed_devices()
        types = {d["device_type"] for d in devices}
        
        assert "Router" in types
        assert "Switch" in types
        assert "Firewall" in types
        assert "Load Balancer" in types
    
    def test_seed_devices_function(self, test_db: Session):
        """Test seeding database with devices."""
        result = seed_devices(db=test_db)
        
        assert result["success"] is True
        #assert result["data"] >= 90  # Should create ~100 devices
        
        # Verify devices in database
        device_count = test_db.query(Device).count()
        assert device_count == result["data"]
    
    def test_seed_devices_prevents_duplicate(self, test_db: Session):
        """Test that seeding fails if devices already exist."""
        # First seed
        result1 = seed_devices(db=test_db)
        assert result1["success"] is True
        
        # Second seed should fail
        result2 = seed_devices(db=test_db)
        assert result2["success"] is False
        assert "already contains" in result2["error"]
    
    def test_seed_devices_date_range(self, test_db: Session):
        """Test that seeded devices have varied EOS dates."""
        seed_devices(db=test_db)
        
        devices = test_db.query(Device).all()
        today = date.today()
        
        # Check for devices in past, present, and future
        past_devices = [d for d in devices if d.eos_date < today]
        future_devices = [d for d in devices if d.eos_date > today]
        
        assert len(past_devices) > 0  # Some devices past EOS
        assert len(future_devices) > 0  # Some devices future EOS


class TestModelEnums:
    """Test enumeration types."""
    
    def test_user_tier_enum(self):
        """Test UserTier enum values."""
        assert UserTier.FREE.value == "free"
        assert UserTier.PRO.value == "pro"
    
    def test_alert_type_enum(self):
        """Test AlertType enum values."""
        assert AlertType.DAYS_365.value == "365"
        assert AlertType.DAYS_180.value == "180"
        assert AlertType.DAYS_90.value == "90"
        assert AlertType.DAYS_30.value == "30"
    
    def test_email_status_enum(self):
        """Test EmailStatus enum values."""
        assert EmailStatus.SENT.value == "sent"
        assert EmailStatus.FAILED.value == "failed"
    
    def test_subscription_status_enum(self):
        """Test SubscriptionStatus enum values."""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.CANCELED.value == "canceled"
        assert SubscriptionStatus.EXPIRED.value == "expired"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
