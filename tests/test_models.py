
from sqlalchemy.exc import IntegrityError
from database.models import User, Device, TrackedDevice, UserTier, AlertType
from datetime import date, datetime, timedelta
import pytest

def test_create_user(db):
    user = User(
        email="new@example.com",
        hashed_password="hashed",
        full_name="New User",
        tier=UserTier.FREE
    )
    db.add(user)
    db.commit()
    
    assert user.id is not None
    assert user.email == "new@example.com"
    assert user.tier == "free"

def test_user_email_unique(db):
    user1 = User(
        email="duplicate@example.com",
        hashed_password="hashed",
        full_name="User 1"
    )
    db.add(user1)
    db.commit()
    
    user2 = User(
        email="duplicate@example.com",
        hashed_password="hashed",
        full_name="User 2"
    )
    db.add(user2)
    
    with pytest.raises(IntegrityError):
        db.commit()

def test_create_device(db):
    device = Device(
        vendor="Cisco",
        model="Catalyst 9300",
        device_type="Switch",
        eos_date=date(2025, 1, 1),
        slug="cisco-catalyst-9300"
    )
    db.add(device)
    db.commit()
    
    assert device.id is not None
    assert device.vendor == "Cisco"
    
def test_device_slug_unique(db):
    device1 = Device(
        vendor="A", model="A", device_type="A", 
        eos_date=date.today(), slug="unique-slug"
    )
    db.add(device1)
    db.commit()
    
    device2 = Device(
        vendor="B", model="B", device_type="B", 
        eos_date=date.today(), slug="unique-slug"
    )
    db.add(device2)
    
    with pytest.raises(IntegrityError):
        db.commit()

def test_tracked_device_relationship(db, test_user):
    # Create device
    device = Device(
        vendor="Juniper",
        model="EX4300",
        device_type="Switch",
        eos_date=date(2026, 1, 1),
        slug="juniper-ex4300"
    )
    db.add(device)
    db.commit()
    
    # Track it
    track = TrackedDevice(
        user_id=test_user.id,
        device_id=device.id,
        custom_name="Office Switch"
    )
    db.add(track)
    db.commit()
    
    assert len(test_user.tracked_devices) == 1
    assert test_user.tracked_devices[0].device.vendor == "Juniper"
    assert test_user.tracked_devices[0].custom_name == "Office Switch"

def test_tracked_device_unique_per_user(db, test_user):
    device = Device(
        vendor="Test", model="T1", device_type="T", 
        eos_date=date.today(), slug="t1"
    )
    db.add(device)
    db.commit()
    
    # Track once
    t1 = TrackedDevice(user_id=test_user.id, device_id=device.id)
    db.add(t1)
    db.commit()
    
    # Track again (should fail)
    t2 = TrackedDevice(user_id=test_user.id, device_id=device.id)
    db.add(t2)
    
    with pytest.raises(IntegrityError):
        db.commit()
