"""
Device database update functionality.

Handles inserting and updating devices from JSON data with
comprehensive error handling and transaction management.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
import logging

from database.models import Device
from database.connection import SessionLocal
from database.validators import validate_devices_file, ValidationError
from database.utils.slug_generator import generate_unique_slug

logger = logging.getLogger(__name__)


class UpdateStats:
    """Track statistics for update operations."""
    
    def __init__(self):
        self.inserted = 0
        self.updated = 0
        self.skipped = 0
        self.failed = 0
        self.errors: List[str] = []
    
    def add_error(self, error: str):
        """Add error message to list."""
        self.errors.append(error)
        self.failed += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
            "total_processed": self.inserted + self.updated + self.skipped + self.failed,
            "errors": self.errors
        }
    
    def __str__(self) -> str:
        """String representation of stats."""
        return (
            f"Inserted: {self.inserted}, Updated: {self.updated}, "
            f"Skipped: {self.skipped}, Failed: {self.failed}"
        )


def find_existing_device(
    db: Session, 
    vendor: str, 
    model: str
) -> Optional[Device]:
    """
    Find existing device by vendor and model.
    
    Args:
        db: Database session
        vendor: Device vendor
        model: Device model
    
    Returns:
        Device object if found, None otherwise
    """
    return db.query(Device).filter(
        Device.vendor == vendor,
        Device.model == model
    ).first()


def device_needs_update(existing: Device, new_data: Dict[str, Any]) -> bool:
    """
    Check if device data has changed and needs update.
    
    Args:
        existing: Existing device from database
        new_data: New device data
    
    Returns:
        True if update is needed, False otherwise
    """
    # Check each field for changes
    fields_to_check = [
        ('device_type', 'device_type'),
        ('eos_date', 'eos_date'),
        ('eol_date', 'eol_date'),
        ('description', 'description')
    ]
    
    for db_field, data_field in fields_to_check:
        existing_value = getattr(existing, db_field)
        new_value = new_data.get(data_field)
        
        # Handle None values
        if existing_value is None and new_value is None:
            continue
        if existing_value != new_value:
            return True
    
    return False


def upsert_device(
    db: Session, 
    device_data: Dict[str, Any],
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Insert or update a single device.
    
    Args:
        db: Database session
        device_data: Validated device data
        dry_run: If True, only simulate the operation
    
    Returns:
        Dictionary with operation result
    """
    vendor = device_data["vendor"]
    model = device_data["model"]
    
    # Check if device exists
    existing = find_existing_device(db, vendor, model)
    
    if existing:
        # Device exists - check if update is needed
        if device_needs_update(existing, device_data):
            if not dry_run:
                # Update existing device
                existing.device_type = device_data["device_type"]
                existing.eos_date = device_data["eos_date"]
                existing.eol_date = device_data.get("eol_date")
                existing.description = device_data.get("description")
                
                # Update slug if vendor or model changed (shouldn't happen, but handle it)
                new_slug = device_data.get("slug") or generate_unique_slug(
                    vendor, model, db, existing.id
                )
                existing.slug = new_slug
                
                logger.info(f"Updated: {vendor} {model}")
            else:
                logger.info(f"[DRY RUN] Would update: {vendor} {model}")
            
            return {"action": "updated", "device": f"{vendor} {model}"}
        else:
            # No changes needed
            logger.debug(f"Skipped (no changes): {vendor} {model}")
            return {"action": "skipped", "device": f"{vendor} {model}", 
                    "reason": "no_changes"}
    else:
        # Device doesn't exist - insert new
        if not dry_run:
            # Generate unique slug
            slug = device_data.get("slug") or generate_unique_slug(vendor, model, db)
            
            # Create new device
            new_device = Device(
                vendor=vendor,
                model=model,
                device_type=device_data["device_type"],
                eos_date=device_data["eos_date"],
                eol_date=device_data.get("eol_date"),
                slug=slug,
                description=device_data.get("description")
            )
            
            db.add(new_device)
            logger.info(f"Inserted: {vendor} {model}")
        else:
            logger.info(f"[DRY RUN] Would insert: {vendor} {model}")
        
        return {"action": "inserted", "device": f"{vendor} {model}"}


def update_devices_from_json(
    json_file_path: str,
    dry_run: bool = False,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Update device database from JSON file.
    
    Args:
        json_file_path: Path to JSON file
        dry_run: If True, simulate without making changes
        db: Optional database session (creates new if not provided)
    
    Returns:
        Dictionary with update results and statistics
    """
    stats = UpdateStats()
    close_session = False
    
    try:
        # Validate JSON file
        logger.info(f"Validating JSON file: {json_file_path}")
        try:
            validation_result = validate_devices_file(json_file_path)
            devices_data = validation_result["data"]["devices"]
            logger.info(f"Validation successful: {len(devices_data)} devices to process")
        except ValidationError as e:
            logger.error(f"Validation failed: {str(e)}")
            return {
                "success": False,
                "error": f"Validation failed: {str(e)}",
                "stats": stats.to_dict()
            }
        
        # Create database session if not provided
        if db is None:
            db = SessionLocal()
            close_session = True
        
        # Process each device
        logger.info(f"Starting device update (dry_run={dry_run})...")
        
        for i, device_data in enumerate(devices_data):
            try:
                result = upsert_device(db, device_data, dry_run)
                
                if result["action"] == "inserted":
                    stats.inserted += 1
                elif result["action"] == "updated":
                    stats.updated += 1
                elif result["action"] == "skipped":
                    stats.skipped += 1
                
            except Exception as e:
                vendor = device_data.get("vendor", "unknown")
                model = device_data.get("model", "unknown")
                error_msg = f"Failed to process {vendor} {model}: {str(e)}"
                logger.error(error_msg)
                stats.add_error(error_msg)
        
        # Commit transaction if not dry run
        if not dry_run:
            try:
                db.commit()
                logger.info("Transaction committed successfully")
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"Failed to commit transaction: {str(e)}")
                return {
                    "success": False,
                    "error": f"Database commit failed: {str(e)}",
                    "stats": stats.to_dict()
                }
        else:
            db.rollback()
            logger.info("[DRY RUN] Transaction rolled back (no changes made)")
        
        # Close session if we created it
        if close_session:
            db.close()
        
        # Prepare result
        success = stats.failed == 0
        result = {
            "success": success,
            "dry_run": dry_run,
            "stats": stats.to_dict(),
            "summary": str(stats)
        }
        
        if not success:
            result["warning"] = f"{stats.failed} devices failed to process"
        
        logger.info(f"Update complete: {stats}")
        return result
    
    except Exception as e:
        logger.exception("Unexpected error during update")
        if db and close_session:
            db.rollback()
            db.close()
        
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "stats": stats.to_dict()
        }


def export_devices_to_json(
    output_file: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Export current devices to JSON file.
    
    Args:
        output_file: Path to output JSON file
        db: Optional database session
    
    Returns:
        Dictionary with export results
    """
    import json
    
    close_session = False
    
    try:
        # Create session if not provided
        if db is None:
            db = SessionLocal()
            close_session = True
        
        # Query all devices
        devices = db.query(Device).order_by(Device.vendor, Device.model).all()
        
        # Convert to JSON format
        devices_data = []
        for device in devices:
            devices_data.append({
                "vendor": device.vendor,
                "model": device.model,
                "device_type": device.device_type,
                "eos_date": device.eos_date.strftime("%Y-%m-%d"),
                "eol_date": device.eol_date.strftime("%Y-%m-%d") if device.eol_date else None,
                "slug": device.slug,
                "description": device.description
            })
        
        # Create output structure
        output_data = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "device_count": len(devices_data),
                "exported_by": "eos-tracker-export"
            },
            "devices": devices_data
        }
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(devices_data)} devices to {output_file}")
        
        if close_session:
            db.close()
        
        return {
            "success": True,
            "device_count": len(devices_data),
            "output_file": output_file
        }
    
    except Exception as e:
        logger.exception("Failed to export devices")
        if db and close_session:
            db.close()
        
        return {
            "success": False,
            "error": f"Export failed: {str(e)}"
        }
