"""
Public Routes
Homepage, device search, and individual device pages (SEO-optimized)
"""

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, User
from devices import search_devices, get_device_by_slug, get_vendors, get_device_types
from auth import get_current_user_optional


router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/", response_class=HTMLResponse)
def homepage(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Homepage with hero section and device search
    """
    # Get some featured devices or recent additions
    result = search_devices("", None, None, 1, 6, db)
    featured_devices = result["data"]["devices"] if result["success"] else []
    
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "current_user": current_user,
            "featured_devices": featured_devices
        }
    )


@router.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    q: str = Query("", description="Search query"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    page: int = Query(1, ge=1, description="Page number"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Device search results page with filters and pagination
    """
    # Get search results
    result = search_devices(q, vendor, device_type, page, 20, db)
    
    if not result["success"]:
        devices = []
        total = 0
        pages = 0
    else:
        devices = result["data"]["devices"]
        total = result["data"]["total"]
        pages = result["data"]["pages"]
    
    # Get filter options
    vendors_result = get_vendors(db)
    types_result = get_device_types(db)
    
    vendors = vendors_result["data"] if vendors_result["success"] else []
    device_types = types_result["data"] if types_result["success"] else []
    
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "current_user": current_user,
            "devices": devices,
            "total": total,
            "page": page,
            "pages": pages,
            "query": q,
            "selected_vendor": vendor,
            "selected_type": device_type,
            "vendors": vendors,
            "device_types": device_types
        }
    )


@router.get("/device/{slug}", response_class=HTMLResponse)
def device_page(
    request: Request,
    slug: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Individual device page (SEO-optimized with structured data)
    """
    # Get device by slug
    result = get_device_by_slug(slug, db)
    
    if not result["success"]:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )
    
    device = result["data"]
    
    # Get related devices (same vendor)
    related_result = search_devices("", device["vendor"], None, 1, 4, db)
    related_devices = related_result["data"]["devices"] if related_result["success"] else []
    
    # Filter out current device from related
    related_devices = [d for d in related_devices if d["id"] != device["id"]][:3]
    
    # Prepare structured data for SEO
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"{device['vendor']} {device['model']}",
        "description": device.get("description", f"{device['vendor']} {device['model']} - End of Support: {device['eos_date']}"),
        "brand": {
            "@type": "Brand",
            "name": device["vendor"]
        },
        "category": device["device_type"]
    }
    
    return templates.TemplateResponse(
        "device.html",
        {
            "request": request,
            "current_user": current_user,
            "device": device,
            "related_devices": related_devices,
            "structured_data": structured_data
        }
    )


@router.get("/about", response_class=HTMLResponse)
def about_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """About page"""
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "current_user": current_user}
    )

@router.get("/terms", response_class=HTMLResponse)
def terms_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """About page"""
    return templates.TemplateResponse(
        "terms.html",
        {"request": request, "current_user": current_user}
    )

@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """About page"""
    return templates.TemplateResponse(
        "privacy.html",
        {"request": request, "current_user": current_user}
    )

@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Pricing page"""
    return templates.TemplateResponse(
        "pricing.html",
        {"request": request, "current_user": current_user}
    )
