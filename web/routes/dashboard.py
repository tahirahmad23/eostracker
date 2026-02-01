"""
Dashboard Routes
User dashboard and device tracking management
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from database import get_db,User
from auth import get_current_user_optional
from tracking import (
    get_user_tracked_devices,
    add_tracked_device,
    remove_tracked_device,
    can_add_device,
)
from devices import search_devices,get_device
from web.routes.auth import set_flash_message, get_flash_messages
from alerts.integration import trigger_immediate_alert_check
import logging
logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Enhanced user dashboard with comprehensive statistics and visualizations
    """

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Get tracked devices
    tracked_result = get_user_tracked_devices(current_user.id, db)
    tracked_devices = tracked_result["data"] if tracked_result["success"] else []
    
    # Calculate basic statistics
    total_devices = len(tracked_devices)
    safe_devices = len([d for d in tracked_devices if d["device"]["status"] == "safe"])
    warning_devices = len([d for d in tracked_devices if d["device"]["status"] == "warning"])
    approaching_devices = len([d for d in tracked_devices if d["device"]["status"] == "approaching"])
    not_supported_devices = len([d for d in tracked_devices if d["device"]["status"] == "not supported"])
    
    # Critical alerts (EOS or <30 days)
    critical_alerts = [
        d for d in tracked_devices 
        if d["device"]["days_until_eos"] < 30
    ]
    critical_alerts.sort(key=lambda x: x["device"]["days_until_eos"])
    
    # Upcoming alerts (30-90 days)
    upcoming_alerts = [
        d for d in tracked_devices 
        if 30 <= d["device"]["days_until_eos"] <= 90
    ]
    upcoming_alerts.sort(key=lambda x: x["device"]["days_until_eos"])
    
    # Device type breakdown
    device_types = defaultdict(int)
    device_types_status = defaultdict(lambda: {"safe": 0, "warning": 0, "critical": 0})
    
    for device in tracked_devices:
        device_type = device["device"]["device_type"]
        device_types[device_type] += 1
        
        # Categorize by severity
        if device["device"]["days_until_eos"] < 30:
            device_types_status[device_type]["critical"] += 1
        elif device["device"]["days_until_eos"] < 90:
            device_types_status[device_type]["warning"] += 1
        else:
            device_types_status[device_type]["safe"] += 1
    
    # Timeline data - devices reaching EOS by month (next 12 months)
    timeline_data = []
    current_date = datetime.now()
    
    for i in range(12):
        month_start = current_date + timedelta(days=i*30)
        month_end = current_date + timedelta(days=(i+1)*30)
        
        devices_in_month = len([
            d for d in tracked_devices
            if 0 <= d["device"]["days_until_eos"] <= (i+1)*30
            and d["device"]["days_until_eos"] > i*30
        ])
        
        timeline_data.append({
            "month": month_start.strftime("%b %y"),
            "count": devices_in_month,
            "month_num": i
        })
    
    # Health score (0-100)
    if total_devices > 0:
        health_score = int(
            (safe_devices * 100 + approaching_devices * 50 + warning_devices * 25) / total_devices
        )
    else:
        health_score = 100
    
    # Calculate trends (comparing to hypothetical previous month)
    # This is simplified - you could track historical data
    devices_at_risk = warning_devices + not_supported_devices
    risk_percentage = int((devices_at_risk / total_devices * 100)) if total_devices > 0 else 0
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request),
            # Basic stats
            "total_devices": total_devices,
            "safe_devices": safe_devices,
            "warning_devices": warning_devices,
            "approaching_devices": approaching_devices,
            "not_supported_devices": not_supported_devices,
            "health_score": health_score,
            "risk_percentage": risk_percentage,
            # Alerts
            "critical_alerts": critical_alerts[:5],  # Top 5 critical
            "upcoming_alerts": upcoming_alerts[:5],  # Top 5 upcoming
            # Analytics
            "device_types": dict(device_types),
            "device_types_status": dict(device_types_status),
            "timeline_data": timeline_data,
            # Recent activity
            "recent_devices": tracked_devices[:5]  # Most recent 5
        }
    )


@router.get("/tracking", response_class=HTMLResponse)
def tracking_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Tracked devices list with table view
    """

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    # Get tracked devices
    tracked_result = get_user_tracked_devices(current_user.id, db)
    tracked_devices = tracked_result["data"] if tracked_result["success"] else []
    
    # Check if user can add more devices
    can_add_result = can_add_device(current_user.id, db)
    can_add_more = can_add_result["data"] if can_add_result["success"] else False
    
    # Calculate tier limit message
    device_limit = 3 if current_user.tier == "free" else "unlimited"
    
    return templates.TemplateResponse(
        "tracking.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request),
            "tracked_devices": tracked_devices,
            "can_add_more": can_add_more,
            "device_limit": device_limit
        }
    )


@router.get("/tracking/add", response_class=HTMLResponse)
def add_device_page(
    request: Request,
    device_id: Optional[int] = None,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Add device to tracking page
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    # Check if user can add devices
    can_add_result = can_add_device(current_user.id, db)
    if not can_add_result["success"] or not can_add_result["data"]:
        set_flash_message(
            request,
            "You've reached your device limit. Upgrade to Pro for unlimited tracking.",
            "warning"
        )
        return RedirectResponse(url="/tracking", status_code=303)
    
    # Get all devices for selection (limit to first 100 for dropdown)
    devices_result = search_devices("", None, None, 1, 100, db)
    devices = devices_result["data"]["devices"] if devices_result["success"] else []
    # If a specific device_id is requested, ensure it is in the list
    if device_id:
        # Check if device is already in the loaded devices list
        if not any(d["id"] == device_id for d in devices):
            try:
                # Fetch the specific device and add it to the list
                device_result = get_device(device_id, db)
                if device_result["success"] and device_result["data"]:
                    devices.insert(0, device_result["data"])
            except Exception as e:
                # Fallback if get_device fails or doesn't exist
                logger.error(f"Could not fetch specific device {device_id}: {str(e)}")
            
    return templates.TemplateResponse(
        "add_device.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request),
            "devices": devices,
            "selected_device_id": device_id
        }
    )


@router.post("/tracking/add")
def add_device_to_tracking(
    request: Request,
    device_id: int = Form(...),
    custom_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Process add device form
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Add device to tracking
    result = add_tracked_device(current_user.id, device_id, custom_name, notes, db)
    
    if not result["success"]:
        
        set_flash_message(request, result["error"], "error")
    else:
        # Trigger debounced critical alert check for the newly added device
        trigger_immediate_alert_check(current_user.id, result["data"]["id"])
        set_flash_message(request, "Device added to tracking successfully", "success")
    
    return RedirectResponse(url="/tracking", status_code=303)


@router.post("/tracking/{tracked_device_id}/remove")
def remove_device_from_tracking(
    request: Request,
    tracked_device_id: int,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Remove device from tracking
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    # Remove device
    result = remove_tracked_device(current_user.id, tracked_device_id, db)
    
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
    else:
        set_flash_message(request, "Device removed from tracking", "success")
    
    return RedirectResponse(url="/tracking", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """
    User profile page
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request)
        }
    )