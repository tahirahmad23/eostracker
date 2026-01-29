"""
Slug generation utilities for device models.

Generates SEO-friendly, URL-safe slugs with collision handling.
"""

import re
from typing import Optional
from sqlalchemy.orm import Session


def generate_slug(vendor: str, model: str) -> str:
    """
    Generate SEO-friendly slug from vendor and model.
    
    Args:
        vendor: Device vendor name
        model: Device model name
    
    Returns:
        URL-safe slug
    
    Example:
        generate_slug("Cisco", "Catalyst 3850") -> "cisco-catalyst-3850"
        generate_slug("HPE Aruba", "6300M") -> "hpe-aruba-6300m"
    """
    combined = f"{vendor} {model}"
    
    # Convert to lowercase
    slug = combined.lower()
    
    # Replace spaces and slashes with hyphens
    slug = slug.replace(" ", "-")
    slug = slug.replace("/", "-")
    slug = slug.replace("\\", "-")
    
    # Remove parentheses and brackets
    slug = slug.replace("(", "")
    slug.replace(")", "")
    slug = slug.replace("[", "")
    slug = slug.replace("]", "")
    
    # Remove other special characters except hyphens and alphanumeric
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Replace multiple consecutive hyphens with single hyphen
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


def generate_unique_slug(
    vendor: str, 
    model: str, 
    db: Session,
    device_id: Optional[int] = None
) -> str:
    """
    Generate unique slug with collision handling.
    
    If slug already exists, appends -2, -3, etc. until unique slug is found.
    
    Args:
        vendor: Device vendor name
        model: Device model name
        db: Database session
        device_id: Optional device ID to exclude from uniqueness check (for updates)
    
    Returns:
        Unique URL-safe slug
    
    Example:
        First device: "cisco-catalyst-3850"
        Second device with same name: "cisco-catalyst-3850-2"
    """
    from database.models import Device
    
    base_slug = generate_slug(vendor, model)
    slug = base_slug
    counter = 2
    
    while True:
        # Check if slug exists
        query = db.query(Device).filter(Device.slug == slug)
        
        # Exclude current device if updating
        if device_id:
            query = query.filter(Device.id != device_id)
        
        existing = query.first()
        
        if not existing:
            # Slug is unique
            return slug
        
        # Slug exists, try with counter
        slug = f"{base_slug}-{counter}"
        counter += 1
        
        # Safety check to prevent infinite loop
        if counter > 1000:
            raise ValueError(
                f"Could not generate unique slug for {vendor} {model} "
                f"after 1000 attempts"
            )


def validate_slug(slug: str) -> bool:
    """
    Validate slug format.
    
    Args:
        slug: Slug to validate
    
    Returns:
        True if valid, False otherwise
    
    Valid slug rules:
    - Only lowercase letters, numbers, and hyphens
    - No consecutive hyphens
    - No leading or trailing hyphens
    - Between 1 and 255 characters
    """
    if not slug or len(slug) > 255:
        return False
    
    # Check for invalid characters
    if not re.match(r'^[a-z0-9\-]+$', slug):
        return False
    
    # Check for consecutive hyphens
    if '--' in slug:
        return False
    
    # Check for leading/trailing hyphens
    if slug.startswith('-') or slug.endswith('-'):
        return False
    
    return True
