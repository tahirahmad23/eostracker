# QA Test Plan for EOS Tracker

## Overview
This document outlines a comprehensive, production-grade Quality Assurance (QA) strategy for the EOS Tracker application. The plan covers Unit, Integration, End-to-End (E2E), Performance, and Security testing.

## 1. Test Strategy

### 1.1 Unit Testing
**Goal**: Verify individual components work in isolation.
**Tools**: `pytest`, `unittest.mock`
**Coverage**:
- **Models**:
    - Verify `User` creation, password hashing, and relationship integrity.
    - Verify `Device` and `TrackedDevice` constraints (e.g., unique constraints).
    - Test Enum validations (`UserTier`, `AlertType`, `EmailStatus`).
- **Alerts Module (`alerts/email.py`)**:
    - `_create_alert_email_html`: Verify device table rendering, date formatting, and threshold coloring.
    - `_create_welcome_email_html`: Verify context injection (user name).
    - `send_alert_email`: Mock `resend.Emails.send` to verify payload structure and API key handling.
    - `send_welcome_email`: Mock successful and failed sending scenarios.
- **Admin Utilities**:
    - Test `hash_password` and password verification (referenced in `admin/views.py`).

### 1.2 Integration Testing
**Goal**: Verify interactions between components (e.g., API <-> DB, Webhooks).
**Tools**: `pytest`, `TestClient` (FastAPI)
**Coverage**:
- **Authentication**:
    - Successful Login/Register/Logout.
    - Invalid credentials/duplicate email handling.
    - Session/Cookie persistence (`access_token` cookie `httponly` check).
    - Protected route access control (Admin vs User).
- **Subscription Flow (`web/routes/subscription.py`)**:
    - `create_checkout`: Verify redirection to Lemon Squeezy.
    - `lemonsqueezy_webhook`:
        - Verify signature validation (Mock `X-Signature` header).
        - Test `subscription_created` event: Verify User tier updates to `PRO`.
        - Test `subscription_updated` (cancellation): Verify User tier downgrade logic.
        - Test invalid JSON or missing headers response (400 Bad Request).
- **Data Operations**:
    - CRUD operations for `TrackedDevices`.
    - Search functionality for `Devices`.
- **Admin Interface**:
    - `UserAdmin`: Verify password hashing on create/update.
    - Verify `AlertHistory` is read-only (no create/edit forms accessible).
    - ACL: Verify non-admin users cannot access `/admin`.

### 1.3 End-to-End (E2E) Testing
**Goal**: Verify Critical User Journeys (CUJs) from a user's perspective.
**Tools**: `Playwright` (Recommended for modern web apps) or `Selenium`.
**Scenarios**:
1.  **New User Onboarding**:
    - Register -> System sends Welcome Email -> User Auto-logged in -> Dashboard.
2.  **Tracking Workflow**:
    - Login -> Search Device (e.g., "Cisco") -> Add to Tracked -> Verify in Dashboard.
3.  **Subscription Upgrade**:
    - Free User (Limit 3 devices) -> Try adding 4th (Error) -> Click Upgrade -> (Mock Payment) -> Verify Pro Badge -> Add 4th Device (Success).
4.  **Admin Management**:
    - Admin Login -> Create New Device "TestRouter" -> Verify available in User Search.

### 1.4 Performance Testing
**Goal**: Ensure system handles expected load.
**Tools**: `Locust` or `k6`
**Scenarios**:
- **Dashboard Load**: Simulate 100 users loading dashboard with 50 tracked devices each.
- **Search Latency**: Heavy search queries on `Devices` catalog (concurrent).
- **Webhook Throughput**: Simulate burst of webhook events from Lemon Squeezy.

### 1.5 Security Testing
**Goal**: Identify vulnerabilities.
**Tools**: `OWASP ZAP` (Automated scan), `Bandit` (Static analysis).
**Checks**:
- **Auth**: Brute force protection (rate limiting), Weak password rejection.
- **XSS**: Input sanitation in `custom_name` for Track Devices.
- **Injection**: Ensure SQLAdmin filters are secure.
- **Webhook Security**: Verify `X-Signature` is strictly enforced (replay attacks/spoofing).

## 2. Test Environment Setup
- **Dockerized Testing**: Use `docker-compose.test.yml` to spin up a clean DB for each test run.
- **CI/CD Integration**:
    - GitHub Actions / GitLab CI.
    - Trigger: PRs to `main` and `develop`.
    - Steps: Lint (Black/Flake8) -> Unit -> Integration -> Build Docker -> (Optional) E2E.

## 3. Implementation Phases

### Phase 1: Foundation (Current Priority)
- [ ] Setup `pytest` configuration and fixtures (`conftest.py`).
- [ ] Implement Model functional tests (User, Device).
- [ ] Implement Auth Route integration tests (Login/Register).

### Phase 2: Critical Logic coverage
- [ ] **Alerts**: Unit test email rendering and mocking Resend API.
- [ ] **Subscription**: Test webhook signature validation and tier update logic.
- [ ] **Admin**: Test password hashing hook in `UserAdmin`.

### Phase 3: E2E and Reliability
- [ ] Setup Playwright for "New User Onboarding" flow.
- [ ] Load test search endpoints.

## 4. Specific Test Cases to Implement

### Alerts (`alerts/email.py`)
- `test_alert_email_rendering`: Assert "Days Left" badge color is correct for different thresholds.
- `test_send_email_no_api_key`: Should handle missing key gracefully (Result["success"] is False).

### Subscription (`subscription.py`)
- `test_webhook_invalid_signature`: Post to `/webhooks/lemonsqueezy` with wrong signature -> 400.
- `test_webhook_subscription_created`: Post valid payload -> User.tier becomes `PRO`.

### Admin (`admin/views.py`)
- `test_admin_create_user_hashes_pw`: Create user via Admin -> Verify `hashed_password` in DB is not plain text.
- `test_admin_alert_history_readonly`: Attempt POST to alert history endpoint -> 405 Method Not Allowed / 403.
