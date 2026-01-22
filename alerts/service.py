"""
Alert Service - Module 6
Handles email alert checking, scheduling, and history tracking for devices approaching EOS.
"""

from typing import Dict, List, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import User, TrackedDevice, AlertHistory, Device
from database import AlertType, EmailStatus
from devices.utils import calculate_days_until_eos
from tracking import get_user_tracked_devices
from alerts.email import send_alert_email


# Type alias for Result pattern
Result = Dict[str, Any]


def check_and_send_alerts(db: Session) -> Result:
    """
    Check all users' tracked devices and send alerts for devices approaching EOS.
    Runs daily via scheduler at 9 AM UTC.
    
    Args:
        db: Database session
    
    Returns:
        Result dict with:
        - success: True if check completed (even if no alerts sent)
        - data: {"alerts_sent": int, "users_notified": int}
        - error: Error message if failed
    
    Example:
        result = check_and_send_alerts(db)
        if result["success"]:
            print(f"Sent {result['data']['alerts_sent']} alerts")
    """
    try:
        alerts_sent = 0
        users_notified = set()
        
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            # Check alerts for this user
            result = check_user_alerts(user.id, db)
            if result["success"] and result["data"] > 0:
                alerts_sent += result["data"]
                users_notified.add(user.id)
        
        return {
            "success": True,
            "data": {
                "alerts_sent": alerts_sent,
                "users_notified": len(users_notified)
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to check alerts: {str(e)}"
        }


def check_user_alerts(user_id: int, db: Session) -> Result:
    """
    Check alerts for a specific user's tracked devices.
    
    Args:
        user_id: User ID to check alerts for
        db: Database session
    
    Returns:
        Result dict with:
        - success: True if check completed
        - data: Number of alerts sent (int)
        - error: Error message if failed
    
    Example:
        result = check_user_alerts(123, db)
        if result["success"]:
            print(f"Sent {result['data']} alerts for user")
    """
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Get user's tracked devices with full device info
        tracked_result = get_user_tracked_devices(user_id, db)
        if not tracked_result["success"]:
            return tracked_result
        
        tracked_devices = tracked_result["data"]
        
        # Alert thresholds in days
        alert_thresholds = {
            AlertType.DAYS_365: 365,
            AlertType.DAYS_180: 180,
            AlertType.DAYS_90: 90,
            AlertType.DAYS_30: 30
        }
        
        # Group devices by alert type
        alerts_to_send: Dict[str, List[Dict]] = {
            AlertType.DAYS_365: [],
            AlertType.DAYS_180: [],
            AlertType.DAYS_90: [],
            AlertType.DAYS_30: []
        }
        
        for tracked in tracked_devices:
            device_info = tracked["device"]
            days_until_eos = calculate_days_until_eos(device_info["eos_date"])
            
            # Check each threshold
            for alert_type, threshold in alert_thresholds.items():
                # Check if we should send this alert
                # Alert if days_until_eos is within 1 day of threshold (to account for daily checks)
                if abs(days_until_eos - threshold) <= 1:
                    # Check if alert already sent
                    already_sent = db.query(AlertHistory).filter(
                        and_(
                            AlertHistory.user_id == user_id,
                            AlertHistory.tracked_device_id == tracked["id"],
                            AlertHistory.alert_type == alert_type
                        )
                    ).first()
                    
                    if not already_sent:
                        alerts_to_send[alert_type].append({
                            "tracked_device_id": tracked["id"],
                            "device_info": device_info,
                            "custom_name": tracked.get("custom_name"),
                            "days_until_eos": days_until_eos
                        })
        
        # Send alerts grouped by type
        total_alerts_sent = 0
        
        for alert_type, devices in alerts_to_send.items():
            if not devices:
                continue
            
            # Prepare device list for email
            device_list = []
            for d in devices:
                device_list.append({
                    "vendor": d["device_info"]["vendor"],
                    "model": d["device_info"]["model"],
                    "device_type": d["device_info"]["device_type"],
                    "eos_date": d["device_info"]["eos_date"],
                    "custom_name": d["custom_name"],
                    "days_until_eos": d["days_until_eos"]
                })
            
            # Send email
            email_result = send_alert_email(
                user_email=user.email,
                user_name=user.full_name,
                devices=device_list,
                alert_type=alert_type,
                db=db
            )
            
            # Record alert history for each device
            for d in devices:
                alert_history = AlertHistory(
                    user_id=user_id,
                    tracked_device_id=d["tracked_device_id"],
                    alert_type=alert_type,
                    email_status=EmailStatus.SENT if email_result["success"] else EmailStatus.FAILED,
                    sent_at=datetime.utcnow()
                )
                db.add(alert_history)
            
            if email_result["success"]:
                total_alerts_sent += len(devices)
        
        db.commit()
        
        return {
            "success": True,
            "data": total_alerts_sent
        }
    
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to check user alerts: {str(e)}"
        }


def get_alert_history(user_id: int, db: Session) -> Result:
    """
    Get alert history for a user.
    
    Args:
        user_id: User ID to get history for
        db: Database session
    
    Returns:
        Result dict with:
        - success: True if retrieved
        - data: List of alert history dicts
        - error: Error message if failed
    
    Example:
        result = get_alert_history(123, db)
        if result["success"]:
            for alert in result["data"]:
                print(f"Alert sent at {alert['sent_at']}")
    """
    try:
        # Get user to verify existence
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Get alert history with joined relationships
        history = db.query(AlertHistory).filter(
            AlertHistory.user_id == user_id
        ).order_by(AlertHistory.sent_at.desc()).all()
        
        # Format response
        history_list = []
        for alert in history:
            # Get device info
            tracked_device = db.query(TrackedDevice).filter(
                TrackedDevice.id == alert.tracked_device_id
            ).first()
            
            if tracked_device:
                device = db.query(Device).filter(
                    Device.id == tracked_device.device_id
                ).first()
                
                history_list.append({
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "sent_at": alert.sent_at,
                    "email_status": alert.email_status,
                    "device": {
                        "vendor": device.vendor if device else None,
                        "model": device.model if device else None,
                        "eos_date": device.eos_date if device else None
                    },
                    "custom_name": tracked_device.custom_name
                })
        
        return {
            "success": True,
            "data": history_list
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get alert history: {str(e)}"
        }
