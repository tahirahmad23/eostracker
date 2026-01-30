"""
Device utility functions for EOS calculations and slug generation.

This module provides helper functions for calculating days until EOS,
determining device status, and generating SEO-friendly slugs.
"""

from datetime import date
import re


def calculate_days_until_eos(eos_date: date) -> int:
    """
    Calculate days until End-of-Support date.
    
    Args:
        eos_date: The end-of-support date
    
    Returns:
        Number of days until EOS (positive = future, negative = overdue)
    
    Example:
        >>> from datetime import date, timedelta
        >>> future_date = date.today() + timedelta(days=100)
        >>> calculate_days_until_eos(future_date)
        100
        >>> past_date = date.today() - timedelta(days=50)
        >>> calculate_days_until_eos(past_date)
        -50
    """
    today = date.today()
    delta = eos_date - today
    return delta.days


def get_device_status(eos_date: date) -> str:
    """
    Determine device status based on days until EOS.
    
    Status determination:
    - "active": More than 365 days until EOS
    - "approaching": Between 90-365 days until EOS
    - "end_of_support": Less than 90 days until EOS (including past dates)
    
    Args:
        eos_date: The end-of-support date
    
    Returns:
        Device status string: "active", "approaching", or "end_of_support"
    
    Example:
        >>> from datetime import date, timedelta
        >>> far_future = date.today() + timedelta(days=400)
        >>> get_device_status(far_future)
        'active'
        >>> near_future = date.today() + timedelta(days=180)
        >>> get_device_status(near_future)
        'approaching'
        >>> soon = date.today() + timedelta(days=30)
        >>> get_device_status(soon)
        'end_of_support'
    """
    days_until = calculate_days_until_eos(eos_date)
    
    if days_until > 365:
        return "active"
    elif days_until >= 90:
        return "approaching"
    else:
        return "Not Supported"


def generate_slug(vendor: str, model: str) -> str:
    """
    Generate SEO-friendly slug from vendor and model.
    
    Rules:
    - Combine vendor and model with hyphen
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove special characters (parentheses, slashes, etc.)
    - Multiple consecutive hyphens become single hyphen
    - Strip leading/trailing hyphens
    
    Args:
        vendor: Device vendor name
        model: Device model name
    
    Returns:
        SEO-friendly slug string
    
    Example:
        >>> generate_slug("Cisco", "Catalyst 3850")
        'cisco-catalyst-3850'
        >>> generate_slug("Palo Alto", "PA-5220")
        'palo-alto-pa-5220'
        >>> generate_slug("F5", "BIG-IP 2000s")
        'f5-big-ip-2000s'
        >>> generate_slug("Juniper", "EX4300 (48-Port)")
        'juniper-ex4300-48-port'
    """
    # Combine vendor and model
    combined = f"{vendor} {model}"
    
    # Convert to lowercase
    slug = combined.lower()
    
    # Replace special characters with spaces (except hyphens)
    slug = re.sub(r'[^\w\s-]', ' ', slug)
    
    # Replace whitespace and multiple spaces with single hyphen
    slug = re.sub(r'[\s_]+', '-', slug)
    
    # Replace multiple consecutive hyphens with single hyphen
    slug = re.sub(r'-+', '-', slug)
    
    # Strip leading and trailing hyphens
    slug = slug.strip('-')
    
    return slug
