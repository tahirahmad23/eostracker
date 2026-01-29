"""
Database module for EOS Tracker.

Provides database models, connection management, seeding utilities,
and production-safe device update system.
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
    SessionLocal,
    DATABASE_URL
)
from database.seed_data import seed_devices
from database.update_devices import (
    update_devices_from_json,
    export_devices_to_json
)
from database.validators import (
    validate_devices_file,
    ValidationError
)
from database.utils.slug_generator import (
    generate_slug,
    generate_unique_slug,
    validate_slug
)

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
    "DATABASE_URL",
    # Seed
    "seed_devices",
    # Update System
    "update_devices_from_json",
    "export_devices_to_json",
    "validate_devices_file",
    "ValidationError",
    # Utils
    "generate_slug",
    "generate_unique_slug",
    "validate_slug"
]
