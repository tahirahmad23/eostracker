"""
Alert Service Module - Module 6
Provides email alerts, scheduling, and alert history tracking.
"""

from alerts.service import (
    check_and_send_alerts,
    check_user_alerts,
    get_alert_history
)

from alerts.email import (
    send_alert_email,
    send_welcome_email
)

from alerts.scheduler import (
    start_scheduler,
    stop_scheduler,
    get_next_run_time,
    trigger_alert_check_now
)


__all__ = [
    # Service functions
    'check_and_send_alerts',
    'check_user_alerts',
    'get_alert_history',
    
    # Email functions
    'send_alert_email',
    'send_welcome_email',
    
    # Scheduler functions
    'start_scheduler',
    'stop_scheduler',
    'get_next_run_time',
    'trigger_alert_check_now',
]
