"""
User Tracking Service
Manages user's tracked devices with tier-based limits and full device information.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from database.models import User, Device, TrackedDevice
from database import UserTier
from devices.service import get_device

# Type aliases for Result pattern
Result = Dict[str, Any]

# Constants
MAX_DEVICES_FREE = 3


def add_tracked_device(
    user_id: int,
    device_id: int,
    custom_name: Optional[str],
    notes: Optional[str],
    db: Session
) -> Result:
    """
    Add device to user's tracking list with tier limit enforcement.
    
    Args:
        user_id: ID of the user adding the device
        device_id: ID of the device to track
        custom_name: Optional custom name for the device (max 100 chars)
        notes: Optional notes about the device
        db: Database session
    
    Returns:
        Result containing TrackedDeviceInfo or error message
    
    Example:
        result = add_tracked_device(
            user_id=1,
            device_id=5,
            custom_name="Production Router",
            notes="Critical infrastructure",
            db=db
        )
        if result["success"]:
            tracked = result["data"]
            print(f"Added device: {tracked['device']['model']}")
    """
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Validate custom_name length if provided
        if custom_name and len(custom_name) > 100:
            return {
                "success": False,
                "error": "Custom name must be 100 characters or less"
            }
        
        # Check if device exists using device catalog service
        device_result = get_device(device_id, db)
        if not device_result["success"]:
            return {
                "success": False,
                "error": "Device not found in catalog"
            }
        
        # Check for duplicate tracking
        existing = db.query(TrackedDevice).filter(
            and_(
                TrackedDevice.user_id == user_id,
                TrackedDevice.device_id == device_id
            )
        ).first()
        
        if existing:
            return {
                "success": False,
                "error": "Device is already being tracked"
            }
        
        # Check tier limits for free users
        if user.tier == UserTier.FREE:
            tracked_count = db.query(TrackedDevice).filter(
                TrackedDevice.user_id == user_id
            ).count()
            
            if tracked_count >= MAX_DEVICES_FREE:
                return {
                    "success": False,
                    "error": f"Free tier limited to {MAX_DEVICES_FREE} devices. Upgrade to Pro for unlimited tracking."
                }
        
        # Create tracked device
        tracked_device = TrackedDevice(
            user_id=user_id,
            device_id=device_id,
            custom_name=custom_name,
            notes=notes
        )
        
        db.add(tracked_device)
        db.commit()
        db.refresh(tracked_device)
        
        # Load device relationship for response
        db.refresh(tracked_device)
        tracked_device_with_device = db.query(TrackedDevice).options(
            joinedload(TrackedDevice.device)
        ).filter(TrackedDevice.id == tracked_device.id).first()
        
        # Build TrackedDeviceInfo response
        tracked_info = _build_tracked_device_info(tracked_device_with_device)
        
        return {
            "success": True,
            "data": tracked_info
        }
    
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to add tracked device: {str(e)}"
        }


def remove_tracked_device(
    user_id: int,
    tracked_device_id: int,
    db: Session
) -> Result:
    """
    Remove device from user's tracking list.
    
    Args:
        user_id: ID of the user removing the device
        tracked_device_id: ID of the TrackedDevice record to remove
        db: Database session
    
    Returns:
        Result with success status or error message
    
    Example:
        result = remove_tracked_device(user_id=1, tracked_device_id=5, db=db)
        if result["success"]:
            print("Device removed successfully")
    """
    try:
        # Find tracked device
        tracked = db.query(TrackedDevice).filter(
            TrackedDevice.id == tracked_device_id
        ).first()
        
        if not tracked:
            return {
                "success": False,
                "error": "Tracked device not found"
            }
        
        # Verify ownership
        if tracked.user_id != user_id:
            return {
                "success": False,
                "error": "You can only remove devices you are tracking"
            }
        
        # Delete tracked device
        db.delete(tracked)
        db.commit()
        
        return {
            "success": True,
            "data": None
        }
    
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to remove tracked device: {str(e)}"
        }


def get_user_tracked_devices(
    user_id: int,
    db: Session
) -> Result:
    """
    Get all devices tracked by a user with full device information.
    
    Uses eager loading to prevent N+1 queries when accessing device details.
    
    Args:
        user_id: ID of the user
        db: Database session
    
    Returns:
        Result containing list of TrackedDeviceInfo objects
    
    Example:
        result = get_user_tracked_devices(user_id=1, db=db)
        if result["success"]:
            for tracked in result["data"]:
                print(f"{tracked['custom_name'] or tracked['device']['model']}")
                print(f"  Status: {tracked['device']['status']}")
    """
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Query with eager loading to prevent N+1 queries
        tracked_devices = db.query(TrackedDevice).options(
            joinedload(TrackedDevice.device)
        ).filter(
            TrackedDevice.user_id == user_id
        ).order_by(
            TrackedDevice.added_at.desc()
        ).all()
        
        # Build TrackedDeviceInfo list
        tracked_list = [
            _build_tracked_device_info(td) for td in tracked_devices
        ]
        
        return {
            "success": True,
            "data": tracked_list
        }
    
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to get tracked devices: {str(e)}"
        }


def can_add_device(
    user_id: int,
    db: Session
) -> Result:
    """
    Check if user can add more devices based on their tier.
    
    Args:
        user_id: ID of the user
        db: Database session
    
    Returns:
        Result containing boolean indicating if user can add devices
    
    Example:
        result = can_add_device(user_id=1, db=db)
        if result["success"]:
            if result["data"]:
                print("User can add more devices")
            else:
                print("User at device limit")
    """
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Pro users can always add devices
        if user.tier == UserTier.PRO:
            return {
                "success": True,
                "data": True
            }
        
        # Free users limited to MAX_DEVICES_FREE
        tracked_count = db.query(TrackedDevice).filter(
            TrackedDevice.user_id == user_id
        ).count()
        
        can_add = tracked_count < MAX_DEVICES_FREE
        
        return {
            "success": True,
            "data": can_add
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to check device limit: {str(e)}"
        }


def _build_tracked_device_info(tracked_device: TrackedDevice) -> Dict[str, Any]:
    """
    Build TrackedDeviceInfo response object from TrackedDevice model.
    
    Args:
        tracked_device: TrackedDevice ORM object with loaded device relationship
    
    Returns:
        Dictionary containing TrackedDeviceInfo structure
    """
    from devices.utils import calculate_days_until_eos, get_device_status
    
    device = tracked_device.device
    days_until_eos = calculate_days_until_eos(device.eos_date)
    status = get_device_status(device.eos_date)
    
    return {
        "id": tracked_device.id,
        "user_id": tracked_device.user_id,
        "device": {
            "id": device.id,
            "vendor": device.vendor,
            "model": device.model,
            "device_type": device.device_type,
            "eos_date": device.eos_date.isoformat(),
            "eol_date": device.eol_date.isoformat() if device.eol_date else None,
            "slug": device.slug,
            "description": device.description,
            "days_until_eos": days_until_eos,
            "status": status,
            "created_at": device.created_at.isoformat()
        },
        "custom_name": tracked_device.custom_name,
        "notes": tracked_device.notes,
        "added_at": tracked_device.added_at.isoformat()
    }
