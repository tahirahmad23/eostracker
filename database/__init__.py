"""
Database module for EOS Tracker.

Provides database models, connection management, and seeding utilities.
"""

from database.models import (
    Base,
    User,
    Device,
    TrackedDevice,
    Subscription,
    AlertHistory,
    UserTier,
    AlertType,
    EmailStatus,
    SubscriptionStatus
)
from database.connection import (
    get_db,
    init_db,
    drop_all_tables,
    check_connection,
    engine,
    SessionLocal
)
from database.seed_data import seed_devices

__all__ = [
    # Models
    "Base",
    "User",
    "Device",
    "TrackedDevice",
    "Subscription",
    "AlertHistory",
    # Enums
    "UserTier",
    "AlertType",
    "EmailStatus",
    "SubscriptionStatus",
    # Connection
    "get_db",
    "init_db",
    "drop_all_tables",
    "check_connection",
    "engine",
    "SessionLocal",
    # Seed
    "seed_devices",
]
