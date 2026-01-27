"""
API Routes
JSON API endpoints for device search, tracking, and reports
"""
from io import BytesIO
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, Query,Request
from fastapi.responses import Response, JSONResponse,RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from alerts.integration import trigger_immediate_alert_check
 
from database import User, get_db
from auth import get_current_user_optional
from devices import search_devices, get_device
from tracking import (
    get_user_tracked_devices,
    add_tracked_device,
    remove_tracked_device,
    import_from_csv,
    export_to_csv,
    export_to_excel
)
from reports import generate_pdf_report, generate_csv_export
from pydantic import BaseModel
from web.routes.auth import set_flash_message, get_flash_messages

class TrackDeviceRequest(BaseModel):
    device_id: int
    custom_name: Optional[str] = None
    notes: Optional[str] = None


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
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    List user's tracked devices
    
    Returns array of tracked devices with details
    """

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
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
    payload: TrackDeviceRequest,
    current_user: User = Depends(get_current_user_optional),
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

    
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    result = add_tracked_device(
        current_user.id, 
        payload.device_id, 
        payload.custom_name, 
        payload.notes, 
        db
    )
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
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Remove device from tracking
    
    Returns success status
    """
    
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
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
    request : Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Import devices from CSV file
    
    CSV format: vendor,model,custom_name,notes
    
    Returns import statistics and errors
    """


    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    # Read CSV file
    content = await file.read()
    if file.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(BytesIO(content))
            # Convert the dataframe to a CSV string so your existing function works
            csv_content = df.to_csv(index=False).encode('utf-8')
        except Exception as e:
            set_flash_message(request, f"Invalid Excel file: {e}","error")
            return RedirectResponse(url="/tracking", status_code=303)
    else:
        # It's already a CSV
        csv_content = content
    # Import devices
    result = import_from_csv(current_user.id, csv_content, db)
    
    if result["success"]:
        trigger_immediate_alert_check(current_user.id)

        set_flash_message(request, result["data"])
        return RedirectResponse(url="/tracking", status_code=303)
    elif "Pro feature" in result["error"]:
        set_flash_message(request, result["error"],"error")
        # Redirect to pricing so they can upgrade
        return RedirectResponse(url="/subscription", status_code=303)
    elif "CSV must contain columns" in result["error"]:
        set_flash_message(request, result["error"], "error")
        # Redirect to pricing so they can upgrade
        return RedirectResponse(url="/tracking", status_code=303)
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.get("/tracking/export")
def api_export_csv(
    request : Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    format: str = "excel"  # or "csv"
):
    """
    Export tracked devices to CSV
    
    Returns CSV file for download
    """

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    if format == "excel":
        
        result = export_to_excel(current_user.id, db)
    else:        
        result = export_to_csv(current_user.id, db)
    name = result["name"]
    if result["success"]:
        return Response(
            content=result["data"],
            media_type=result["media_type"],
            headers={
                "Content-Disposition": f"attachment; filename={name}"
            }
        )
    elif "Pro feature" in result["error"]:
        set_flash_message(request, result["error"], "error")
        # Redirect to pricing so they can upgrade
        return RedirectResponse(url="/subscription", status_code=303)
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@router.post("/reports/generate")
def api_generate_report(
    include_charts: bool = False,
    current_user: User = Depends(get_current_user_optional),
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

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
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
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Export report as CSV (alternative to PDF)
    
    Returns CSV file for download
    """

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
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
