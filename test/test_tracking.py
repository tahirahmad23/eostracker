"""
Tests for User Tracking Service
Comprehensive test suite covering tier limits, duplicates, CSV import/export, and integration.
"""

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, User, Device, TrackedDevice
from database import UserTier
from tracking import (
    add_tracked_device,
    remove_tracked_device,
    get_user_tracked_devices,
    can_add_device,
    import_from_csv,
    export_to_csv
)


# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database for each test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def free_user(db_session):
    """Create a free tier user"""
    user = User(
        email="free@example.com",
        hashed_password="hashed_password",
        full_name="Free User",
        tier=UserTier.FREE
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def pro_user(db_session):
    """Create a pro tier user"""
    user = User(
        email="pro@example.com",
        hashed_password="hashed_password",
        full_name="Pro User",
        tier=UserTier.PRO
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_devices(db_session):
    """Create sample devices for testing"""
    devices = [
        Device(
            vendor="Cisco",
            model="Catalyst 3850",
            device_type="Switch",
            eos_date=date(2025, 12, 31),
            slug="cisco-catalyst-3850"
        ),
        Device(
            vendor="Juniper",
            model="EX4200",
            device_type="Switch",
            eos_date=date(2026, 6, 30),
            slug="juniper-ex4200"
        ),
        Device(
            vendor="Arista",
            model="7050X",
            device_type="Switch",
            eos_date=date(2024, 3, 15),
            slug="arista-7050x"
        ),
        Device(
            vendor="Palo Alto",
            model="PA-5220",
            device_type="Firewall",
            eos_date=date(2027, 1, 1),
            slug="palo-alto-pa-5220"
        )
    ]
    
    for device in devices:
        db_session.add(device)
    
    db_session.commit()
    
    for device in devices:
        db_session.refresh(device)
    
    return devices


# ==================== Add Tracked Device Tests ====================

class TestAddTrackedDevice:
    
    def test_add_tracked_device_success(self, db_session, free_user, sample_devices):
        """Test free user successfully adds first device"""
        result = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name="Production Switch",
            notes="Main datacenter",
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"]["user_id"] == free_user.id
        assert result["data"]["device"]["model"] == "Catalyst 3850"
        assert result["data"]["custom_name"] == "Production Switch"
        assert result["data"]["notes"] == "Main datacenter"
    
    def test_add_tracked_device_at_limit(self, db_session, free_user, sample_devices):
        """Test free user at 3 device limit cannot add more"""
        # Add 3 devices (max for free tier)
        for i in range(3):
            add_tracked_device(
                user_id=free_user.id,
                device_id=sample_devices[i].id,
                custom_name=None,
                notes=None,
                db=db_session
            )
        
        # Try to add 4th device
        result = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[3].id,
            custom_name=None,
            notes=None,
            db=db_session
        )
        
        assert result["success"] is False
        assert "limited to 3 devices" in result["error"]
    
    def test_add_tracked_device_pro_unlimited(self, db_session, pro_user, sample_devices):
        """Test pro user can add many devices"""
        # Add all 4 devices
        for device in sample_devices:
            result = add_tracked_device(
                user_id=pro_user.id,
                device_id=device.id,
                custom_name=None,
                notes=None,
                db=db_session
            )
            assert result["success"] is True
        
        # Verify all were added
        tracked = db_session.query(TrackedDevice).filter(
            TrackedDevice.user_id == pro_user.id
        ).count()
        assert tracked == 4
    
    def test_add_duplicate_device(self, db_session, free_user, sample_devices):
        """Test adding same device twice returns error"""
        # Add device first time
        result1 = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name=None,
            notes=None,
            db=db_session
        )
        assert result1["success"] is True
        
        # Try to add same device again
        result2 = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name=None,
            notes=None,
            db=db_session
        )
        
        assert result2["success"] is False
        assert "already being tracked" in result2["error"]
    
    def test_add_with_custom_name_and_notes(self, db_session, free_user, sample_devices):
        """Test custom fields are saved correctly"""
        result = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name="Edge Router DC1",
            notes="Critical infrastructure - monitor closely",
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"]["custom_name"] == "Edge Router DC1"
        assert result["data"]["notes"] == "Critical infrastructure - monitor closely"
    
    def test_add_invalid_device_id(self, db_session, free_user):
        """Test adding non-existent device returns error"""
        result = add_tracked_device(
            user_id=free_user.id,
            device_id=99999,
            custom_name=None,
            notes=None,
            db=db_session
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_add_custom_name_too_long(self, db_session, free_user, sample_devices):
        """Test custom name length validation"""
        long_name = "x" * 101  # 101 characters
        
        result = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name=long_name,
            notes=None,
            db=db_session
        )
        
        assert result["success"] is False
        assert "100 characters" in result["error"]


# ==================== Remove Tracked Device Tests ====================

class TestRemoveTrackedDevice:
    
    def test_remove_tracked_device_success(self, db_session, free_user, sample_devices):
        """Test owner successfully removes tracked device"""
        # Add device first
        add_result = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name=None,
            notes=None,
            db=db_session
        )
        tracked_id = add_result["data"]["id"]
        
        # Remove device
        result = remove_tracked_device(
            user_id=free_user.id,
            tracked_device_id=tracked_id,
            db=db_session
        )
        
        assert result["success"] is True
        
        # Verify it was deleted
        tracked = db_session.query(TrackedDevice).filter(
            TrackedDevice.id == tracked_id
        ).first()
        assert tracked is None
    
    def test_remove_not_owned(self, db_session, free_user, pro_user, sample_devices):
        """Test user cannot remove device tracked by another user"""
        # Free user adds device
        add_result = add_tracked_device(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name=None,
            notes=None,
            db=db_session
        )
        tracked_id = add_result["data"]["id"]
        
        # Pro user tries to remove it
        result = remove_tracked_device(
            user_id=pro_user.id,
            tracked_device_id=tracked_id,
            db=db_session
        )
        
        assert result["success"] is False
        assert "only remove devices you are tracking" in result["error"]
    
    def test_remove_non_existent_device(self, db_session, free_user):
        """Test removing non-existent tracked device returns error"""
        result = remove_tracked_device(
            user_id=free_user.id,
            tracked_device_id=99999,
            db=db_session
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]


# ==================== Get Tracked Devices Tests ====================

class TestGetUserTrackedDevices:
    
    def test_get_user_tracked_devices_empty(self, db_session, free_user):
        """Test new user has empty tracked devices list"""
        result = get_user_tracked_devices(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"] == []
    
    def test_get_user_tracked_devices_multiple(self, db_session, free_user, sample_devices):
        """Test returns all user's tracked devices with full info"""
        # Add 3 devices
        for i in range(3):
            add_tracked_device(
                user_id=free_user.id,
                device_id=sample_devices[i].id,
                custom_name=f"Device {i+1}",
                notes=f"Notes for device {i+1}",
                db=db_session
            )
        
        # Get tracked devices
        result = get_user_tracked_devices(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        assert len(result["data"]) == 3
        
        # Verify structure of first device
        first = result["data"][0]
        assert "id" in first
        assert "user_id" in first
        assert "device" in first
        assert "custom_name" in first
        assert "notes" in first
        assert "added_at" in first
        
        # Verify device info is complete
        device_info = first["device"]
        assert "vendor" in device_info
        assert "model" in device_info
        assert "device_type" in device_info
        assert "eos_date" in device_info
        assert "days_until_eos" in device_info
        assert "status" in device_info


# ==================== Can Add Device Tests ====================

class TestCanAddDevice:
    
    def test_can_add_device_free_at_limit(self, db_session, free_user, sample_devices):
        """Test free user at limit returns false"""
        # Add 3 devices (max for free tier)
        for i in range(3):
            add_tracked_device(
                user_id=free_user.id,
                device_id=sample_devices[i].id,
                custom_name=None,
                notes=None,
                db=db_session
            )
        
        result = can_add_device(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"] is False
    
    def test_can_add_device_free_below_limit(self, db_session, free_user, sample_devices):
        """Test free user below limit returns true"""
        # Add 2 devices (below limit of 3)
        for i in range(2):
            add_tracked_device(
                user_id=free_user.id,
                device_id=sample_devices[i].id,
                custom_name=None,
                notes=None,
                db=db_session
            )
        
        result = can_add_device(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"] is True
    
    def test_can_add_device_pro(self, db_session, pro_user, sample_devices):
        """Test pro user always returns true"""
        # Add all 4 devices
        for device in sample_devices:
            add_tracked_device(
                user_id=pro_user.id,
                device_id=device.id,
                custom_name=None,
                notes=None,
                db=db_session
            )
        
        # Even with 4 devices, pro user can still add more
        result = can_add_device(
            user_id=pro_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"] is True


# ==================== CSV Import Tests ====================

class TestCSVImport:
    
    def test_csv_import_valid_file(self, db_session, pro_user, sample_devices):
        """Test importing valid CSV file successfully"""
        csv_content = b"""vendor,model,custom_name,notes
Cisco,Catalyst 3850,Prod Switch,Main datacenter
Juniper,EX4200,Backup Switch,Secondary DC"""
        
        result = import_from_csv(
            user_id=pro_user.id,
            csv_file=csv_content,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"]["imported"] == 2
        assert result["data"]["skipped"] == 0
        
        # Verify devices were added
        tracked = db_session.query(TrackedDevice).filter(
            TrackedDevice.user_id == pro_user.id
        ).count()
        assert tracked == 2
    
    def test_csv_import_non_existent_devices(self, db_session, pro_user, sample_devices):
        """Test CSV import skips devices not in catalog"""
        csv_content = b"""vendor,model,custom_name,notes
Cisco,Catalyst 3850,Prod Switch,Main
Unknown,Model XYZ,,,
Juniper,EX4200,Backup,Secondary"""
        
        result = import_from_csv(
            user_id=pro_user.id,
            csv_file=csv_content,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"]["imported"] == 2
        assert result["data"]["skipped"] == 1
        assert any("not found in catalog" in err for err in result["data"]["errors"])
    
    def test_csv_import_duplicate_devices(self, db_session, pro_user, sample_devices):
        """Test CSV import skips devices already tracked"""
        # Add device first
        add_tracked_device(
            user_id=pro_user.id,
            device_id=sample_devices[0].id,
            custom_name=None,
            notes=None,
            db=db_session
        )
        
        # Try to import same device
        csv_content = b"""vendor,model,custom_name,notes
Cisco,Catalyst 3850,Prod Switch,Main"""
        
        result = import_from_csv(
            user_id=pro_user.id,
            csv_file=csv_content,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"]["imported"] == 0
        assert result["data"]["skipped"] == 1
        assert any("already tracked" in err for err in result["data"]["errors"])
    
    def test_csv_import_malformed_file(self, db_session, pro_user):
        """Test CSV import handles malformed files gracefully"""
        csv_content = b"""not,a,valid,csv,format
no vendor or model columns"""
        
        result = import_from_csv(
            user_id=pro_user.id,
            csv_file=csv_content,
            db=db_session
        )
        
        assert result["success"] is False
        assert "must contain columns" in result["error"]
    
    def test_csv_import_empty_file(self, db_session, pro_user):
        """Test CSV import handles empty file"""
        csv_content = b""
        
        result = import_from_csv(
            user_id=pro_user.id,
            csv_file=csv_content,
            db=db_session
        )
        
        assert result["success"] is False
        assert "empty" in result["error"].lower()
    
    def test_csv_import_free_tier_blocked(self, db_session, free_user, sample_devices):
        """Test free users cannot access CSV import feature"""
        csv_content = b"""vendor,model,custom_name,notes
Cisco,Catalyst 3850,Switch 1,Main"""
        
        result = import_from_csv(
            user_id=free_user.id,
            csv_file=csv_content,
            db=db_session
        )
        
        assert result["success"] is False
        assert "Pro feature" in result["error"]
        assert "CSV bulk import" in result["error"]
    
    def test_csv_import_pro_tier_allowed(self, db_session, pro_user, sample_devices):
        """Test Pro users can use CSV import"""
        csv_content = b"""vendor,model,custom_name,notes
Cisco,Catalyst 3850,Switch 1,Main
Juniper,EX4200,Switch 2,Secondary"""
        
        result = import_from_csv(
            user_id=pro_user.id,
            csv_file=csv_content,
            db=db_session
        )
        
        assert result["success"] is True
        assert result["data"]["imported"] == 2
        assert result["data"]["skipped"] == 0


# ==================== CSV Export Tests ====================

class TestCSVExport:
    
    def test_csv_export_free_tier_blocked(self, db_session, free_user, sample_devices):
        """Test free users cannot access CSV export feature"""
        result = export_to_csv(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is False
        assert "Pro feature" in result["error"]
        assert "CSV export" in result["error"]
    
    def test_csv_export_multiple_devices(self, db_session, pro_user, sample_devices):
        """Test Pro users can export multiple devices to valid CSV"""
        # Add 2 devices
        add_tracked_device(
            user_id=pro_user.id,
            device_id=sample_devices[0].id,
            custom_name="Prod Switch",
            notes="Main datacenter",
            db=db_session
        )
        add_tracked_device(
            user_id=pro_user.id,
            device_id=sample_devices[1].id,
            custom_name="Backup",
            notes="Secondary",
            db=db_session
        )
        
        result = export_to_csv(
            user_id=pro_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        assert isinstance(result["data"], bytes)
        
        # Decode and verify CSV content
        csv_text = result["data"].decode('utf-8')
        lines = csv_text.strip().split('\n')
        
        # Should have header + 2 data rows
        assert len(lines) == 3
        
        # Verify header
        assert "vendor" in lines[0]
        assert "model" in lines[0]
        assert "custom_name" in lines[0]
        
        # Verify data rows contain device info
        assert "Cisco" in csv_text
        assert "Catalyst 3850" in csv_text
        assert "Prod Switch" in csv_text
    
    def test_csv_export_empty(self, db_session, pro_user):
        """Test Pro user exporting empty list returns header only"""
        result = export_to_csv(
            user_id=pro_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        
        csv_text = result["data"].decode('utf-8')
        lines = csv_text.strip().split('\n')
        
        # Should have only header row
        assert len(lines) == 1
        assert "vendor,model" in lines[0]
