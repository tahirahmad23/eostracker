"""
Admin module for EOS Tracker.

Provides a Django-like admin interface using SQLAdmin with
secure authentication for admin users only.
"""

from admin.views import (
    UserAdmin,
    DeviceAdmin,
    TrackedDeviceAdmin,
    SubscriptionAdmin,
    AlertHistoryAdmin
)

from admin.auth import AdminAuth, authentication_backend

__all__ = [
    "UserAdmin",
    "DeviceAdmin",
    "TrackedDeviceAdmin",
    "SubscriptionAdmin",
    "AlertHistoryAdmin",
    "AdminAuth",
    "authentication_backend"
]
