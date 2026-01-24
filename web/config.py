"""
Application Settings Configuration
Loads and validates environment variables using Pydantic
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    
    # ========================================================================
    # JWT AUTHENTICATION
    # ========================================================================
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    jwt_refresh_expiration_days: int = 7
    
    # ========================================================================
    # SESSION
    # ========================================================================
    session_secret_key: str
    
    # ========================================================================
    # PAYSTACK
    # ========================================================================
    paystack_secret_key: str
    paystack_public_key: str
    paystack_pro_plan_code: Optional[str] = None
    paystack_pro_plan_amount: int = 4900  # In kobo (₦49.00)
    paystack_currency: str = "NGN"
    
    # ========================================================================
    # EMAIL (RESEND)
    # ========================================================================
    resend_api_key: str
    resend_from_email: str = "noreply@eostracker.com"
    resend_from_name: str = "EOS Tracker"
    email_enabled: bool = True
    email_send_welcome: bool = True
    email_send_alerts: bool = True
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    environment: str = "development"
    debug: bool = True
    app_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    
    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins into list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # ========================================================================
    # SCHEDULER
    # ========================================================================
    alert_check_interval_hours: int = 24
    alert_check_time: str = "09:00"
    scheduler_timezone: str = "UTC"
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    rate_limit_enabled: bool = True
    login_rate_limit: int = 5
    login_rate_period: int = 900  # 15 minutes
    api_rate_limit: int = 100
    api_rate_period: int = 3600  # 1 hour
    
    # ========================================================================
    # LOGGING
    # ========================================================================
    log_level: str = "INFO"
    log_file_path: Optional[str] = None
    log_format: str = "json"
    
    # ========================================================================
    # SECURITY
    # ========================================================================
    bcrypt_rounds: int = 12
    https_only: bool = False
    cookie_secure: bool = False
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    
    # ========================================================================
    # TIER LIMITS
    # ========================================================================
    free_tier_device_limit: int = 3
    pro_tier_device_limit: int = -1  # -1 = unlimited
    
    # ========================================================================
    # ALERT THRESHOLDS
    # ========================================================================
    alert_threshold_365: int = 365
    alert_threshold_180: int = 180
    alert_threshold_90: int = 90
    alert_threshold_30: int = 30
    
    # ========================================================================
    # FILE STORAGE
    # ========================================================================
    upload_dir: str = "/tmp/eos-tracker/uploads"
    max_upload_size: int = 10485760  # 10MB
    allowed_extensions: str = "csv,txt"
    
    @field_validator("allowed_extensions")
    @classmethod
    def parse_allowed_extensions(cls, v: str) -> List[str]:
        """Parse comma-separated extensions into list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v
    
    # ========================================================================
    # OPTIONAL SERVICES
    # ========================================================================
    sentry_dsn: Optional[str] = None
    ga_tracking_id: Optional[str] = None
    redis_url: Optional[str] = None
    
    # ========================================================================
    # DEVELOPMENT
    # ========================================================================
    reload: bool = False
    show_sql: bool = False
    auto_seed: bool = False
    
    # ========================================================================
    # TESTING
    # ========================================================================
    test_database_url: str = "sqlite:///./test_eos_tracker.db"
    test_skip_emails: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def get_database_url(self, test: bool = False) -> str:
        """Get database URL (test or regular)"""
        return self.test_database_url if test else self.database_url
    
    def get_alert_thresholds(self) -> List[int]:
        """Get all alert thresholds as sorted list"""
        return sorted([
            self.alert_threshold_365,
            self.alert_threshold_180,
            self.alert_threshold_90,
            self.alert_threshold_30
        ], reverse=True)


# Singleton settings instance
settings = Settings()


# Helper functions
def get_settings() -> Settings:
    """Get settings instance"""
    return settings


def is_production() -> bool:
    """Check if running in production"""
    return settings.is_production()


def is_development() -> bool:
    """Check if running in development"""
    return settings.is_development()
