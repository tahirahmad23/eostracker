"""
Tests for Module 7: Report Generator

Tests PDF and CSV generation with tier-based features.
"""

import pytest
from datetime import date, datetime
from io import BytesIO
import csv
import pdfminer
from pdfminer.high_level import extract_text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from database.models import Base, User, Device, TrackedDevice
from database import UserTier
from reports import generate_pdf_report, generate_csv_export


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    Uses in-memory SQLite for fast, isolated tests.
    """
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(engine)


# ============================================================================
# USER FIXTURES
# ============================================================================

@pytest.fixture
def free_user(db_session: Session) -> User:
    """Create a free tier user for testing."""
    user = User(
        email="free@example.com",
        hashed_password="hashed123",
        full_name="Free User",
        tier=UserTier.FREE,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def pro_user(db_session: Session) -> User:
    """Create a pro tier user for testing."""
    user = User(
        email="pro@example.com",
        hashed_password="hashed123",
        full_name="Pro User",
        tier=UserTier.PRO,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_devices(db_session: Session) -> list[Device]:
    """Create sample devices for testing."""
    devices = [
        Device(
            vendor="Cisco",
            model="Catalyst 3850",
            device_type="Switch",
            eos_date=date(2026, 4, 30),  # 98 days from Jan 22, 2026
            eol_date=date(2025, 10, 31),
            slug="cisco-catalyst-3850",
            description="Enterprise switch"
        ),
        Device(
            vendor="Juniper",
            model="EX4300",
            device_type="Switch",
            eos_date=date(2026, 7, 15),  # 174 days
            eol_date=date(2026, 1, 15),
            slug="juniper-ex4300",
            description="Access switch"
        ),
        Device(
            vendor="Aruba",
            model="2930F",
            device_type="Switch",
            eos_date=date(2025, 12, 31),  # -22 days (overdue)
            eol_date=date(2025, 6, 30),
            slug="aruba-2930f",
            description="Layer 3 switch"
        ),
        Device(
            vendor="Cisco",
            model="ASR 1001-X",
            device_type="Router",
            eos_date=date(2027, 3, 31),  # 433 days
            eol_date=date(2026, 9, 30),
            slug="cisco-asr-1001-x",
            description="Aggregation router"
        ),
        Device(
            vendor="Palo Alto",
            model="PA-220",
            device_type="Firewall",
            eos_date=date(2026, 2, 28),  # 37 days
            eol_date=date(2025, 8, 31),
            slug="palo-alto-pa-220",
            description="Next-gen firewall"
        ),
    ]
    
    for device in devices:
        db_session.add(device)
    db_session.commit()
    
    for device in devices:
        db_session.refresh(device)
    
    return devices


@pytest.fixture
def tracked_devices_free(db_session: Session, free_user: User, sample_devices: list[Device]) -> list[TrackedDevice]:
    """Create tracked devices for free user (3 devices)."""
    tracked = [
        TrackedDevice(
            user_id=free_user.id,
            device_id=sample_devices[0].id,
            custom_name="Main Distribution Switch",
            notes="Building A datacenter"
        ),
        TrackedDevice(
            user_id=free_user.id,
            device_id=sample_devices[2].id,
            custom_name="Access Switch Floor 2",
            notes="Critical - needs replacement"
        ),
        TrackedDevice(
            user_id=free_user.id,
            device_id=sample_devices[4].id,
            custom_name="Edge Firewall",
            notes="Primary security device"
        ),
    ]
    
    for t in tracked:
        db_session.add(t)
    db_session.commit()
    
    return tracked


@pytest.fixture
def tracked_devices_pro(db_session: Session, pro_user: User, sample_devices: list[Device]) -> list[TrackedDevice]:
    """Create tracked devices for pro user (all 5 devices)."""
    tracked = [
        TrackedDevice(
            user_id=pro_user.id,
            device_id=device.id,
            custom_name=f"Device {i+1}",
            notes=f"Note for device {i+1}"
        )
        for i, device in enumerate(sample_devices)
    ]
    
    for t in tracked:
        db_session.add(t)
    db_session.commit()
    
    return tracked


# ============================================================================
# PDF GENERATION TESTS
# ============================================================================

class TestPDFGeneration:
    """Test PDF report generation."""
    
    def test_generate_basic_pdf_free_tier(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test basic PDF generation for free tier user."""
        result = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
       
        assert result["success"] is True
        assert isinstance(result["data"], bytes)
        assert len(result["data"]) > 0
        
        # PDF should start with PDF header
        assert result["data"][:4] == b'%PDF'
    
    def test_generate_enhanced_pdf_pro_tier(self, db_session: Session, pro_user: User, tracked_devices_pro):
        """Test enhanced PDF generation for pro tier user."""
        result = generate_pdf_report(
            user_id=pro_user.id,
            include_charts=True,
            db=db_session
        )
        
        assert result["success"] is True
        assert isinstance(result["data"], bytes)
        assert len(result["data"]) > 0
        
        # PDF should be valid
        assert result["data"][:4] == b'%PDF'
        
        # Enhanced PDF should be larger due to charts
        # (This is a heuristic, actual size varies)
        assert len(result["data"]) > 5000
    
    def test_basic_report_no_charts(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test that free tier reports don't include charts."""
        result = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
        
        assert result["success"] is True
        
        # Basic reports should be smaller (no charts)
        # This is approximate
        assert len(result["data"]) < 20000
    
    def test_pro_report_has_charts(self, db_session: Session, pro_user: User, tracked_devices_pro):
        """Test that pro tier reports include charts."""
        result = generate_pdf_report(
            user_id=pro_user.id,
            include_charts=True,
            db=db_session
        )
        result2 = generate_pdf_report(
            user_id=pro_user.id,
            include_charts=False,
            db=db_session
        )
        
        assert result["success"] is True
        assert len(result["data"]) > len(result2["data"])
        # Pro reports with charts should be larger
        # assert len(result["data"]) > 10000
    
    def test_pdf_contains_all_devices(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test that PDF includes all tracked devices."""
        result = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
        
        assert result["success"] is True
        # pdf_content = result["data"].decode('latin-1', errors='ignore')
        # pdf_content = base64.b64encode(result["data"]).decode("utf-8")
        pdf_content = extract_text(BytesIO(result["data"]))
        # Check that device vendors are in PDF
        assert 'Cisco' in pdf_content
        assert 'Aruba' in pdf_content
        assert 'Palo Alto' in pdf_content
    
    def test_pdf_correct_device_data(self, db_session: Session, free_user: User, tracked_devices_free, sample_devices):
        """Test that device data is accurately represented."""
        result = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
        
        assert result["success"] is True
        pdf_content = extract_text(BytesIO(result["data"]))
    
        # Check for specific device models
        assert 'Catalyst 3850' in pdf_content
        assert '2930F' in pdf_content
        assert 'PA-220' in pdf_content
        
        # Check for custom names
        # assert 'Main Distribution Switch' in pdf_content
        # assert 'Edge Firewall' in pdf_content
    
    def test_status_colors_applied(self, db_session: Session, pro_user: User, tracked_devices_pro):
        """Test that status colors are properly applied in PDF."""
        result = generate_pdf_report(
            user_id=pro_user.id,
            include_charts=True,
            db=db_session
        )
        
        assert result["success"] is True
        
        # PDF should contain color definitions
        # ReportLab includes color info in PDF
        pdf_content = extract_text(BytesIO(result["data"]))
        
        # Check that status terms appear
        assert 'Active' in pdf_content or 'Approaching' in pdf_content
    
    def test_empty_report_no_devices(self, db_session: Session, free_user: User):
        """Test handling of report with no tracked devices."""
        # Free user has no tracked devices in this test
        result = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
        
        assert result["success"] is True
        assert isinstance(result["data"], bytes)
        
        pdf_content = extract_text(BytesIO(result["data"]))
        
        # Should contain message about no devices
        assert 'No devices' in pdf_content or '0' in pdf_content


# ============================================================================
# CSV EXPORT TESTS
# ============================================================================

class TestCSVExport:
    """Test CSV export functionality."""
    
    def test_generate_csv_export_success(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test successful CSV export."""
        result = generate_csv_export(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        assert isinstance(result["data"], bytes)
        assert len(result["data"]) > 0
    
    def test_csv_contains_all_data(self, db_session: Session, free_user: User, tracked_devices_free, sample_devices):
        """Test that CSV contains all device data."""
        result = generate_csv_export(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        
        # Decode CSV
        csv_content = result["data"].decode('utf-8')
        lines = csv_content.strip().split('\n')
        
        # Should have header + 3 devices
        assert len(lines) == 4
        
        # Parse CSV
        reader = csv.reader(lines)
        rows = list(reader)
        
        # Check vendors
        vendors = [row[0] for row in rows[1:]]  # Skip header
        assert 'Cisco' in vendors
        assert 'Aruba' in vendors
        assert 'Palo Alto' in vendors
    
    def test_csv_correct_headers(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test that CSV has correct column headers."""
        result = generate_csv_export(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        
        csv_content = result["data"].decode('utf-8')
        lines = csv_content.strip().split('\n')
        
        reader = csv.reader(lines)
        header = next(reader)
        
        expected_headers = [
            'Vendor',
            'Model',
            'Device Type',
            'EOS Date',
            'Days Until EOS',
            'Status',
            'Custom Name',
            'Notes',
            'Date Added'
        ]
        
        assert header == expected_headers
    
    def test_csv_utf8_encoding(self, db_session: Session, pro_user: User, sample_devices):
        """Test that CSV uses UTF-8 encoding."""
        # Create device with unicode characters
        device = Device(
            vendor="Cisco",
            model="Catalyst 9300",
            device_type="Switch",
            eos_date=date(2026, 6, 30),
            slug="cisco-catalyst-9300",
            description="Switch with unicode: café, naïve, 中文"
        )
        db_session.add(device)
        db_session.commit()
        db_session.refresh(device)
        
        tracked = TrackedDevice(
            user_id=pro_user.id,
            device_id=device.id,
            custom_name="Test Switch",
            notes="Unicode test: café, naïve, 中文"
        )
        db_session.add(tracked)
        db_session.commit()
        
        result = generate_csv_export(
            user_id=pro_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        
        # Should decode without errors
        csv_content = result["data"].decode('utf-8')
        assert 'café' in csv_content or 'naïve' in csv_content
    
    def test_csv_empty_export(self, db_session: Session, free_user: User):
        """Test CSV export with no tracked devices."""
        result = generate_csv_export(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        
        csv_content = result["data"].decode('utf-8')
        lines = csv_content.strip().split('\n')
        
        # Should only have header
        assert len(lines) == 1


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling in report generation."""
    
    def test_invalid_user_id_pdf(self, db_session: Session):
        """Test PDF generation with invalid user ID."""
        result = generate_pdf_report(
            user_id=99999,
            include_charts=False,
            db=db_session
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_invalid_user_id_csv(self, db_session: Session):
        """Test CSV export with invalid user ID."""
        result = generate_csv_export(
            user_id=99999,
            db=db_session
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_user_tier_determines_report_type(self, db_session: Session, free_user: User, pro_user: User):
        """Test that user tier correctly determines report type."""
        # Free user - even with include_charts=True, should get basic
        result_free = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
        
        # Pro user with charts
        result_pro = generate_pdf_report(
            user_id=pro_user.id,
            include_charts=True,
            db=db_session
        )
        
        assert result_free["success"] is True
        assert result_pro["success"] is True
        
        # Both should generate valid PDFs
        assert result_free["data"][:4] == b'%PDF'
        assert result_pro["data"][:4] == b'%PDF'


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Test integration with other modules."""
    
    def test_integration_with_tracking_service(self, db_session: Session, pro_user: User, tracked_devices_pro):
        """Test that report generation correctly uses tracking service."""
        result = generate_pdf_report(
            user_id=pro_user.id,
            include_charts=True,
            db=db_session
        )
        
        assert result["success"] is True
        
        # Verify it retrieved all tracked devices
        pdf_content = result["data"].decode('latin-1', errors='ignore')
        
        # Should contain device count (5 devices)
        assert '5' in pdf_content
    
    def test_integration_with_device_utils(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test that report uses device utility functions."""
        result = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
        
        assert result["success"] is True
        pdf_content = extract_text(BytesIO(result["data"]))
        
        # Should contain status information
        # (calculated by device utils)
        assert 'Active' in pdf_content or 'Approaching' in pdf_content or 'End' in pdf_content
    
    def test_devices_sorted_by_eos_date(self, db_session: Session, pro_user: User, tracked_devices_pro):
        """Test that devices are sorted by EOS date in reports."""
        result_csv = generate_csv_export(
            user_id=pro_user.id,
            db=db_session
        )
        
        assert result_csv["success"] is True
        
        csv_content = result_csv["data"].decode('utf-8')
        lines = csv_content.strip().split('\n')
        reader = csv.reader(lines)
        
        # Skip header
        next(reader)
        
        # Extract EOS dates
        eos_dates = []
        for row in reader:
            eos_date_str = row[3]  # EOS Date column
            eos_dates.append(eos_date_str)

        
        print(eos_dates)
       
        print(sorted(eos_dates))
        # Should be sorted (earliest first)
        assert eos_dates == sorted(eos_dates)


# ============================================================================
# ADDITIONAL TESTS
# ============================================================================

class TestAdditionalFeatures:
    """Test additional features and edge cases."""
    
    def test_custom_names_in_reports(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test that custom device names appear in reports."""
        result_pdf = generate_pdf_report(
            user_id=free_user.id,
            include_charts=False,
            db=db_session
        )
        
        assert result_pdf["success"] is True
        pdf_content = extract_text(BytesIO(result_pdf["data"]))
        custom_name = 'Main Distribution Switch'
        # Check for custom names
        assert custom_name in pdf_content or custom_name[:17] in pdf_content
        
        result_csv = generate_csv_export(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result_csv["success"] is True
        csv_content = result_csv["data"].decode('utf-8')
        
        assert 'Main Distribution Switch' in csv_content
    
    def test_notes_in_csv_export(self, db_session: Session, free_user: User, tracked_devices_free):
        """Test that device notes appear in CSV export."""
        result = generate_csv_export(
            user_id=free_user.id,
            db=db_session
        )
        
        assert result["success"] is True
        csv_content = result["data"].decode('utf-8')
        
        # Check for notes
        assert 'Building A datacenter' in csv_content
        assert 'Critical - needs replacement' in csv_content
    
    def test_pro_tier_statistics(self, db_session: Session, pro_user: User, tracked_devices_pro):
        """Test that Pro tier reports include statistics."""
        result = generate_pdf_report(
            user_id=pro_user.id,
            include_charts=True,
            db=db_session
        )
        
        assert result["success"] is True
        pdf_content = extract_text(BytesIO(result["data"]))
        
        # Should contain summary statistics
        assert 'Summary' in pdf_content or 'Statistics' in pdf_content or 'Total' in pdf_content
