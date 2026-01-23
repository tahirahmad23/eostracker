"""
Report Generator Service

Provides PDF and CSV report generation for tracked devices.
Implements tier-based features:
- Free tier: Basic PDF reports
- Pro tier: Enhanced PDF reports with charts and statistics
"""

import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Dict, Any

from sqlalchemy.orm import Session

from database.models import User
from database import UserTier
from tracking import get_user_tracked_devices
from .templates import generate_basic_pdf, generate_enhanced_pdf


# Type alias for Result pattern
Result = Dict[str, Any]


def generate_pdf_report(
    user_id: int,
    include_charts: bool,
    db: Session
) -> Result:
    """
    Generate PDF report for user's tracked devices.
    
    Free tier users receive basic table format.
    Pro tier users receive enhanced reports with charts and statistics.
    The include_charts parameter is automatically determined by user tier.
    
    Args:
        user_id: User ID to generate report for
        include_charts: Whether to include charts (Pro tier feature)
        db: Database session
    
    Returns:
        Result containing PDF bytes or error message
        
    Example:
        result = generate_pdf_report(user_id=1, include_charts=True, db=db)
        if result["success"]:
            pdf_bytes = result["data"]
            # Send to user or save to file
    """
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Get tracked devices
        devices_result = get_user_tracked_devices(user_id, db)
        if not devices_result["success"]:
            return devices_result
        
        tracked_devices_info = devices_result["data"]
        
        eos_date_info_map = dict()
        eos_dates = []
        for tracked_info in tracked_devices_info:
            eos_dates.append(tracked_info["device"]["eos_date"])
            eos_date_info_map[tracked_info["device"]["eos_date"]] = tracked_info
        eos_dates = sorted(eos_dates)

        # Prepare device data for PDF
        device_data = []
        for eos_date in eos_dates:
            tracked_info = eos_date_info_map[eos_date]
            # tracked_info is a dict with 'device' (DeviceInfo dict), 'custom_name', 'notes'

            device_info = tracked_info['device']
            
            device_data_item = {
                'vendor': device_info['vendor'],
                'model': device_info['model'],
                'device_type': device_info['device_type'],
                'eos_date': device_info['eos_date'],
                'days_until_eos': device_info['days_until_eos'],
                'status': device_info['status'],
                'custom_name': tracked_info['custom_name'],
                'notes': tracked_info['notes'],
            }
            device_data.append(device_data_item)
        
        # Sort by EOS date (soonest first)
        device_data.sort(key=lambda d: d['eos_date'])
        # Create PDF in memory
        buffer = BytesIO()
        
        # Determine report type based on user tier and include_charts flag
        # Pro tier gets enhanced if include_charts=True
        user_tier = user.tier
        if user_tier == UserTier.PRO and include_charts:
            generate_enhanced_pdf(
                user_name=user.full_name,
                tier=user_tier.value,
                devices=device_data,
                buffer=buffer
            )
        else:
            generate_basic_pdf(
                user_name=user.full_name,
                tier=user_tier.value,
                devices=device_data,
                buffer=buffer
            )
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return {
            "success": True,
            "data": pdf_bytes
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate PDF report: {str(e)}"
        }


def generate_csv_export(user_id: int, db: Session) -> Result:
    """
    Export user's tracked devices to CSV format.
    
    CSV includes: Vendor, Model, Type, EOS Date, Days Until EOS, Status,
    Custom Name, and Notes. Compatible with Excel and Google Sheets.
    
    Args:
        user_id: User ID to export devices for
        db: Database session
    
    Returns:
        Result containing CSV bytes or error message
        
    Example:
        result = generate_csv_export(user_id=1, db=db)
        if result["success"]:
            csv_bytes = result["data"]
            # Send to user for download
    """
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Get tracked devices
        devices_result = get_user_tracked_devices(user_id, db)
        if not devices_result["success"]:
            return devices_result
        
        tracked_devices_info = devices_result["data"]
        
        
        eos_date_info_map = dict()
        eos_dates = []
        for tracked_info in tracked_devices_info:
            eos_dates.append(tracked_info["device"]["eos_date"])
            eos_date_info_map[tracked_info["device"]["eos_date"]] = tracked_info
        eos_dates = sorted(eos_dates)
        

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Vendor',
            'Model',
            'Device Type',
            'EOS Date',
            'Days Until EOS',
            'Status',
            'Custom Name',
            'Notes',
            'Date Added'
        ])
        
        # Write device rows
        for eos_date in eos_dates:
            tracked_info = eos_date_info_map[eos_date]
        # for tracked_info in tracked_devices_info:
            # tracked_info is a dict with 'device' (DeviceInfo dict), 'custom_name', 'notes', 'added_at'
            device_info = tracked_info['device']
            
            # Get pre-calculated values from DeviceInfo
            days_until_eos = device_info['days_until_eos']
            status = device_info['status']
            
            # Format dates
            eos_date = device_info['eos_date']
            if hasattr(eos_date, 'strftime'):
                eos_date_str = eos_date.strftime('%Y-%m-%d')
            else:
                eos_date_str = str(eos_date)
            
            added_at = tracked_info['added_at']
            if hasattr(added_at, 'strftime'):
                added_date_str = added_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                added_date_str = str(added_at)
            
            # Format status for readability
            status_display = status.replace('_', ' ').title()
            
            writer.writerow([
                device_info['vendor'],
                device_info['model'],
                device_info['device_type'],
                eos_date_str,
                days_until_eos,
                status_display,
                tracked_info['custom_name'] or '',
                tracked_info['notes'] or '',
                added_date_str
            ])
        
        # Get CSV content as bytes (UTF-8 encoded)
        csv_content = output.getvalue()
        csv_bytes = csv_content.encode('utf-8')
        output.close()
        
        return {
            "success": True,
            "data": csv_bytes
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate CSV export: {str(e)}"
        }