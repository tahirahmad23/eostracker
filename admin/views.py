"""
SQLAdmin ModelViews for EOS Tracker.

Defines admin interfaces for all database models with custom configurations,
including proper password hashing for user management.
"""

from sqladmin import ModelView
from wtforms import PasswordField
from database.models import User, Device, TrackedDevice, Subscription, AlertHistory
from auth.security import hash_password


class UserAdmin(ModelView, model=User):
    """Admin interface for User model with password hashing support."""
    
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    
    # List view configuration
    column_list = [
        User.id,
        User.email,
        User.full_name,
        User.tier,
        User.is_active,
        User.is_admin,
        User.created_at
    ]
    
    column_searchable_list = [User.email, User.full_name]
    column_sortable_list = [User.id, User.email, User.created_at]
    column_default_sort = [(User.created_at, True)]
    
    # Form configuration
    form_columns = [
        User.email,
        User.full_name,
        User.tier,
        User.is_active,
        User.is_admin,
    ]
    
    # Add password field separately (custom handling)
    form_extra_fields = {
        "password": PasswordField("Password")
    }
    
    # Labels for better readability
    column_labels = {
        User.id: "ID",
        User.email: "Email Address",
        User.full_name: "Full Name",
        User.tier: "Subscription Tier",
        User.is_active: "Active",
        User.is_admin: "Admin",
        User.created_at: "Created At",
        User.updated_at: "Updated At"
    }
    
    # Don't show password hash in list
    # column_exclude_list = [User.hashed_password]
    
    # Details view
    column_details_list = [
        User.id,
        User.email,
        User.full_name,
        User.tier,
        User.is_active,
        User.is_admin,
        User.created_at,
        User.updated_at
    ]
    
    # Formatting
    column_formatters = {
        User.tier: lambda m, a: m.tier.value if m.tier else "N/A",
        User.is_active: lambda m, a: "✓" if m.is_active else "✗",
        User.is_admin: lambda m, a: "✓" if m.is_admin else "✗",
    }
    
    # Export capability
    can_export = True
    
    async def on_model_change(self, data: dict, model: User, is_created: bool, request) -> None:
        """
        Hash password before saving to database.
        
        This hook is called when creating or updating a user via admin.
        If a password is provided, it gets hashed before storage.
        """
        if "password" in data and data["password"]:
            model.hashed_password = hash_password(data["password"])
        elif is_created and not model.hashed_password:
            # Require password for new users
            raise ValueError("Password is required when creating a new user")


class DeviceAdmin(ModelView, model=Device):
    """Admin interface for Device model."""
    
    name = "Device"
    name_plural = "Devices"
    icon = "fa-solid fa-server"
    
    # List view configuration
    column_list = [
        Device.id,
        Device.vendor,
        Device.model,
        Device.device_type,
        Device.eos_date,
        Device.eol_date,
        Device.created_at
    ]
    
    column_searchable_list = [Device.vendor, Device.model, Device.device_type, Device.slug]
    column_sortable_list = [Device.id, Device.vendor, Device.model, Device.eos_date]
    column_default_sort = [(Device.created_at, True)]
    
 
    # Labels
    column_labels = {
        Device.id: "ID",
        Device.vendor: "Vendor",
        Device.model: "Model",
        Device.device_type: "Type",
        Device.eos_date: "End of Support",
        Device.eol_date: "End of Life",
        Device.slug: "URL Slug",
        Device.description: "Description",
        Device.created_at: "Created At"
    }
    
    # Form configuration
    form_columns = [
        Device.vendor,
        Device.model,
        Device.device_type,
        Device.eos_date,
        Device.eol_date,
        Device.slug,
        Device.description
    ]
    
    # Details view
    column_details_list = [
        Device.id,
        Device.vendor,
        Device.model,
        Device.device_type,
        Device.eos_date,
        Device.eol_date,
        Device.slug,
        Device.description,
        Device.created_at
    ]
    
    # Export capability
    can_export = True


class TrackedDeviceAdmin(ModelView, model=TrackedDevice):
    """Admin interface for TrackedDevice model."""
    
    name = "Tracked Device"
    name_plural = "Tracked Devices"
    icon = "fa-solid fa-bookmark"
    
    # List view configuration
    column_list = [
        TrackedDevice.id,
        TrackedDevice.user_id,
        TrackedDevice.device_id,
        TrackedDevice.custom_name,
        TrackedDevice.added_at
    ]
    
    column_searchable_list = [TrackedDevice.custom_name]
    column_sortable_list = [TrackedDevice.id, TrackedDevice.added_at]
    column_default_sort = [(TrackedDevice.added_at, True)]
    
 
    
    # Labels
    column_labels = {
        TrackedDevice.id: "ID",
        TrackedDevice.user_id: "User",
        TrackedDevice.device_id: "Device",
        TrackedDevice.custom_name: "Custom Name",
        TrackedDevice.notes: "Notes",
        TrackedDevice.added_at: "Added At"
    }
    
    # Form configuration
    form_columns = [
        TrackedDevice.user_id,
        TrackedDevice.device_id,
        TrackedDevice.custom_name,
        TrackedDevice.notes
    ]
    
    # Export capability
    can_export = True


class SubscriptionAdmin(ModelView, model=Subscription):
    """Admin interface for Subscription model."""
    
    name = "Subscription"
    name_plural = "Subscriptions"
    icon = "fa-solid fa-credit-card"
    
    # List view configuration
    column_list = [
        Subscription.id,
        Subscription.user_id,
        Subscription.status,
        Subscription.current_period_start,
        Subscription.current_period_end,
        Subscription.cancel_at_period_end,
        Subscription.created_at
    ]
    
    column_sortable_list = [Subscription.id, Subscription.created_at, Subscription.current_period_end]
    column_default_sort = [(Subscription.created_at, True)]
    

    # Labels
    column_labels = {
        Subscription.id: "ID",
        Subscription.user_id: "User",
        Subscription.lemonsqueezy_subscription_id: "LemonSqueezy Sub ID",
        Subscription.lemonsqueezy_customer_id: "Customer ID",
        Subscription.lemonsqueezy_order_id: "Order ID",
        Subscription.lemonsqueezy_product_id: "Product ID",
        Subscription.lemonsqueezy_variant_id: "Variant ID",
        Subscription.status: "Status",
        Subscription.current_period_start: "Period Start",
        Subscription.current_period_end: "Period End",
        Subscription.cancel_at_period_end: "Cancel at End",
        Subscription.created_at: "Created At",
        Subscription.updated_at: "Updated At"
    }
    
    # Form configuration
    form_columns = [
        Subscription.user_id,
        Subscription.lemonsqueezy_subscription_id,
        Subscription.lemonsqueezy_customer_id,
        Subscription.lemonsqueezy_order_id,
        Subscription.lemonsqueezy_product_id,
        Subscription.lemonsqueezy_variant_id,
        Subscription.status,
        Subscription.current_period_start,
        Subscription.current_period_end,
        Subscription.cancel_at_period_end
    ]
    
    # Formatting
    column_formatters = {
        Subscription.cancel_at_period_end: lambda m, a: "✓" if m.cancel_at_period_end else "✗",
    }
    
    # Export capability
    can_export = True


class AlertHistoryAdmin(ModelView, model=AlertHistory):
    """Admin interface for AlertHistory model (read-only)."""
    
    name = "Alert History"
    name_plural = "Alert History"
    icon = "fa-solid fa-bell"
    
    # Make it read-only
    can_create = False
    can_edit = False
    can_delete = False
    
    # List view configuration
    column_list = [
        AlertHistory.id,
        AlertHistory.user_id,
        AlertHistory.tracked_device_id,
        AlertHistory.alert_type,
        AlertHistory.email_status,
        AlertHistory.sent_at
    ]
    
    column_sortable_list = [AlertHistory.id, AlertHistory.sent_at]
    column_default_sort = [(AlertHistory.sent_at, True)]
    
 
    
    # Labels
    column_labels = {
        AlertHistory.id: "ID",
        AlertHistory.user_id: "User",
        AlertHistory.tracked_device_id: "Tracked Device",
        AlertHistory.alert_type: "Alert Type",
        AlertHistory.email_status: "Email Status",
        AlertHistory.sent_at: "Sent At"
    }
    
    # Formatting
    column_formatters = {
        AlertHistory.alert_type: lambda m, a: m.alert_type.value if m.alert_type else "N/A",
        AlertHistory.email_status: lambda m, a: m.email_status.value if m.email_status else "N/A",
    }
    
    # Export capability
    can_export = True
