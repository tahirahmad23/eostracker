"""
CSV Import/Export Handler for Tracked Devices
Handles bulk import of devices from CSV and export of tracked devices to CSV.
"""

import csv
import io
from io import BytesIO
import pandas as pd
from typing import Dict, List, Any
from sqlalchemy.orm import Session, joinedload
import logging

from database.models import Device, TrackedDevice
from tracking.service import add_tracked_device, get_user_tracked_devices

logger = logging.getLogger(__name__)

# Type alias for Result pattern
Result = Dict[str, Any]


def import_from_csv(
    user_id: int,
    csv_file: bytes,
    db: Session
) -> Result:
    """
    Import devices from CSV file and add them to user's tracking list.
    
    **Pro Feature Only**: CSV bulk import is only available for Pro tier users.
    Free tier users must add devices individually.
    
    CSV Format:
        vendor,model,custom_name,notes
        Cisco,Catalyst 3850,Production Switch,Located in DC1
        Juniper,EX4200,,Backup router
    
    Behavior:
        - Pro tier only feature
        - Skips devices not found in catalog
        - Skips devices already tracked by user
        - Returns summary of imported, skipped, and errors
    
    Args:
        user_id: ID of the user importing devices
        csv_file: CSV file content as bytes
        db: Database session
    
    Returns:
        Result containing import summary:
        {
            "imported": int,      # Number of devices successfully added
            "skipped": int,       # Number of devices skipped
            "errors": [str]       # List of error messages
        }
    
    Example:
        csv_content = b"vendor,model,custom_name,notes\\nCisco,Catalyst 3850,Prod,Main\\n"
        result = import_from_csv(user_id=1, csv_file=csv_content, db=db)
        if result["success"]:
            print(f"Imported: {result['data']['imported']}")
            print(f"Skipped: {result['data']['skipped']}")
    """
    try:
        # Check user exists and tier
        from database.models import User
        from database import UserTier
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("CSV import failed: user not found")
            return {
                "success": False,
                "error": "User not found"
            }
        
        # CSV import is Pro-only feature
        if user.tier != UserTier.PRO:
            logger.info("CSV import blocked: pro tier required")
            return {
                "success": False,
                "error": "CSV bulk import is a Pro feature. Upgrade to Pro to import devices from CSV."
            }
        
        # Continue with CSV import for Pro users
        # Decode bytes to string
        csv_text = csv_file.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        imported_device_ids = []
        imported_count = 0
        skipped_count = 0
        error_list = []
        
        # Validate CSV headers
        if csv_reader.fieldnames is None:
            logger.warning("CSV import failed: missing headers")
            return {
                "success": False,
                "error": "CSV file is empty or has no headers"
            }
        
        required_headers = {'vendor', 'model'}
        csv_headers = set(csv_reader.fieldnames)
        
        if not required_headers.issubset(csv_headers):
            logger.warning("CSV import failed: required headers missing")
            return {
                "success": False,
                "error": f"CSV must contain columns: {', '.join(required_headers)}"
            }
        
        # Process each row
        row_number = 1  # Start at 1 (header is row 0)
        for row in csv_reader:
            row_number += 1
            
            try:
                vendor = row.get('vendor', '').strip()
                model = row.get('model', '').strip()
                custom_name = row.get('custom_name', '').strip() or None
                notes = row.get('notes', '').strip() or None
                
                # Skip empty rows
                if not vendor or not model:
                    error_list.append(f"Row {row_number}: Missing vendor or model")
                    skipped_count += 1
                    continue
                
                # Find device in catalog
                device = db.query(Device).filter(
                    Device.vendor == vendor,
                    Device.model == model
                ).first()
                
                if not device:
                    error_list.append(
                        f"Row {row_number}: Device '{vendor} {model}' not found in catalog"
                    )
                    skipped_count += 1
                    continue
                
                # Check if already tracked
                existing = db.query(TrackedDevice).filter(
                    TrackedDevice.user_id == user_id,
                    TrackedDevice.device_id == device.id
                ).first()
                
                if existing:
                    error_list.append(
                        f"Row {row_number}: Device '{vendor} {model}' is already tracked"
                    )
                    skipped_count += 1
                    continue
                
                # Try to add device
                result = add_tracked_device(
                    user_id=user_id,
                    device_id=device.id,
                    custom_name=custom_name,
                    notes=notes,
                    db=db
                )
                
                if result["success"]:
                    imported_count += 1
                    imported_device_ids.append(result["data"]["id"])
                else:
                    # Handle tier limit or other errors
                    error_msg = result["error"]
                    error_list.append(f"Row {row_number}: {error_msg}")
                    
                    # If tier limit reached, stop processing
                    if "limited to" in error_msg.lower():
                        break
                    
                    skipped_count += 1
            
            except Exception as e:
                error_list.append(f"Row {row_number}: {str(e)}")
                skipped_count += 1
                continue
        
        return {
            "success": True,
            "data": f"imported: {imported_count}, skipped: {skipped_count}",
            "imported_device_ids": imported_device_ids
            }
    
    except UnicodeDecodeError:
        logger.exception("CSV import failed: invalid encoding")
        return {
            "success": False,
            "error": "Invalid file encoding. CSV must be UTF-8 encoded"
        }
    
    except csv.Error as e:
        logger.exception("CSV import failed: invalid CSV format")
        return {
            "success": False,
            "error": f"Invalid CSV format: {str(e)}"
        }
    
    except Exception as e:
        db.rollback()
        logger.exception("CSV import failed")
        return {
            "success": False,
            "error": f"Failed to import CSV: {str(e)}"
        }


def export_to_csv(
    user_id: int,
    db: Session
) -> Result:
    """
    Export user's tracked devices to CSV format.
    
    **Pro Feature Only**: CSV export is only available for Pro tier users.
    
    CSV Format (RFC 4180):
        vendor,model,device_type,eos_date,custom_name,notes,days_until_eos,status
        Cisco,Catalyst 3850,Switch,2025-12-31,Prod Switch,Main DC,345,active
    
    Args:
        user_id: ID of the user exporting devices
        db: Database session
    
    Returns:
        Result containing CSV file as bytes
    
    Example:
        result = export_to_csv(user_id=1, db=db)
        if result["success"]:
            csv_bytes = result["data"]
            with open("devices.csv", "wb") as f:
                f.write(csv_bytes)
    """
    try:
        # Check user exists and tier
        from database.models import User
        from database import UserTier
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("CSV export failed: user not found")
            return {
                "success": False,
                "error": "User not found"
            }
        
        # CSV export is Pro-only feature
        if user.tier != UserTier.PRO:
            logger.info("CSV export blocked: pro tier required")
            return {
                "success": False,
                "error": "CSV export is a Pro feature. Upgrade to Pro to export your devices to CSV."
            }
        
        # Continue with CSV export for Pro users
        # Get user's tracked devices
        tracked_result = get_user_tracked_devices(user_id, db)
        
        if not tracked_result["success"]:
            return tracked_result
        
        tracked_devices = tracked_result["data"]
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                'vendor',
                'model',
                'device_type',
                'eos_date',
                'custom_name',
                'notes',
                'days_until_eos',
                'status'
            ]
        )
        
        # Write header
        writer.writeheader()
        
        # Write rows
        for tracked in tracked_devices:
            device = tracked['device']
            writer.writerow({
                'vendor': device['vendor'],
                'model': device['model'],
                'device_type': device['device_type'],
                'eos_date': device['eos_date'],
                'custom_name': tracked['custom_name'] or '',
                'notes': tracked['notes'] or '',
                'days_until_eos': device['days_until_eos'],
                'status': device['status']
            })
        
        # Convert to bytes
        csv_bytes = output.getvalue().encode('utf-8')
        logger.info("CSV export generated", extra={"device_count": len(tracked_devices)})
        return {
            "success": True,
            "data": csv_bytes,
            "media_type":"text/csv",
            "name":"tracked_devices.csv"
        }
    
    except Exception as e:
        logger.exception("CSV export failed")
        return {
            "success": False,
            "error": f"Failed to export CSV: {str(e)}"
        }


def export_to_excel(
    user_id: int, 
    db: Session
) -> Result:
    """
    Export user's tracked devices to Excel (.xlsx) format.
    
    **Pro Feature Only**: Excel export is only available for Pro tier users.
    
    Excel Sheet Structure:
        Vendor | Model | Custom Name | Notes | Created At
    
    Args:
        user_id: ID of the user exporting devices
        db: Database session
    
    Returns:
        Result containing Excel file as bytes (BytesIO value)
    
    Example:
        result = export_to_excel(user_id=1, db=db)
        if result["success"]:
            excel_bytes = result["data"]
            with open("network_inventory.xlsx", "wb") as f:
                f.write(excel_bytes)
    """
    try:
        # 1. Check user exists and tier
        from database.models import User, Device
        from database import UserTier
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("Excel export failed: user not found")
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Excel export is Pro-only feature
        if user.tier != UserTier.PRO:
            logger.info("Excel export blocked: pro tier required")
            return {
                "success": False,
                "error": "Excel export is a Pro feature. Upgrade to Pro to export your devices."
            }

        # 2. Fetch Devices
        tracked_result = get_user_tracked_devices(user_id, db)
        
        if not tracked_result["success"]:
            return {
                "success": False,
                "error": "No devices found to export."
            }
        tracked_devices = tracked_result["data"]
        # 3. Process data for DataFrame
        data = [
            {
                'vendor': tracked["device"]['vendor'],
                'model': tracked["device"]['model'],
                'device_type': tracked["device"]['device_type'],
                'eos_date': tracked["device"]['eos_date'],
                'custom_name': tracked['custom_name'] or '',
                'notes': tracked['notes'] or '',
                'days_until_eos': tracked["device"]['days_until_eos'],
                'status': tracked["device"]['status']
            } 
            for tracked in tracked_devices
        ]
        # 4. Generate Excel in memory
        df = pd.DataFrame(data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Inventory')
        
        # Get the byte values
        excel_data = output.getvalue()
        logger.info("Excel export generated", extra={"device_count": len(tracked_devices)})
        return {
            "success": True,
            "data": excel_data,
            "media_type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "name":"tracked_devices.xlsx"
        }

    except Exception as e:
        logger.exception("Excel export failed")
        return {
            "success": False,
            "error": f"Failed to export Excel: {str(e)}"
        }