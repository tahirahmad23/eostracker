"""
Device Tracking Integration with Alert System

Helper function to trigger debounced critical alert checks when devices are added.
This should be called after successfully adding a tracked device.

Usage in your tracking service/routes:
    from alerts.integration import trigger_immediate_alert_check
    
    # After adding tracked device
    result = add_tracked_device(user_id, device_id, db)
    if result["success"]:
        # Trigger debounced critical alert check
        trigger_immediate_alert_check(user_id, result["data"]["id"])
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def trigger_immediate_alert_check(user_id: int, tracked_device_id: int) -> Optional[dict]:
    """
    Trigger a debounced critical alert check for newly added device.
    
    This uses a 10-minute debouncing mechanism:
    - When a device is added, a check is scheduled for 10 minutes later
    - If another device is added within 10 minutes, the timer resets
    - All devices added in the session are checked together
    - Only checks critical devices (EOS or <90 days) to avoid spam
    
    Args:
        user_id: User ID who just added a device
        tracked_device_id: ID of the newly added tracked device
    
    Returns:
        Status dict or None if scheduler disabled
    
    Example:
        # In your device tracking route/service
        result = add_tracked_device(user_id=123, device_id=456, db=db)
        if result["success"]:
            # Schedule debounced critical alert check
            trigger_immediate_alert_check(
                user_id=123, 
                tracked_device_id=result["data"]["id"]
            )
    """
    # Only run if scheduler is enabled
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "False").lower() == "true"

    if not scheduler_enabled:
        logger.debug("Alert check skipped (scheduler disabled)")
        return None
    
    try:
        from alerts.scheduler import trigger_immediate_critical_check
        
        # Schedule debounced critical check
        trigger_immediate_critical_check(user_id, tracked_device_id)
        
        return {
            "success": True, 
            "message": "Critical alert check scheduled with 10-minute debouncing"
        }
    
    except Exception as e:
        # Log error but don't fail the request
        logger.exception("Failed to schedule critical alert check")
        return None


def trigger_bulk_alert_check(user_id: int, tracked_device_ids: list) -> Optional[dict]:
    """
    Trigger debounced critical alert checks for multiple newly added devices.
    
    Useful for CSV imports or bulk device additions.
    Calls trigger_immediate_alert_check for each device, which will cause
    the debouncing timer to reset and all devices to be checked together.
    
    Args:
        user_id: User ID who added the devices
        tracked_device_ids: List of tracked device IDs
    
    Returns:
        Status dict or None if scheduler disabled
    
    Example:
        # After CSV import
        result = import_from_csv(user_id=123, csv_data, db)
        if result["success"] and result.get("tracked_device_ids"):
            trigger_bulk_alert_check(123, result["tracked_device_ids"])
    """
    if not tracked_device_ids:
        return None
    
    # Trigger check for each device - debouncing will collect them all
    for tracked_id in tracked_device_ids:
        trigger_immediate_alert_check(user_id, tracked_id)
    
    logger.info(
        f"Scheduled debounced critical checks for {len(tracked_device_ids)} devices "
        f"for user {user_id}"
    )
    
    return {
        "success": True,
        "message": f"Critical alert check scheduled for {len(tracked_device_ids)} devices"
    }

