"""
Database connection and session management.

Provides database session factory and dependency injection
for FastAPI routes. Handles connection pooling and cleanup.
"""

from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
import logging

from database.models import Base

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

# Create engine with connection pooling
# pool_size: max connections in pool
# max_overflow: additional connections beyond pool_size
# pool_pre_ping: verify connections before using
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL query logging during development
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    
    Creates a new database session for each request and ensures
    proper cleanup after the request completes.
    
    Yields:
        Session: SQLAlchemy database session
    
    Example:
        @app.get("/devices")
        def list_devices(db: Session = Depends(get_db)):
            devices = db.query(Device).all()
            return devices
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> Dict[str, Any]:
    """
    Initialize database tables.
    
    Creates all tables defined in SQLAlchemy models.
    Safe to call multiple times - only creates missing tables.
    
    Returns:
        Result dictionary with success status
    
    Example:
        result = init_db()
        if result["success"]:
            print("Database initialized successfully")
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
        return {
            "success": True,
            "data": "Database tables created successfully"
        }
    except Exception as e:
        logger.exception("Failed to initialize database tables")
        return {
            "success": False,
            "error": f"Failed to initialize database: {str(e)}"
        }


def drop_all_tables() -> Dict[str, Any]:
    """
    Drop all database tables.
    
    WARNING: This deletes all data! Only use for testing or reset.
    
    Returns:
        Result dictionary with success status
    """
    try:
        logger.warning("Dropping all database tables")
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped")
        return {
            "success": True,
            "data": "All tables dropped successfully"
        }
    except Exception as e:
        logger.exception("Failed to drop database tables")
        return {
            "success": False,
            "error": f"Failed to drop tables: {str(e)}"
        }


def check_connection() -> Dict[str, Any]:
    """
    Verify database connection is working.
    
    Returns:
        Result dictionary with success status and connection info
    
    Example:
        result = check_connection()
        if result["success"]:
            print("Database is reachable")
    """
    try:
        db = SessionLocal()
        # Try to execute a simple query
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection check succeeded")
        return {
            "success": True,
            "data": {
                "status": "connected",
                "url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "unknown"
            }
        }
    except Exception as e:
        logger.exception("Database connection check failed")
        return {
            "success": False,
            "error": f"Database connection failed: {str(e)}"
        }
