"""
Tests for Device Catalog Service

Comprehensive test suite for device search, retrieval, and utility functions.
Tests use SQLite in-memory database for isolation.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Device
from devices.service import (
    search_devices,
    get_device,
    get_device_by_slug,
    get_vendors,
    get_device_types
)
from devices.utils import (
    calculate_days_until_eos,
    get_device_status,
    generate_slug
)


# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Seed test data
    _seed_test_devices(session)
    
    yield session
    
    session.close()


def _seed_test_devices(session):
    """Seed database with test devices."""
    today = date.today()
    
    devices = [
        # Active devices (>365 days)
        Device(
            vendor="Cisco",
            model="Catalyst 3850",
            device_type="Switch",
            eos_date=today + timedelta(days=500),
            eol_date=today + timedelta(days=550),
            slug="cisco-catalyst-3850",
            description="Enterprise switch"
        ),
        Device(
            vendor="Cisco",
            model="ASR 1000",
            device_type="Router",
            eos_date=today + timedelta(days=400),
            eol_date=today + timedelta(days=450),
            slug="cisco-asr-1000",
            description="Aggregation router"
        ),
        # Approaching devices (90-365 days)
        Device(
            vendor="Palo Alto",
            model="PA-5220",
            device_type="Firewall",
            eos_date=today + timedelta(days=180),
            eol_date=today + timedelta(days=200),
            slug="palo-alto-pa-5220",
            description="Next-gen firewall"
        ),
        Device(
            vendor="F5",
            model="BIG-IP 2000s",
            device_type="Load Balancer",
            eos_date=today + timedelta(days=120),
            eol_date=None,
            slug="f5-big-ip-2000s",
            description="Application delivery controller"
        ),
        # End of support devices (<90 days or past)
        Device(
            vendor="Juniper",
            model="EX4300",
            device_type="Switch",
            eos_date=today + timedelta(days=30),
            eol_date=today + timedelta(days=60),
            slug="juniper-ex4300",
            description="Campus switch"
        ),
        Device(
            vendor="Arista",
            model="7050SX",
            device_type="Switch",
            eos_date=today - timedelta(days=100),
            eol_date=today - timedelta(days=50),
            slug="arista-7050sx",
            description="Datacenter switch - ALREADY EOS"
        ),
        # Additional vendors for filter testing
        Device(
            vendor="HP",
            model="ProCurve 2920",
            device_type="Switch",
            eos_date=today + timedelta(days=200),
            eol_date=None,
            slug="hp-procurve-2920",
            description="Edge switch"
        ),
        Device(
            vendor="Fortinet",
            model="FortiGate 100F",
            device_type="Firewall",
            eos_date=today + timedelta(days=300),
            eol_date=None,
            slug="fortinet-fortigate-100f",
            description="UTM firewall"
        ),
    ]
    
    for device in devices:
        session.add(device)
    
    session.commit()


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================

class TestDeviceUtils:
    """Test utility functions for EOS calculations and slug generation."""
    
    def test_calculate_days_until_eos_future(self):
        """Test calculating days until EOS for future date."""
        future_date = date.today() + timedelta(days=100)
        result = calculate_days_until_eos(future_date)
        assert result == 100
    
    def test_calculate_days_until_eos_past(self):
        """Test calculating days until EOS for past date (overdue)."""
        past_date = date.today() - timedelta(days=50)
        result = calculate_days_until_eos(past_date)
        assert result == -50
    
    def test_calculate_days_until_eos_today(self):
        """Test calculating days until EOS for today."""
        today = date.today()
        result = calculate_days_until_eos(today)
        assert result == 0
    
    def test_get_device_status_active(self):
        """Test status determination for active device (>365 days)."""
        future_date = date.today() + timedelta(days=400)
        status = get_device_status(future_date)
        assert status == "active"
    
    def test_get_device_status_approaching(self):
        """Test status determination for approaching device (90-365 days)."""
        future_date = date.today() + timedelta(days=180)
        status = get_device_status(future_date)
        assert status == "approaching"
    
    def test_get_device_status_approaching_boundary(self):
        """Test status at 90 days boundary (should be approaching)."""
        future_date = date.today() + timedelta(days=90)
        status = get_device_status(future_date)
        assert status == "approaching"
    
    def test_get_device_status_end_of_support(self):
        """Test status determination for end of support (<90 days)."""
        near_future = date.today() + timedelta(days=30)
        status = get_device_status(near_future)
        assert status == "end_of_support"
    
    def test_get_device_status_overdue(self):
        """Test status determination for past EOS date."""
        past_date = date.today() - timedelta(days=100)
        status = get_device_status(past_date)
        assert status == "end_of_support"
    
    def test_generate_slug_basic(self):
        """Test basic slug generation."""
        slug = generate_slug("Cisco", "Catalyst 3850")
        assert slug == "cisco-catalyst-3850"
    
    def test_generate_slug_with_hyphen(self):
        """Test slug generation with existing hyphens."""
        slug = generate_slug("Palo Alto", "PA-5220")
        assert slug == "palo-alto-pa-5220"
    
    def test_generate_slug_with_special_chars(self):
        """Test slug generation with special characters."""
        slug = generate_slug("F5", "BIG-IP 2000s")
        assert slug == "f5-big-ip-2000s"
    
    def test_generate_slug_with_parentheses(self):
        """Test slug generation with parentheses."""
        slug = generate_slug("Juniper", "EX4300 (48-Port)")
        assert slug == "juniper-ex4300-48-port"
    
    def test_generate_slug_with_slash(self):
        """Test slug generation with slashes."""
        slug = generate_slug("Cisco", "ASR9000/9006")
        assert slug == "cisco-asr9000-9006"
    
    def test_generate_slug_multiple_spaces(self):
        """Test slug generation with multiple spaces."""
        slug = generate_slug("Arista", "7050   SX-128")
        assert slug == "arista-7050-sx-128"


# ============================================================================
# SERVICE FUNCTION TESTS - SEARCH
# ============================================================================

class TestSearchDevices:
    """Test device search functionality with filters and pagination."""
    
    def test_search_devices_no_filters(self, db_session):
        """Test search without filters returns all devices."""
        result = search_devices("", None, None, 1, 20, db_session)
        
        assert result["success"] is True
        assert result["data"]["total"] == 8
        assert len(result["data"]["devices"]) == 8
        assert result["data"]["page"] == 1
        assert result["data"]["pages"] == 1
    
    def test_search_devices_with_vendor_filter(self, db_session):
        """Test search with vendor filter only."""
        result = search_devices("", "Cisco", None, 1, 20, db_session)
        
        assert result["success"] is True
        assert result["data"]["total"] == 2
        assert len(result["data"]["devices"]) == 2
        assert all(d["vendor"] == "Cisco" for d in result["data"]["devices"])
    
    def test_search_devices_with_type_filter(self, db_session):
        """Test search with device_type filter only."""
        result = search_devices("", None, "Switch", 1, 20, db_session)
        
        assert result["success"] is True
        assert result["data"]["total"] == 4
        assert len(result["data"]["devices"]) == 4
        assert all(d["device_type"] == "Switch" for d in result["data"]["devices"])
    
    def test_search_devices_with_both_filters(self, db_session):
        """Test search with both vendor and type filters."""
        result = search_devices("", "Cisco", "Switch", 1, 20, db_session)
        
        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["devices"][0]["vendor"] == "Cisco"
        assert result["data"]["devices"][0]["device_type"] == "Switch"
    
    def test_search_devices_with_query_string(self, db_session):
        """Test search with query string matching vendor."""
        result = search_devices("cisco", None, None, 1, 20, db_session)
        
        assert result["success"] is True
        assert result["data"]["total"] == 2
        assert all("cisco" in d["vendor"].lower() for d in result["data"]["devices"])
    
    def test_search_devices_query_matches_model(self, db_session):
        """Test search query matching model name."""
        result = search_devices("catalyst", None, None, 1, 20, db_session)
        
        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert "Catalyst" in result["data"]["devices"][0]["model"]
    
    def test_search_devices_case_insensitive(self, db_session):
        """Test search is case-insensitive."""
        result1 = search_devices("CISCO", None, None, 1, 20, db_session)
        result2 = search_devices("cisco", None, None, 1, 20, db_session)
        
        assert result1["success"] is True
        assert result2["success"] is True
        assert result1["data"]["total"] == result2["data"]["total"]
    
    def test_search_devices_pagination_page_1(self, db_session):
        """Test pagination - first page."""
        result = search_devices("", None, None, 1, 3, db_session)
        
        assert result["success"] is True
        assert result["data"]["page"] == 1
        assert result["data"]["pages"] == 3  # 8 devices / 3 per page = 3 pages
        assert len(result["data"]["devices"]) == 3
    
    def test_search_devices_pagination_page_2(self, db_session):
        """Test pagination - second page."""
        result = search_devices("", None, None, 2, 3, db_session)
        
        assert result["success"] is True
        assert result["data"]["page"] == 2
        assert len(result["data"]["devices"]) == 3
    
    def test_search_devices_pagination_last_page(self, db_session):
        """Test pagination - last page with partial results."""
        result = search_devices("", None, None, 3, 3, db_session)
        
        assert result["success"] is True
        assert result["data"]["page"] == 3
        assert len(result["data"]["devices"]) == 2  # Last page has 2 devices
    
    def test_search_devices_no_results(self, db_session):
        """Test search with no matching results."""
        result = search_devices("nonexistent", None, None, 1, 20, db_session)
        
        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert len(result["data"]["devices"]) == 0
    
    def test_search_devices_includes_calculated_fields(self, db_session):
        """Test that search results include calculated EOS fields."""
        result = search_devices("", None, None, 1, 1, db_session)
        
        assert result["success"] is True
        device = result["data"]["devices"][0]
        assert "days_until_eos" in device
        assert "status" in device
        assert device["status"] in ["active", "approaching", "end_of_support"]


# ============================================================================
# SERVICE FUNCTION TESTS - RETRIEVAL
# ============================================================================

class TestGetDevice:
    """Test device retrieval by ID and slug."""
    
    def test_get_device_by_id_found(self, db_session):
        """Test getting device by valid ID."""
        # First, get a device to know its ID
        devices = db_session.query(Device).first()
        device_id = devices.id
        
        result = get_device(device_id, db_session)
        
        assert result["success"] is True
        assert result["data"]["id"] == device_id
        assert "vendor" in result["data"]
        assert "model" in result["data"]
        assert "days_until_eos" in result["data"]
        assert "status" in result["data"]
    
    def test_get_device_by_id_not_found(self, db_session):
        """Test getting device with invalid ID."""
        result = get_device(9999, db_session)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_get_device_by_slug_found(self, db_session):
        """Test getting device by valid slug."""
        result = get_device_by_slug("cisco-catalyst-3850", db_session)
        
        assert result["success"] is True
        assert result["data"]["slug"] == "cisco-catalyst-3850"
        assert result["data"]["vendor"] == "Cisco"
        assert result["data"]["model"] == "Catalyst 3850"
    
    def test_get_device_by_slug_not_found(self, db_session):
        """Test getting device with invalid slug."""
        result = get_device_by_slug("invalid-slug-12345", db_session)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_get_device_includes_all_fields(self, db_session):
        """Test that retrieved device includes all required fields."""
        result = get_device_by_slug("palo-alto-pa-5220", db_session)
        
        assert result["success"] is True
        device = result["data"]
        
        # Check all required fields
        assert "id" in device
        assert "vendor" in device
        assert "model" in device
        assert "device_type" in device
        assert "eos_date" in device
        assert "eol_date" in device
        assert "slug" in device
        assert "description" in device
        assert "days_until_eos" in device
        assert "status" in device
        assert "created_at" in device
    
    def test_get_device_status_calculation(self, db_session):
        """Test that device status is calculated correctly."""
        # Get active device
        result = get_device_by_slug("cisco-catalyst-3850", db_session)
        assert result["success"] is True
        assert result["data"]["status"] == "active"
        assert result["data"]["days_until_eos"] > 365
        
        # Get approaching device
        result = get_device_by_slug("palo-alto-pa-5220", db_session)
        assert result["success"] is True
        assert result["data"]["status"] == "approaching"
        
        # Get end of support device
        result = get_device_by_slug("arista-7050sx", db_session)
        assert result["success"] is True
        assert result["data"]["status"] == "end_of_support"


# ============================================================================
# SERVICE FUNCTION TESTS - LISTS
# ============================================================================

class TestGetVendorsAndTypes:
    """Test vendor and device type listing functions."""
    
    def test_get_vendors_list(self, db_session):
        """Test getting distinct vendor list."""
        result = get_vendors(db_session)
        
        assert result["success"] is True
        vendors = result["data"]
        
        # Should have 7 unique vendors
        assert len(vendors) == 7
        assert "Cisco" in vendors
        assert "Palo Alto" in vendors
        assert "F5" in vendors
        assert "Juniper" in vendors
        assert "Arista" in vendors
        assert "HP" in vendors
        assert "Fortinet" in vendors
    
    def test_get_vendors_sorted(self, db_session):
        """Test that vendors are sorted alphabetically."""
        result = get_vendors(db_session)
        
        assert result["success"] is True
        vendors = result["data"]
        
        # Check if sorted
        assert vendors == sorted(vendors)
    
    def test_get_device_types_list(self, db_session):
        """Test getting distinct device type list."""
        result = get_device_types(db_session)
        
        assert result["success"] is True
        types = result["data"]
        
        # Should have 4 unique types
        assert len(types) == 4
        assert "Switch" in types
        assert "Router" in types
        assert "Firewall" in types
        assert "Load Balancer" in types
    
    def test_get_device_types_sorted(self, db_session):
        """Test that device types are sorted alphabetically."""
        result = get_device_types(db_session)
        
        assert result["success"] is True
        types = result["data"]
        
        # Check if sorted
        assert types == sorted(types)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_search_and_retrieve_workflow(self, db_session):
        """Test complete workflow: search -> get by slug."""
        # Search for Cisco devices
        search_result = search_devices("cisco", None, None, 1, 20, db_session)
        assert search_result["success"] is True
        
        # Get first device's slug
        first_device = search_result["data"]["devices"][0]
        slug = first_device["slug"]
        
        # Retrieve by slug
        device_result = get_device_by_slug(slug, db_session)
        assert device_result["success"] is True
        assert device_result["data"]["id"] == first_device["id"]
    
    def test_filter_by_vendor_from_list(self, db_session):
        """Test getting vendor list and filtering by one."""
        # Get all vendors
        vendors_result = get_vendors(db_session)
        assert vendors_result["success"] is True
        
        # Pick a vendor
        vendor = vendors_result["data"][0]
        
        # Search by that vendor
        search_result = search_devices("", vendor, None, 1, 20, db_session)
        assert search_result["success"] is True
        assert all(d["vendor"] == vendor for d in search_result["data"]["devices"])
    
    def test_empty_database_behavior(self):
        """Test functions with empty database."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Search should return empty results
        result = search_devices("", None, None, 1, 20, session)
        assert result["success"] is True
        assert result["data"]["total"] == 0
        
        # Get vendors should return empty list
        result = get_vendors(session)
        assert result["success"] is True
        assert result["data"] == []
        
        # Get types should return empty list
        result = get_device_types(session)
        assert result["success"] is True
        assert result["data"] == []
        
        session.close()
