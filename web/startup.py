"""
Application Startup and Shutdown Handlers

This module integrates the alert scheduler with your FastAPI application.
Import and use these in your main.py or app.py file.

Usage in main.py:
    from web.startup import startup_handler, shutdown_handler
    
    app = FastAPI()
    
    @app.on_event("startup")
    async def on_startup():
        await startup_handler()
    
    @app.on_event("shutdown")
    async def on_shutdown():
        await shutdown_handler()
"""


from alerts.scheduler import start_scheduler, stop_scheduler, get_next_run_time
import logging
logger = logging.getLogger(__name__)


async def startup_handler():
    """
    Handle application startup.
    
    - Starts the alert scheduler if SCHEDULER_ENABLED=True
    - Logs scheduler status and next run time
    
    This should be called in your FastAPI app's startup event.
    """
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP")
    logger.info("=" * 60)
    
    # Start the alert scheduler
    scheduler = start_scheduler()
    
    if scheduler:
        next_run = get_next_run_time()
        logger.info(f"✓ Alert scheduler initialized")
        logger.info(f"  Next check: {next_run}")
    else:
        logger.info("ℹ Alert scheduler disabled (set SCHEDULER_ENABLED=True to enable)")
    
    logger.info("=" * 60)


async def shutdown_handler():
    """
    Handle application shutdown.
    
    - Gracefully stops the alert scheduler
    - Ensures all jobs complete
    
    This should be called in your FastAPI app's shutdown event.
    """
    logger.info("=" * 60)
    logger.info("APPLICATION SHUTDOWN")
    logger.info("=" * 60)
    
    # Stop the scheduler
    stop_scheduler()
    logger.info("✓ Alert scheduler stopped")
    
    logger.info("=" * 60)
