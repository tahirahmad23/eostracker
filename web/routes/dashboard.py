"""
Dashboard Routes
User dashboard and device tracking management
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db,User
from auth import get_current_user
from tracking import (
    get_user_tracked_devices,
    add_tracked_device,
    remove_tracked_device,
    can_add_device
)
from devices import search_devices
from web.routes.auth import set_flash_message, get_flash_messages

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    User dashboard with statistics and quick actions
    """
    # Get tracked devices
    tracked_result = get_user_tracked_devices(current_user.id, db)
    tracked_devices = tracked_result["data"] if tracked_result["success"] else []
    
    # Calculate statistics
    total_devices = len(tracked_devices)
    active_devices = len([d for d in tracked_devices if d["device"]["status"] == "active"])
    approaching_devices = len([d for d in tracked_devices if d["device"]["status"] == "approaching"])
    eos_devices = len([d for d in tracked_devices if d["device"]["status"] == "end_of_support"])
    
    # Get upcoming alerts (devices with EOS in next 90 days)
    upcoming_alerts = [d for d in tracked_devices if 0 < d["device"]["days_until_eos"] <= 90]
    upcoming_alerts.sort(key=lambda x: x["device"]["days_until_eos"])
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request),
            "total_devices": total_devices,
            "active_devices": active_devices,
            "approaching_devices": approaching_devices,
            "eos_devices": eos_devices,
            "upcoming_alerts": upcoming_alerts[:5],  # Top 5
            "recent_devices": tracked_devices[:5]  # Most recent 5
        }
    )


@router.get("/tracking", response_class=HTMLResponse)
def tracking_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tracked devices list with table view
    """
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add device to tracking page
    """
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
    
    return templates.TemplateResponse(
        "add_device.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request),
            "devices": devices
        }
    )


@router.post("/tracking/add")
def add_device_to_tracking(
    request: Request,
    device_id: int = Form(...),
    custom_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process add device form
    """
    # Add device to tracking
    result = add_tracked_device(current_user.id, device_id, custom_name, notes, db)
    
    if not result["success"]:
        set_flash_message(request, result["error"], "error")
    else:
        set_flash_message(request, "Device added to tracking successfully", "success")
    
    return RedirectResponse(url="/tracking", status_code=303)


@router.post("/tracking/{tracked_device_id}/remove")
def remove_device_from_tracking(
    request: Request,
    tracked_device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove device from tracking
    """
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
    current_user: User = Depends(get_current_user)
):
    """
    User profile page
    """
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_messages": get_flash_messages(request)
        }
    )
