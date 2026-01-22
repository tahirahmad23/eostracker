"""
Scheduler Configuration - Module 6
Configures APScheduler to run daily alert checks at 9 AM UTC.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy.orm import Session

from database.connection import get_db, SessionLocal
from alerts.service import check_and_send_alerts


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Scheduler instance (singleton)
_scheduler = None


def get_scheduler():
    """
    Get or create the scheduler instance.
    
    Returns:
        Configured APScheduler instance
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = create_scheduler()
    
    return _scheduler


def create_scheduler() -> BackgroundScheduler:
    """
    Create and configure APScheduler with PostgreSQL job store.
    
    Returns:
        Configured BackgroundScheduler instance
    
    Example:
        scheduler = create_scheduler()
        scheduler.start()
    """
    # Get database URL from environment
    import os
    database_url = os.getenv("DATABASE_URL", "postgresql://eosalert:eosalert@db:5432/eosalert")
    
    # Configure job stores
    jobstores = {
        'default': SQLAlchemyJobStore(url=database_url)
    }
    
    # Configure executors
    executors = {
        'default': ThreadPoolExecutor(max_workers=5)
    }
    
    # Job defaults
    job_defaults = {
        'coalesce': True,  # Combine multiple missed runs into one
        'max_instances': 1,  # Only one instance of job at a time
        'misfire_grace_time': 3600  # Allow 1 hour grace period for missed jobs
    }
    
    # Create scheduler
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )
    
    logger.info("APScheduler created with PostgreSQL job store")
    
    return scheduler


def add_alert_job(scheduler: BackgroundScheduler) -> None:
    """
    Add daily alert check job to scheduler.
    Runs at 9:00 AM UTC every day.
    
    Args:
        scheduler: APScheduler instance
    
    Example:
        scheduler = create_scheduler()
        add_alert_job(scheduler)
        scheduler.start()
    """
    # Define job function
    def run_alert_check():
        """Wrapper function to run alert checks with database session."""
        logger.info("Starting daily alert check...")
        
        db = SessionLocal()
        try:
            result = check_and_send_alerts(db)
            
            if result["success"]:
                data = result["data"]
                logger.info(
                    f"Alert check completed: {data['alerts_sent']} alerts sent "
                    f"to {data['users_notified']} users"
                )
            else:
                logger.error(f"Alert check failed: {result['error']}")
        
        except Exception as e:
            logger.error(f"Exception during alert check: {str(e)}", exc_info=True)
        
        finally:
            db.close()
    
    # Add job with cron trigger (9 AM UTC daily)
    trigger = CronTrigger(hour=9, minute=0, timezone='UTC')
    
    scheduler.add_job(
        func=run_alert_check,
        trigger=trigger,
        id='daily_alert_check',
        name='Daily EOS Alert Check',
        replace_existing=True
    )
    
    logger.info("Added daily alert check job (runs at 9:00 AM UTC)")


def start_scheduler() -> BackgroundScheduler:
    """
    Start the scheduler with alert job configured.
    
    Returns:
        Started scheduler instance
    
    Example:
        scheduler = start_scheduler()
        # Scheduler is now running in background
    """
    scheduler = get_scheduler()
    
    # Add alert job if not already added
    if not scheduler.get_job('daily_alert_check'):
        add_alert_job(scheduler)
    
    # Start scheduler if not already running
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started successfully")
    
    return scheduler


def stop_scheduler() -> None:
    """
    Stop the scheduler gracefully.
    
    Example:
        stop_scheduler()  # Stops background scheduler
    """
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped")
        _scheduler = None


def get_next_run_time() -> str:
    """
    Get the next scheduled run time for alert check.
    
    Returns:
        ISO format timestamp of next run, or "Not scheduled" if job not found
    
    Example:
        next_run = get_next_run_time()
        print(f"Next alert check: {next_run}")
    """
    scheduler = get_scheduler()
    job = scheduler.get_job('daily_alert_check')
    
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    
    return "Not scheduled"


def trigger_alert_check_now() -> dict:
    """
    Manually trigger an immediate alert check (for testing/admin use).
    
    Returns:
        Result dict from check_and_send_alerts
    
    Example:
        result = trigger_alert_check_now()
        if result["success"]:
            print(f"Sent {result['data']['alerts_sent']} alerts")
    """
    logger.info("Manually triggering alert check...")
    
    db = SessionLocal()
    try:
        result = check_and_send_alerts(db)
        
        if result["success"]:
            logger.info(
                f"Manual alert check completed: {result['data']['alerts_sent']} alerts sent"
            )
        else:
            logger.error(f"Manual alert check failed: {result['error']}")
        
        return result
    
    finally:
        db.close()
