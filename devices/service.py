"""
Device Catalog Service

Provides search, retrieval, and listing functionality for the device catalog.
All functions return Result<T> type for consistent error handling.
"""

from typing import Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database.models import Device
from devices.utils import calculate_days_until_eos, get_device_status


# Type alias for Result pattern
Result = dict[str, Any]


def search_devices(
    query: str,
    vendor: str | None,
    device_type: str | None,
    page: int,
    page_size: int,
    db: Session
) -> Result:
    """
    Search devices with filters and pagination.
    
    Filters:
    - query: Searches both vendor and model fields (case-insensitive)
    - vendor: Filter by specific vendor (optional)
    - device_type: Filter by specific device type (optional)
    - Pagination with configurable page size
    
    Args:
        query: Search string for vendor/model
        vendor: Optional vendor filter
        device_type: Optional device type filter
        page: Page number (1-indexed)
        page_size: Number of items per page
        db: Database session
    
    Returns:
        Result containing:
        - devices: List of DeviceInfo dictionaries
        - total: Total number of matching devices
        - page: Current page number
        - pages: Total number of pages
    
    Example:
        result = search_devices("cisco", "Cisco", None, 1, 20, db)
        if result["success"]:
            devices = result["data"]["devices"]
            total = result["data"]["total"]
    """
    try:
        # Start with base query
        base_query = db.query(Device)
        
        # Apply search query filter (vendor or model)
        if query and query.strip():
            search_term = f"%{query.strip()}%"
            base_query = base_query.filter(
                or_(
                    Device.vendor.ilike(search_term),
                    Device.model.ilike(search_term)
                )
            )
        
        # Apply vendor filter
        if vendor:
            base_query = base_query.filter(Device.vendor == vendor)
        
        # Apply device type filter
        if device_type:
            base_query = base_query.filter(Device.device_type == device_type)
        
        # Get total count for pagination
        total = base_query.count()
        
        # Calculate total pages
        pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        # Ensure page is within valid range
        page = max(1, min(page, pages))
        
        # Apply pagination
        offset = (page - 1) * page_size
        devices = base_query.order_by(Device.vendor, Device.model).offset(offset).limit(page_size).all()
        
        # Convert to DeviceInfo format
        device_list = [_device_to_info(device) for device in devices]
        
        return {
            "success": True,
            "data": {
                "devices": device_list,
                "total": total,
                "page": page,
                "pages": pages
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}"
        }


def get_device(device_id: int, db: Session) -> Result:
    """
    Get device by ID with calculated EOS information.
    
    Args:
        device_id: Device primary key
        db: Database session
    
    Returns:
        Result containing DeviceInfo or error message
    
    Example:
        result = get_device(1, db)
        if result["success"]:
            device = result["data"]
            print(f"{device['vendor']} {device['model']}")
    """
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        
        if not device:
            return {
                "success": False,
                "error": f"Device with ID {device_id} not found"
            }
        
        return {
            "success": True,
            "data": _device_to_info(device)
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve device: {str(e)}"
        }


def get_device_by_slug(slug: str, db: Session) -> Result:
    """
    Get device by SEO-friendly slug.
    
    Args:
        slug: URL-safe device identifier (e.g., "cisco-catalyst-3850")
        db: Database session
    
    Returns:
        Result containing DeviceInfo or error message
    
    Example:
        result = get_device_by_slug("cisco-catalyst-3850", db)
        if result["success"]:
            device = result["data"]
    """
    try:
        device = db.query(Device).filter(Device.slug == slug).first()
        
        if not device:
            return {
                "success": False,
                "error": f"Device with slug '{slug}' not found"
            }
        
        return {
            "success": True,
            "data": _device_to_info(device)
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve device: {str(e)}"
        }


def get_vendors(db: Session) -> Result:
    """
    Get list of all unique vendors in the database.
    
    Args:
        db: Database session
    
    Returns:
        Result containing sorted list of vendor names
    
    Example:
        result = get_vendors(db)
        if result["success"]:
            vendors = result["data"]
            # ['Arista', 'Cisco', 'F5', ...]
    """
    try:
        vendors = db.query(Device.vendor).distinct().order_by(Device.vendor).all()
        vendor_list = [vendor[0] for vendor in vendors]
        
        return {
            "success": True,
            "data": vendor_list
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve vendors: {str(e)}"
        }


def get_device_types(db: Session) -> Result:
    """
    Get list of all unique device types in the database.
    
    Args:
        db: Database session
    
    Returns:
        Result containing sorted list of device type names
    
    Example:
        result = get_device_types(db)
        if result["success"]:
            types = result["data"]
            # ['Firewall', 'Router', 'Switch', 'Wireless']
    """
    try:
        types = db.query(Device.device_type).distinct().order_by(Device.device_type).all()
        type_list = [device_type[0] for device_type in types]
        
        return {
            "success": True,
            "data": type_list
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve device types: {str(e)}"
        }


def _device_to_info(device: Device) -> dict:
    """
    Convert Device model to DeviceInfo dictionary with calculated fields.
    
    Internal helper function that adds:
    - days_until_eos (calculated from eos_date)
    - status (active/approaching/end_of_support)
    
    Args:
        device: SQLAlchemy Device model instance
    
    Returns:
        DeviceInfo dictionary with all fields
    """
    days_until = calculate_days_until_eos(device.eos_date)
    status = get_device_status(device.eos_date)
    
    return {
        "id": device.id,
        "vendor": device.vendor,
        "model": device.model,
        "device_type": device.device_type,
        "eos_date": device.eos_date,
        "eol_date": device.eol_date,
        "slug": device.slug,
        "description": device.description,
        "days_until_eos": days_until,
        "status": status,
        "created_at": device.created_at
    }
