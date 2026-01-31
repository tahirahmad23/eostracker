"""
Email Service - Module 6
Handles email delivery via Resend with HTML templates for alerts and welcome emails.
"""

import os
from typing import Dict, List, Any
from datetime import datetime
import resend
from sqlalchemy.orm import Session
from html import escape as html_escape
import logging

logger = logging.getLogger(__name__)

# Type alias for Result pattern
Result = Dict[str, Any]


# Email configuration from environment
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")

# Configure Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def _create_alert_email_html(user_name: str, devices: List[Dict], alert_type: str) -> str:
    """
    Create HTML email template for EOS alerts.
    
    Args:
        user_name: User's full name
        devices: List of device dicts with vendor, model, eos_date, etc.
        alert_type: Alert type (365, 180, 90, 30)
    
    Returns:
        HTML string for email body
    """
    # Determine alert message based on type
    alert_messages = {
        "365": "1 year (365 days)",
        "180": "6 months (180 days)",
        "90": "3 months (90 days)",
        "30": "1 month (30 days)"
    }
    
    threshold = alert_messages.get(alert_type, f"{alert_type} days")
    device_count = len(devices)
    device_plural = "device" if device_count == 1 else "devices"
    verb = "is" if device_count == 1 else "are"
    # Escape user name to prevent XSS
    safe_user_name = html_escape(user_name)

    if alert_type != "0":
        msg = f'You have <strong>{device_count} {device_plural}</strong> reaching End-of-Support in less than <strong style="color: #dc2626;">{threshold}</strong>.'
    else:
        msg = f'You have <strong>{device_count} {device_plural}</strong> that {verb} <strong style="color: #dc2626;">No longer supported</strong>.'
    
    # Build device rows
    device_rows = ""
    for device in devices:
        # Escape custom name if present
        safe_custom_name = html_escape(device['custom_name']) if device.get('custom_name') else ""
        custom_name_display = f"<br><small style='color: #666;'>({safe_custom_name})</small>" if safe_custom_name else ""
        eos_date_str = device['eos_date'].strftime('%B %d, %Y') if isinstance(device['eos_date'], datetime) else str(device['eos_date'])
        
        device_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                <strong>{device['vendor']} {device['model']}</strong>{custom_name_display}
                <br><small style="color: #6c757d;">{device['device_type']}</small>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                <span style="color: #dc2626; font-weight: bold;">{eos_date_str}</span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                <span style="background: #f59e0b; color: white; padding: 4px 8px; border-radius: 4px; font-size: 14px;">
                    {device['days_until_eos']} days
                </span>
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EOS Alert</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #003f5d 0%, #00547c 100%); padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">⚠️ EOS Alert</h1>
                                <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 16px;">End-of-Support Notification</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 30px;">
                                <p style="font-size: 16px; color: #212529; margin: 0 0 20px 0;">
                                    Hello <strong>{safe_user_name}</strong>,
                                </p>
                                
                                <p style="font-size: 16px; color: #212529; margin: 0 0 20px 0;">
                                   {msg}
                                </p>
                                
                                <div style="background-color: #fff3cd; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
                                    <p style="margin: 0; color: #856404; font-size: 14px;">
                                        <strong>⏰ Action Required:</strong> Review these devices and plan for replacements or upgrades to maintain security and support coverage.
                                    </p>
                                </div>
                                
                                <!-- Device Table -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0; border: 1px solid #ddd; border-radius: 4px; overflow: hidden;">
                                    <thead>
                                        <tr style="background-color: #f8f9fa;">
                                            <th style="padding: 12px; text-align: left; color: #333; font-size: 14px; border-bottom: 2px solid #ddd;">Device</th>
                                            <th style="padding: 12px; text-align: center; color: #333; font-size: 14px; border-bottom: 2px solid #ddd;">EOS Date</th>
                                            <th style="padding: 12px; text-align: center; color: #333; font-size: 14px; border-bottom: 2px solid #ddd;">Days Left</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {device_rows}
                                    </tbody>
                                </table>
                                
                                <p style="font-size: 14px; color: #666; margin: 20px 0 0 0;">
                                    <strong>What happens at EOS?</strong><br>
                                    • No more security patches or bug fixes<br>
                                    • Potential compliance violations<br>
                                    • Increased vulnerability to attacks<br>
                                    • Loss of vendor support
                                </p>
                                
                                <div style="text-align: center; margin: 30px 0;">
                                    <a href="https://eostracker.xyz/dashboard" style="background-color: #00699b; color: #ffffff; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                                        View Dashboard
                                    </a>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
                                <p style="margin: 0; font-size: 12px; color: #666;">
                                    You're receiving this email because you're tracking these devices on EOS Alert.
                                </p>
                                <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                                    <a href="https://eostracker.xyz/settings" style="color: #00699b; text-decoration: none;">Manage Alert Settings</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return html


def _create_welcome_email_html(user_name: str) -> str:
    """
    Create HTML email template for welcome email.
    
    Args:
        user_name: User's full name
    
    Returns:
        HTML string for email body
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to EOS Alert</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #003f5d 0%, #00547c 100%); padding: 40px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 32px;">Welcome to EOS Alert!</h1>
                                <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 18px;">Your Network's Safety Net</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <p style="font-size: 18px; color: #212529; margin: 0 0 20px 0;">
                                    Hi <strong>{html_escape(user_name)}</strong>,
                                </p>
                                
                                <p style="font-size: 16px; color: #495057; margin: 0 0 20px 0;">
                                    Welcome aboard! We're excited to help you stay ahead of End-of-Support dates and keep your network infrastructure secure.
                                </p>
                                
                                <div style="background-color: #e6f5f0; border-left: 4px solid #009b69; padding: 20px; margin: 30px 0;">
                                    <h3 style="margin: 0 0 15px 0; color: #005d3f; font-size: 18px;">Getting Started</h3>
                                    <ol style="margin: 0; padding-left: 20px; color: #495057; font-size: 15px; line-height: 1.8;">
                                        <li><strong>Add your devices:</strong> Track up to 3 devices on the free tier</li>
                                        <li><strong>Set up alerts:</strong> Receive notifications at 365, 180, 90, and 30 days before EOS</li>
                                        <li><strong>Generate reports:</strong> Create professional PDF reports for stakeholders</li>
                                    </ol>
                                </div>
                                
                                <h3 style="color: #212529; font-size: 18px; margin: 30px 0 15px 0;">📊 What You Can Do</h3>
                                
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                    <tr>
                                        <td style="padding: 15px; background-color: #f8f9fa; border-radius: 4px; margin-bottom: 10px;">
                                            <strong style="color: #009b69; font-size: 16px;">✓</strong>
                                            <strong style="color: #212529; margin-left: 10px;">Track Critical Dates</strong>
                                            <p style="margin: 5px 0 0 35px; color: #495057; font-size: 14px;">
                                                Monitor EOS dates for all your network equipment in one place
                                            </p>
                                        </td>
                                    </tr>
                                    <tr><td style="height: 10px;"></td></tr>
                                    <tr>
                                        <td style="padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
                                            <strong style="color: #009b69; font-size: 16px;">✓</strong>
                                            <strong style="color: #212529; margin-left: 10px;">Automated Alerts</strong>
                                            <p style="margin: 5px 0 0 35px; color: #495057; font-size: 14px;">
                                                Get email notifications at key milestones before support ends
                                            </p>
                                        </td>
                                    </tr>
                                    <tr><td style="height: 10px;"></td></tr>
                                    <tr>
                                        <td style="padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
                                            <strong style="color: #009b69; font-size: 16px;">✓</strong>
                                            <strong style="color: #212529; margin-left: 10px;">Professional Reports</strong>
                                            <p style="margin: 5px 0 0 35px; color: #495057; font-size: 14px;">
                                                Generate PDF reports to share with management and stakeholders
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <div style="background-color: #fff3cd; border-left: 4px solid #f59e0b; padding: 15px; margin: 30px 0;">
                                    <p style="margin: 0; color: #856404; font-size: 14px;">
                                        <strong>💡 Pro Tip:</strong> Upgrade to Pro ($49/month) for unlimited device tracking, CSV bulk import, and enhanced reporting features.
                                    </p>
                                </div>
                                
                                <div style="text-align: center; margin: 40px 0 20px 0;">
                                    <a href="https://eostracker.xyz/dashboard" style="background-color: #00699b; color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 18px; display: inline-block; font-weight: bold;">
                                        Go to Dashboard
                                    </a>
                                </div>
                                
                                <p style="font-size: 14px; color: #666; margin: 30px 0 0 0; text-align: center;">
                                    Need help? Reply to this email or visit our <a href="https://eostracker.xyz/help" style="color: #00699b;">Help Center</a>
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
                                <p style="margin: 0; font-size: 12px; color: #666;">
                                    EOS Alert - Proactive Network Infrastructure Management
                                </p>
                                <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                                    © 2026 EOS Alert. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return html


def send_alert_email(
    user_email: str,
    user_name: str,
    devices: List[Dict],
    alert_type: str,
    db: Session
) -> Result:
    """
    Send EOS alert email via Resend.
    
    Args:
        user_email: User's email address
        user_name: User's full name
        devices: List of device dicts with vendor, model, eos_date, days_until_eos
        alert_type: Alert type ("365", "180", "90", "30")
        db: Database session (not used, for consistency)
    
    Returns:
        Result dict with:
        - success: True if email sent successfully
        - error: Error message if failed
    
    Example:
        devices = [{"vendor": "Cisco", "model": "3850", ...}]
        result = send_alert_email("user@example.com", "John", devices, "90", db)
    """
    try:
        if not devices:
            logger.warning("Alert email not sent: no devices provided")
            return {"success": False, "error": "No devices provided for alert"}
        
        if not RESEND_API_KEY:
            logger.warning("Alert email not sent: RESEND_API_KEY not configured")
            return {"success": False, "error": "RESEND_API_KEY not configured"}
        
        # Create email content
        html_body = _create_alert_email_html(user_name, devices, alert_type)
        
        # Determine subject based on alert type
        device_count = len(devices)
        device_plural = "device" if device_count == 1 else "devices"
        
        alert_labels = {
            "365": "1 Year",
            "180": "6 Months",
            "90": "3 Months",
            "30": "30 Days"
        }
        if alert_type != "0":
            threshold_label = alert_labels.get(alert_type, f"{alert_type} days")
            subject = f"⚠️ EOS Alert: {device_count} {device_plural} reaching End-of-Support in {threshold_label}"
        else:
            subject = f'EOS Alert: {device_count} {device_plural} is no longer supported'

        # Send email via Resend
        params = {
            "from": FROM_EMAIL,
            "to": [user_email],
            "subject": subject,
            "html": html_body
        }
        
        email = resend.Emails.send(params)
        logger.info(
            "Alert email sent",
            extra={"device_count": len(devices), "alert_type": str(alert_type)},
        )
        return {"success": True, "data": {"id": email.get("id")}}
    
    except Exception as e:
        logger.exception("Failed to send alert email")
        return {
            "success": False,
            "error": f"Failed to send alert email: {str(e)}"
        }


def send_welcome_email(user_email: str, user_name: str) -> Result:
    """
    Send welcome email to new user.
    
    Args:
        user_email: User's email address
        user_name: User's full name
    
    Returns:
        Result dict with:
        - success: True if email sent successfully
        - error: Error message if failed
    
    Example:
        result = send_welcome_email("user@example.com", "John Doe")
        if result["success"]:
            print("Welcome email sent!")
    """
    try:
        if not RESEND_API_KEY:
            logger.warning("Welcome email not sent: RESEND_API_KEY not configured")
            return {"success": False, "error": "RESEND_API_KEY not configured"}
        
        # Create email content
        html_body = _create_welcome_email_html(user_name)
        subject = "Welcome to EOS Alert - Get Started Today!"
        # Send email via Resend
        params = {
            "from": FROM_EMAIL,
            "to": [user_email],
            "subject": subject,
            "html": html_body
        }
        
        email = resend.Emails.send(params)
        logger.info("Welcome email sent")
        return {"success": True, "data": {"id": email.get("id")}}
    
    except Exception as e:
        logger.exception("Failed to send welcome email")
        return {
            "success": False,
            "error": f"Failed to send welcome email: {str(e)}"
        }
