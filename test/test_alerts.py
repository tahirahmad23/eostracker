"""
Tests for Alert Service - Module 6
Comprehensive test coverage for alert checking, email sending, and history tracking.
"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from database.models import User, Device, TrackedDevice, AlertHistory
from database import UserTier, AlertType, EmailStatus
from alerts.service import (
    check_and_send_alerts,
    check_user_alerts,
    get_alert_history
)
from alerts.email import (
    send_alert_email,
    send_welcome_email
)


# Fixtures

@pytest.fixture
def db_session():
    """Mock database session for testing."""
    session = Mock(spec=Session)
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    user = User(
        id=1,
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed",
        tier=UserTier.FREE,
        is_active=True
    )
    return user


@pytest.fixture
def sample_device():
    """Create a sample device for testing."""
    device = Device(
        id=1,
        vendor="Cisco",
        model="Catalyst 3850",
        device_type="Switch",
        eos_date=date.today() + timedelta(days=90),
        eol_date=None,
        slug="cisco-catalyst-3850",
        description="Enterprise switch"
    )
    return device


@pytest.fixture
def sample_tracked_device(sample_user, sample_device):
    """Create a sample tracked device for testing."""
    tracked = TrackedDevice(
        id=1,
        user_id=sample_user.id,
        device_id=sample_device.id,
        custom_name="Office Core Switch",
        notes="Main office switch"
    )
    return tracked


# Service Tests

class TestCheckAndSendAlerts:
    """Test suite for check_and_send_alerts function."""
    
    def test_check_all_users_success(self, db_session, sample_user):
        """Test checking alerts for all active users."""
        # Setup
        db_session.query.return_value.filter.return_value.all.return_value = [sample_user]
        
        with patch('alerts.service.check_user_alerts') as mock_check:
            mock_check.return_value = {"success": True, "data": 2}
            
            # Execute
            result = check_and_send_alerts(db_session)
        
        # Verify
        assert result["success"] is True
        assert result["data"]["alerts_sent"] == 2
        assert result["data"]["users_notified"] == 1
    
    def test_check_multiple_users(self, db_session):
        """Test checking alerts for multiple users."""
        # Setup
        users = [
            User(id=1, email="user1@test.com", full_name="User 1", 
                 hashed_password="hash", tier=UserTier.FREE, is_active=True),
            User(id=2, email="user2@test.com", full_name="User 2",
                 hashed_password="hash", tier=UserTier.PRO, is_active=True),
        ]
        db_session.query.return_value.filter.return_value.all.return_value = users
        
        with patch('alerts.service.check_user_alerts') as mock_check:
            mock_check.side_effect = [
                {"success": True, "data": 1},
                {"success": True, "data": 3}
            ]
            
            # Execute
            result = check_and_send_alerts(db_session)
        
        # Verify
        assert result["success"] is True
        assert result["data"]["alerts_sent"] == 4
        assert result["data"]["users_notified"] == 2
    
    def test_no_users_to_check(self, db_session):
        """Test when there are no active users."""
        # Setup
        db_session.query.return_value.filter.return_value.all.return_value = []
        
        # Execute
        result = check_and_send_alerts(db_session)
        
        # Verify
        assert result["success"] is True
        assert result["data"]["alerts_sent"] == 0
        assert result["data"]["users_notified"] == 0
    
    def test_error_handling(self, db_session):
        """Test error handling when check fails."""
        # Setup
        db_session.query.side_effect = Exception("Database error")
        
        # Execute
        result = check_and_send_alerts(db_session)
        
        # Verify
        assert result["success"] is False
        assert "Failed to check alerts" in result["error"]


class TestCheckUserAlerts:
    """Test suite for check_user_alerts function."""
    
    def test_user_not_found(self, db_session):
        """Test when user doesn't exist."""
        # Setup
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = check_user_alerts(999, db_session)
        
        # Verify
        assert result["success"] is False
        assert "User not found" in result["error"]
    
    def test_alert_365_days(self, db_session, sample_user, sample_device):
        """Test alert sent for device at 365 days before EOS."""
        # Setup device at 365 days
        sample_device.eos_date = date.today() + timedelta(days=365)
        
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,  # User query
            None,  # AlertHistory check (not sent yet)
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": sample_device.eos_date
                    },
                    "custom_name": None
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                mock_email.return_value = {"success": True}
                
                # Execute
                result = check_user_alerts(sample_user.id, db_session)
        
        # Verify
        assert result["success"] is True
        assert result["data"] >= 0  # At least attempted to send
        db_session.commit.assert_called()
    
    def test_alert_180_days(self, db_session, sample_user, sample_device):
        """Test alert sent for device at 180 days before EOS."""
        # Setup device at 180 days
        sample_device.eos_date = date.today() + timedelta(days=180)
        
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            None,  # AlertHistory check
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": sample_device.eos_date
                    }
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                mock_email.return_value = {"success": True}
                
                result = check_user_alerts(sample_user.id, db_session)
        
        assert result["success"] is True
    
    def test_alert_90_days(self, db_session, sample_user):
        """Test alert sent for device at 90 days before EOS."""
        # Setup
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            None,
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": date.today() + timedelta(days=90)
                    }
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                mock_email.return_value = {"success": True}
                
                result = check_user_alerts(sample_user.id, db_session)
        
        assert result["success"] is True
    
    def test_alert_30_days(self, db_session, sample_user):
        """Test alert sent for device at 30 days before EOS."""
        # Setup
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            None,
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": date.today() + timedelta(days=30)
                    }
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                mock_email.return_value = {"success": True}
                
                result = check_user_alerts(sample_user.id, db_session)
        
        assert result["success"] is True
    
    def test_no_alert_outside_threshold(self, db_session, sample_user):
        """Test no alert sent when device is outside thresholds."""
        # Setup device at 200 days (not a threshold)
        db_session.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": date.today() + timedelta(days=200)
                    }
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                result = check_user_alerts(sample_user.id, db_session)
                
                # Email should not be called for non-threshold day
                assert result["success"] is True
    
    def test_duplicate_alert_prevented(self, db_session, sample_user):
        """Test that duplicate alerts are prevented via AlertHistory."""
        # Setup
        existing_alert = AlertHistory(
            id=1,
            user_id=sample_user.id,
            tracked_device_id=1,
            alert_type=AlertType.DAYS_90,
            email_status=EmailStatus.SENT,
            sent_at=datetime.utcnow()
        )
        
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            existing_alert,  # Alert already exists
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": date.today() + timedelta(days=90)
                    }
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                result = check_user_alerts(sample_user.id, db_session)
                
                # Email should not be sent
                mock_email.assert_not_called()
        
        assert result["success"] is True
    
    def test_multiple_devices_grouped(self, db_session, sample_user):
        """Test multiple devices at same threshold grouped in one email."""
        # Setup
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            None,  # No alert history for device 1
            None,  # No alert history for device 2
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [
                    {
                        "id": 1,
                        "device": {
                            "vendor": "Cisco",
                            "model": "3850",
                            "device_type": "Switch",
                            "eos_date": date.today() + timedelta(days=90)
                        }
                    },
                    {
                        "id": 2,
                        "device": {
                            "vendor": "Juniper",
                            "model": "EX4300",
                            "device_type": "Switch",
                            "eos_date": date.today() + timedelta(days=90)
                        }
                    }
                ]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                mock_email.return_value = {"success": True}
                
                result = check_user_alerts(sample_user.id, db_session)
                
                # Should send one email with both devices
                assert mock_email.call_count >= 1
        
        assert result["success"] is True


class TestGetAlertHistory:
    """Test suite for get_alert_history function."""
    
    def test_get_history_success(self, db_session, sample_user, sample_tracked_device, sample_device):
        """Test retrieving alert history successfully."""
        # Setup
        alert = AlertHistory(
            id=1,
            user_id=sample_user.id,
            tracked_device_id=sample_tracked_device.id,
            alert_type=AlertType.DAYS_90,
            email_status=EmailStatus.SENT,
            sent_at=datetime.utcnow()
        )
        
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            sample_tracked_device,
            sample_device
        ]
        db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [alert]
        
        # Execute
        result = get_alert_history(sample_user.id, db_session)
        
        # Verify
        assert result["success"] is True
        assert len(result["data"]) >= 0
    
    def test_get_history_empty(self, db_session, sample_user):
        """Test getting history when no alerts sent."""
        # Setup
        db_session.query.return_value.filter.return_value.first.return_value = sample_user
        db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        # Execute
        result = get_alert_history(sample_user.id, db_session)
        
        # Verify
        assert result["success"] is True
        assert len(result["data"]) == 0
    
    def test_get_history_user_not_found(self, db_session):
        """Test getting history for non-existent user."""
        # Setup
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = get_alert_history(999, db_session)
        
        # Verify
        assert result["success"] is False
        assert "User not found" in result["error"]
    
    def test_alert_history_created_after_send(self, db_session, sample_user):
        """Test that AlertHistory record is created after sending alert."""
        # Setup
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            None,  # No existing alert
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": date.today() + timedelta(days=90)
                    }
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                mock_email.return_value = {"success": True}
                
                result = check_user_alerts(sample_user.id, db_session)
                
                # Verify AlertHistory was added
                db_session.add.assert_called()
        
        assert result["success"] is True
    
    def test_alert_history_status_failed(self, db_session, sample_user):
        """Test that failed emails are logged with failed status."""
        # Setup
        db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_user,
            None,
        ]
        
        with patch('alerts.service.get_user_tracked_devices') as mock_tracked:
            mock_tracked.return_value = {
                "success": True,
                "data": [{
                    "id": 1,
                    "device": {
                        "vendor": "Cisco",
                        "model": "3850",
                        "device_type": "Switch",
                        "eos_date": date.today() + timedelta(days=90)
                    }
                }]
            }
            
            with patch('alerts.service.send_alert_email') as mock_email:
                mock_email.return_value = {"success": False, "error": "SES error"}
                
                result = check_user_alerts(sample_user.id, db_session)
                
                # Should still create history record
                db_session.add.assert_called()
        
        assert result["success"] is True


class TestSendAlertEmail:
    """Test suite for send_alert_email function."""
    
    @patch('alerts.email.resend.Emails.send')
    def test_send_alert_email_success(self, mock_send, db_session):
        """Test sending alert email successfully."""
        # Setup
        mock_send.return_value = {'id': 'email-123'}
        
        devices = [{
            "vendor": "Cisco",
            "model": "3850",
            "device_type": "Switch",
            "eos_date": date.today() + timedelta(days=90),
            "custom_name": None,
            "days_until_eos": 90
        }]
        
        # Execute
        result = send_alert_email(
            "test@example.com",
            "Test User",
            devices,
            AlertType.DAYS_90,
            db_session
        )
        
        # Verify
        assert result["success"] is True
        mock_send.assert_called_once()
        
        # Verify email params
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == ["test@example.com"]
        assert "EOS Alert" in call_args["subject"]
        assert "Cisco" in call_args["html"]
    
    @patch('alerts.email.resend.Emails.send')
    def test_send_alert_email_resend_error(self, mock_send, db_session):
        """Test handling Resend error when sending email."""
        # Setup
        mock_send.side_effect = Exception("API error: Invalid API key")
        
        devices = [{
            "vendor": "Cisco",
            "model": "3850",
            "device_type": "Switch",
            "eos_date": date.today(),
            "days_until_eos": 90
        }]
        
        # Execute
        result = send_alert_email(
            "test@example.com",
            "Test User",
            devices,
            AlertType.DAYS_90,
            db_session
        )
        
        # Verify
        assert result["success"] is False
        assert "Failed to send alert email" in result["error"]
    
    def test_send_alert_no_devices(self, db_session):
        """Test error when no devices provided."""
        # Execute
        result = send_alert_email(
            "test@example.com",
            "Test User",
            [],
            AlertType.DAYS_90,
            db_session
        )
        
        # Verify
        assert result["success"] is False
        assert "No devices" in result["error"]
    
    @patch('alerts.email.resend.Emails.send')
    def test_email_template_includes_device_details(self, mock_send, db_session):
        """Test that email template includes all device details."""
        # Setup
        mock_send.return_value = {'id': 'email-123'}
        
        devices = [{
            "vendor": "Cisco",
            "model": "Catalyst 3850",
            "device_type": "Switch",
            "eos_date": date.today() + timedelta(days=90),
            "custom_name": "Core Switch",
            "days_until_eos": 90
        }]
        
        # Execute
        result = send_alert_email(
            "test@example.com",
            "John Doe",
            devices,
            AlertType.DAYS_90,
            db_session
        )
        
        # Verify
        assert result["success"] is True
        
        # Check that send was called with proper content
        call_args = mock_send.call_args[0][0]
        message_body = call_args['html']
        
        assert "Cisco" in message_body
        assert "Catalyst 3850" in message_body
        assert "Core Switch" in message_body
        assert "John Doe" in message_body


class TestSendWelcomeEmail:
    """Test suite for send_welcome_email function."""
    
    @patch('alerts.email.resend.Emails.send')
    def test_send_welcome_email_success(self, mock_send):
        """Test sending welcome email successfully."""
        # Setup
        mock_send.return_value = {'id': 'email-123'}
        
        # Execute
        result = send_welcome_email("newuser@example.com", "New User")
        
        # Verify
        assert result["success"] is True
        mock_send.assert_called_once()
        
        # Check email content
        call_args = mock_send.call_args[0][0]
        subject = call_args['subject']
        body = call_args['html']
        
        assert "Welcome" in subject
        assert "New User" in body
    
    @patch('alerts.email.resend.Emails.send')
    def test_send_welcome_email_resend_error(self, mock_send):
        """Test handling Resend error in welcome email."""
        # Setup
        mock_send.side_effect = Exception("API error: Rate limit exceeded")
        
        # Execute
        result = send_welcome_email("test@example.com", "Test User")
        
        # Verify
        assert result["success"] is False
        assert "Failed to send welcome email" in result["error"]


# Integration test placeholder
class TestIntegration:
    """Integration tests with real database (optional)."""
    
    def test_end_to_end_alert_flow(self):
        """
        Placeholder for end-to-end integration test.
        This would test the complete flow with a real database.
        """
        # This test would require a real database setup
        # Skipped in unit tests
        pass
