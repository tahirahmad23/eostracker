"""
JSON validation for device data updates.

Validates JSON structure and device data before database operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
import json
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_json_structure(data: Dict[str, Any]) -> None:
    """
    Validate top-level JSON structure.
    
    Args:
        data: Parsed JSON data
        
    Raises:
        ValidationError: If structure is invalid
    """
    required_fields = ["devices"]
    optional_fields = ["version", "updated_at", "metadata"]
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: '{field}'")
    
    # Validate devices is a list
    if not isinstance(data["devices"], list):
        raise ValidationError("'devices' must be a list")
    
    # Validate optional fields if present
    if "version" in data and not isinstance(data["version"], str):
        raise ValidationError("'version' must be a string")
    
    if "updated_at" in data and not isinstance(data["updated_at"], str):
        raise ValidationError("'updated_at' must be a string")
    
    logger.info(f"JSON structure valid: {len(data['devices'])} devices found")


def validate_date_format(date_str: str, field_name: str) -> date:
    """
    Validate and parse date string.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        field_name: Name of the field (for error messages)
        
    Returns:
        Parsed date object
        
    Raises:
        ValidationError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(
            f"Invalid date format for '{field_name}': '{date_str}'. "
            f"Expected format: YYYY-MM-DD"
        )


def validate_device(device: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Validate individual device data.
    
    Args:
        device: Device dictionary
        index: Device index in the list (for error messages)
        
    Returns:
        Validated device data with parsed dates
        
    Raises:
        ValidationError: If device data is invalid
    """
    required_fields = ["vendor", "model", "device_type", "eos_date"]
    optional_fields = ["eol_date", "description", "slug"]
    
    # Check required fields
    for field in required_fields:
        if field not in device:
            raise ValidationError(
                f"Device at index {index}: Missing required field '{field}'"
            )
        if not device[field]:
            raise ValidationError(
                f"Device at index {index}: Field '{field}' cannot be empty"
            )
    
    # Validate field types
    string_fields = ["vendor", "model", "device_type"]
    for field in string_fields:
        if not isinstance(device[field], str):
            raise ValidationError(
                f"Device at index {index}: '{field}' must be a string"
            )
    
    # Validate vendor length
    if len(device["vendor"]) > 100:
        raise ValidationError(
            f"Device at index {index}: 'vendor' exceeds 100 characters"
        )
    
    # Validate model length
    if len(device["model"]) > 255:
        raise ValidationError(
            f"Device at index {index}: 'model' exceeds 255 characters"
        )
    
    # Validate device_type length
    if len(device["device_type"]) > 100:
        raise ValidationError(
            f"Device at index {index}: 'device_type' exceeds 100 characters"
        )
    
    # Validate description length if present
    if "description" in device and device["description"]:
        if not isinstance(device["description"], str):
            raise ValidationError(
                f"Device at index {index}: 'description' must be a string"
            )
    
    # Parse and validate dates
    validated_device = device.copy()
    
    # Validate eos_date
    validated_device["eos_date"] = validate_date_format(
        device["eos_date"], 
        f"eos_date (device at index {index})"
    )
    
    # Validate eol_date if present
    if "eol_date" in device and device["eol_date"]:
        validated_device["eol_date"] = validate_date_format(
            device["eol_date"], 
            f"eol_date (device at index {index})"
        )
        
        # Ensure eol_date is after eos_date
        if validated_device["eol_date"] < validated_device["eos_date"]:
            raise ValidationError(
                f"Device at index {index}: 'eol_date' must be after 'eos_date'"
            )
    else:
        validated_device["eol_date"] = None
    
    return validated_device


def validate_devices_file(file_path: str) -> Dict[str, Any]:
    """
    Validate complete devices JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary with validation results and parsed data
        
    Raises:
        ValidationError: If validation fails
    """
    # Read and parse JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValidationError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Failed to read file: {str(e)}")
    
    # Validate structure
    validate_json_structure(data)
    
    # Validate each device
    validated_devices = []
    errors = []
    
    for i, device in enumerate(data["devices"]):
        try:
            validated_device = validate_device(device, i)
            validated_devices.append(validated_device)
        except ValidationError as e:
            errors.append(str(e))
    
    # If there are validation errors, raise combined error
    if errors:
        error_msg = "Validation failed with the following errors:\n" + "\n".join(errors)
        raise ValidationError(error_msg)
    
    logger.info(f"Successfully validated {len(validated_devices)} devices")
    
    return {
        "success": True,
        "data": {
            "version": data.get("version", "unknown"),
            "updated_at": data.get("updated_at"),
            "metadata": data.get("metadata", {}),
            "devices": validated_devices,
            "device_count": len(validated_devices)
        }
    }


def quick_validate(file_path: str) -> bool:
    """
    Quick validation check (returns boolean).
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validate_devices_file(file_path)
        return True
    except ValidationError:
        return False
