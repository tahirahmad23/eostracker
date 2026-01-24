"""
API Routes
JSON API endpoints for device search, tracking, and reports
"""

from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

 
from database import User, get_db
from auth import get_current_user
from devices import search_devices, get_device
from tracking import (
    get_user_tracked_devices,
    add_tracked_device,
    remove_tracked_device,
    import_from_csv,
    export_to_csv
)
from reports import generate_pdf_report, generate_csv_export

router = APIRouter()


@router.get("/devices/search")
def api_search_devices(
    q: str = Query("", description="Search query"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Search devices API endpoint
    
    Returns JSON with devices and pagination info
    """
    result = search_devices(q, vendor, device_type, page, page_size, db)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"]
        }
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.get("/devices/{device_id}")
def api_get_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    """
    Get device details by ID
    
    Returns single device JSON
    """
    result = get_device(device_id, db)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"]
        }
    else:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": result["error"]}
        )


@router.get("/tracking")
def api_list_tracked_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's tracked devices
    
    Returns array of tracked devices with details
    """
    result = get_user_tracked_devices(current_user.id, db)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"]
        }
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.post("/tracking")
def api_add_tracked_device(
    device_id: int,
    custom_name: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add device to tracking
    
    Request body:
    {
        "device_id": 123,
        "custom_name": "My Device",  // optional
        "notes": "Production router"  // optional
    }
    
    Returns created TrackedDeviceInfo
    """
    result = add_tracked_device(current_user.id, device_id, custom_name, notes, db)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"]
        }
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.delete("/tracking/{tracked_device_id}")
def api_remove_tracked_device(
    tracked_device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove device from tracking
    
    Returns success status
    """
    result = remove_tracked_device(current_user.id, tracked_device_id, db)
    
    if result["success"]:
        return {
            "success": True,
            "data": {"message": "Device removed successfully"}
        }
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.post("/tracking/import")
async def api_import_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import devices from CSV file
    
    CSV format: vendor,model,custom_name,notes
    
    Returns import statistics and errors
    """
    # Read CSV file
    csv_content = await file.read()
    
    # Import devices
    result = import_from_csv(current_user.id, csv_content, db)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"]
        }
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.get("/tracking/export")
def api_export_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export tracked devices to CSV
    
    Returns CSV file for download
    """
    result = export_to_csv(current_user.id, db)
    
    if result["success"]:
        return Response(
            content=result["data"],
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=tracked_devices.csv"
            }
        )
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.post("/reports/generate")
def api_generate_report(
    include_charts: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate PDF report
    
    Request body:
    {
        "include_charts": true  // Pro tier only
    }
    
    Returns PDF file for download
    """
    # Override include_charts for free tier
    if current_user.tier == "free":
        include_charts = False
    
    result = generate_pdf_report(current_user.id, include_charts, db)
    
    if result["success"]:
        return Response(
            content=result["data"],
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=eos_report.pdf"
            }
        )
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.get("/reports/export-csv")
def api_export_report_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export report as CSV (alternative to PDF)
    
    Returns CSV file for download
    """
    result = generate_csv_export(current_user.id, db)
    
    if result["success"]:
        return Response(
            content=result["data"],
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=eos_report.csv"
            }
        )
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )
