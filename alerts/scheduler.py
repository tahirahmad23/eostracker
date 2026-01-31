"""
Scheduler Configuration - Module 6
Configures APScheduler to run daily alert checks at user-defined UTC time.
Also handles debounced immediate alerts for newly-added critical devices.
"""

import os
import time
import logging
from datetime import datetime, timedelta
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

# Pending immediate alert checks - {user_id: {"job_id": str, "tracked_device_ids": set()}}
_pending_critical_checks = {}


# MODULE-LEVEL FUNCTION (required for APScheduler pickling)
def run_scheduled_alert_check():
    """
    Run scheduled alert checks with database session.
    
    This must be at module level (not nested) so APScheduler can pickle it
    when storing jobs in the database.
    """
    logger.info("Starting scheduled alert check...")
    
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


def execute_debounced_critical_check(user_id: int):
    """
    Execute debounced critical device check for a specific user.
    
    This must be at module level (not nested) so APScheduler can pickle it.
    Called after 10-minute debounce period when user adds devices.
    
    Args:
        user_id: User ID to check critical devices for
    """
    global _pending_critical_checks
    
    logger.info(f"Executing debounced critical check for user {user_id}...")
    
    # Get the tracked device IDs from pending checks
    if user_id not in _pending_critical_checks:
        logger.warning(f"No pending critical checks found for user {user_id}")
        return
    
    tracked_device_ids = list(_pending_critical_checks[user_id]["tracked_device_ids"])
    
    # Clear the pending check
    del _pending_critical_checks[user_id]
    
    # Execute the check
    db = SessionLocal()
    try:
        from alerts.service import check_critical_tracked_devices
        
        result = check_critical_tracked_devices(user_id, tracked_device_ids, db)
        
        if result["success"]:
            if result["data"] > 0:
                logger.info(
                    f"✓ Sent {result['data']} critical alert(s) for user {user_id} "
                    f"({len(tracked_device_ids)} devices checked)"
                )
            else:
                logger.info(
                    f"No critical alerts needed for user {user_id} "
                    f"({len(tracked_device_ids)} devices checked)"
                )
        else:
            logger.error(f"Critical check failed for user {user_id}: {result['error']}")
    
    except Exception as e:
        logger.error(f"Exception during critical check for user {user_id}: {str(e)}", exc_info=True)
    
    finally:
        db.close()


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
    Runs at time specified by SCHEDULER_HOUR and SCHEDULER_MINUTE env vars.
    
    Args:
        scheduler: APScheduler instance
    
    Example:
        scheduler = create_scheduler()
        add_alert_job(scheduler)
        scheduler.start()
    """
    # Get schedule from environment variables
    scheduler_hour = int(os.getenv("SCHEDULER_HOUR", "9"))
    scheduler_minute = int(os.getenv("SCHEDULER_MINUTE", "0"))
    
    # Add job with cron trigger from env vars
    # Use textual reference to module-level function (required for pickling)
    trigger = CronTrigger(hour=scheduler_hour, minute=scheduler_minute, timezone='UTC')
    
    scheduler.add_job(
        func='alerts.scheduler:run_scheduled_alert_check',  # Textual reference
        trigger=trigger,
        id='daily_alert_check',
        name='Daily EOS Alert Check',
        replace_existing=True
    )
    
    logger.info(f"Added daily alert check job (runs at {scheduler_hour:02d}:{scheduler_minute:02d} UTC)")


def start_scheduler() -> BackgroundScheduler:
    """
    Start the scheduler with alert job configured.
    Only starts if SCHEDULER_ENABLED=True in environment.
    
    Returns:
        Started scheduler instance or None if disabled
    
    Example:
        scheduler = start_scheduler()
        if scheduler:
            print("Scheduler is running")
    """
    # Check if scheduler is enabled
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "False").lower() == "true"
    
    if not scheduler_enabled:
        logger.info("Alert scheduler is DISABLED (SCHEDULER_ENABLED=False)")
        return None
    
    scheduler = get_scheduler()
    
    # Start scheduler first (so it can query the job store)
    if not scheduler.running:
        scheduler.start()
        logger.info("✓ Alert scheduler STARTED successfully")
    
    # Add alert job if not already in job store
    # Check both in-memory and database
    
    if not scheduler.get_job('daily_alert_check'):
        add_alert_job(scheduler)
        logger.info("Alert job added to scheduler")
    else:
        logger.info("Alert job already exists (loaded from database)")
    
    # Log next run time
    next_run = get_next_run_time()
    logger.info(f"Next alert check scheduled for: {next_run}")
    
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


def trigger_immediate_critical_check(user_id: int, tracked_device_id: int) -> None:
    """
    Trigger an immediate critical device check with 10-minute debouncing.
    
    When a user adds a device, this schedules a check for 10 minutes later.
    If another device is added within 10 minutes, the timer resets and all
    devices from the session are checked together.
    
    Only checks critical devices (EOS or <90 days) to avoid spam.
    
    Args:
        user_id: User ID who added the device
        tracked_device_id: ID of the newly tracked device
    
    Example:
        # After user adds a device
        trigger_immediate_critical_check(user_id=123, tracked_device_id=456)
        # Timer starts...
        # User adds another device 2 minutes later
        trigger_immediate_critical_check(user_id=123, tracked_device_id=789)
        # Timer resets, both devices will be checked after 10 minutes
    """
    global _pending_critical_checks
    
    scheduler = get_scheduler()
    if scheduler is None:
        logger.debug("Scheduler not available, skipping critical check")
        return
    
    # If there's already a pending check for this user, cancel it
    if user_id in _pending_critical_checks:
        existing_job_id = _pending_critical_checks[user_id]["job_id"]
        
        try:
            scheduler.remove_job(existing_job_id)
            logger.debug(f"Cancelled existing critical check job {existing_job_id}")
        except Exception as e:
            logger.debug(f"Could not remove job {existing_job_id}: {e}")
        
        # Add new device to the existing set
        _pending_critical_checks[user_id]["tracked_device_ids"].add(tracked_device_id)
        logger.info(
            f"Added device {tracked_device_id} to pending check for user {user_id} "
            f"(total: {len(_pending_critical_checks[user_id]['tracked_device_ids'])} devices)"
        )
    else:
        # Start a new pending check
        _pending_critical_checks[user_id] = {
            "job_id": None,
            "tracked_device_ids": {tracked_device_id}
        }
        logger.info(f"Started new pending critical check for user {user_id}")
    
    # Schedule new job for 10 minutes from now
    run_time = datetime.utcnow() + timedelta(minutes=1)
    job_id = f"critical_check_{user_id}_{int(time.time() * 1000)}"
    
    try:
        scheduler.add_job(
            func='alerts.scheduler:execute_debounced_critical_check',
            args=[user_id],
            trigger='date',
            run_date=run_time,
            id=job_id,
            replace_existing=False
        )
        
        _pending_critical_checks[user_id]["job_id"] = job_id
        
        logger.info(
            f"✓ Scheduled critical check for user {user_id} at {run_time.strftime('%H:%M:%S UTC')} "
            f"({len(_pending_critical_checks[user_id]['tracked_device_ids'])} device(s) pending)"
        )
    
    except Exception as e:
        logger.error(f"Failed to schedule critical check: {e}", exc_info=True)
        # Clean up on failure
        if user_id in _pending_critical_checks:
            del _pending_critical_checks[user_id]

