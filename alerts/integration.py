"""
Device Tracking Integration with Alert System

Helper function to trigger immediate alert checks when devices are added.
This should be called after successfully adding a tracked device.

Usage in your tracking service/routes:
    from alerts.integration import trigger_immediate_alert_check
    
    # After adding tracked device
    result = add_tracked_device(user_id, device_id, db)
    if result["success"]:
        # Trigger immediate alert check
        trigger_immediate_alert_check(user_id)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def trigger_immediate_alert_check(user_id: int) -> Optional[dict]:
    """
    Trigger an immediate alert check for a user after they add a device.
    
    This runs asynchronously in the background so it doesn't block the request.
    Checks if the newly added device(s) trigger any alert thresholds and sends
    emails immediately if needed.
    
    Args:
        user_id: User ID who just added a device
    
    Returns:
        Alert check result dict or None if scheduler disabled
    
    Example:
        # In your device tracking route/service
        result = add_tracked_device(user_id=123, device_id=456, db=db)
        if result["success"]:
            # Check for immediate alerts
            trigger_immediate_alert_check(user_id=123)
    """
    import os
    
    # Only run if scheduler is enabled
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "False").lower() == "true"

    if not scheduler_enabled:
        logger.debug("Alert check skipped (scheduler disabled)")
        return None
    
    try:
        from alerts.scheduler import check_user_alerts_now
        
        # Run alert check in background
        result = check_user_alerts_now(user_id)
        
        if result["success"] and result["data"] > 0:
            logger.info(f"✓ Sent {result['data']} immediate alert(s)")
        
        return result
    
    except Exception as e:
        # Log error but don't fail the request
        logger.exception("Failed to check immediate alerts")
        return None



