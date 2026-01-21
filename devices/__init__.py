"""
Device Catalog Module

Provides device search, retrieval, and EOS tracking functionality.
"""

from devices.service import (
    search_devices,
    get_device,
    get_device_by_slug,
    get_vendors,
    get_device_types
)

from devices.utils import (
    calculate_days_until_eos,
    get_device_status,
    generate_slug
)

__all__ = [
    # Service functions
    "search_devices",
    "get_device",
    "get_device_by_slug",
    "get_vendors",
    "get_device_types",
    
    # Utility functions
    "calculate_days_until_eos",
    "get_device_status",
    "generate_slug"
]
