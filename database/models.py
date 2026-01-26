"""
Database models for EOS Tracker platform.

Defines SQLAlchemy models for all database tables with proper
relationships, indexes, and constraints.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, 
    ForeignKey, Enum as SQLEnum, Text, Index
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class UserTier(str, enum.Enum):
    """User subscription tier enumeration."""
    FREE = "free"
    PRO = "pro"


class AlertType(str, enum.Enum):
    """Alert threshold type in days before EOS."""
    DAYS_365 = "365"
    DAYS_180 = "180"
    DAYS_90 = "90"
    DAYS_30 = "30"


class EmailStatus(str, enum.Enum):
    """Email delivery status."""
    SENT = "sent"
    FAILED = "failed"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status."""
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"


class User(Base):
    """
    User account model.
    
    Stores user authentication and subscription information.
    Free tier: max 3 tracked devices
    Pro tier: unlimited tracked devices
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    tier = Column(SQLEnum(UserTier), default=UserTier.FREE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tracked_devices = relationship("TrackedDevice", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    alert_history = relationship("AlertHistory", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tier='{self.tier}')>"


class Device(Base):
    """
    Network device catalog model.
    
    Stores information about network equipment with EOS/EOL dates.
    Public-facing data used for search and SEO pages.
    """
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor = Column(String(100), nullable=False, index=True)
    model = Column(String(255), nullable=False)
    device_type = Column(String(100), nullable=False, index=True)
    eos_date = Column(Date, nullable=False, index=True)
    eol_date = Column(Date, nullable=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tracked_by = relationship("TrackedDevice", back_populates="device", cascade="all, delete-orphan")
    
    # Composite index for search queries
    __table_args__ = (
        Index('idx_vendor_type', 'vendor', 'device_type'),
        Index('idx_vendor_model', 'vendor', 'model'),
    )
    
    def __repr__(self):
        return f"<Device(id={self.id}, vendor='{self.vendor}', model='{self.model}')>"


class TrackedDevice(Base):
    """
    User's tracked devices model.
    
    Junction table linking users to devices they're monitoring.
    Includes custom names and notes for personalization.
    """
    __tablename__ = "tracked_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    custom_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="tracked_devices")
    device = relationship("Device", back_populates="tracked_by")
    alerts = relationship("AlertHistory", back_populates="tracked_device", cascade="all, delete-orphan")
    
    # Composite index for user queries and unique constraint
    __table_args__ = (
        Index('idx_user_device', 'user_id', 'device_id', unique=True),
    )
    
    def __repr__(self):
        return f"<TrackedDevice(id={self.id}, user_id={self.user_id}, device_id={self.device_id})>"


class Subscription(Base):
    """
    User subscription model.
    
    Tracks Pro tier subscriptions managed through Paystack.
    One subscription per user.
    """
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lemonsqueezy_subscription_id = Column(String, unique=True, index=True)
    lemonsqueezy_customer_id = Column(String, nullable=True)
    lemonsqueezy_order_id = Column(String, nullable=True)
    lemonsqueezy_product_id = Column(String, nullable=True)
    lemonsqueezy_variant_id = Column(String, nullable=True)
    status = Column(String, default="active")
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    

    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class AlertHistory(Base):
    """
    Alert history model.
    
    Tracks sent email alerts to prevent duplicates.
    Each user-device-alert_type combination sent only once.
    """
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tracked_device_id = Column(Integer, ForeignKey("tracked_devices.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    email_status = Column(SQLEnum(EmailStatus), default=EmailStatus.SENT, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="alert_history")
    tracked_device = relationship("TrackedDevice", back_populates="alerts")
    
    # Composite index to prevent duplicate alerts
    __table_args__ = (
        Index('idx_alert_unique', 'user_id', 'tracked_device_id', 'alert_type', unique=True),
    )
    
    def __repr__(self):
        return f"<AlertHistory(id={self.id}, user_id={self.user_id}, alert_type='{self.alert_type}')>"
