# Application Security Plan

## Overview
This plan outlines "just enough" security measures for the EOS Tracker application running in a local Docker environment. The focus is on securing the code logic, data handling, and application dependencies, acknowledging that server-level security (firewalls, WAF) will be handled post-deployment.

## 1. Code Security & Vulnerability Remediation

### 1.1 Cross-Site Scripting (XSS) Prevention [CRITICAL]
**Found Issue**: `alerts/email.py` constructs HTML emails using f-strings with user input (`custom_name`).
**Risk**: Malicious users could inject scripts or break HTML layout via crafted device names.
**Plan**:
- Use `html.escape` from Python's standard library for all user inputs variables before injecting into HTML.
- **Better**: Refactor email generation to use Jinja2 templates (consistent with Flask/FastAPI best practices) which has auto-escaping enabled by default.

### 1.2 CSRF Protection [HIGH]
**Context**: FastAPI does not have built-in CSRF protection for Form POSTs.
**Risk**: Authenticated users could be tricked into submitting forms (e.g., deleting a device) by visiting a malicious site.
**Plan**:
- Since `SameSite=Lax` is already used in cookies (saw in `web/routes/auth.py`), we have partial protection against cross-site POSTs in modern browsers.
- **Action**: Verify `SameSite=Lax` is consistently applied to all cookies.
- **Action**: For a more robust solution, implement a lightweight Double Submit Cookie pattern or use `starlette-csrf` middleware for sensitive form actions (`/tracking/add`, `/subscription/cancel`).

### 1.3 Authorization & Access Control
**Context**: Reviewed `tracking/service.py` and `web/routes/api.py`.
**Findings**:
- `remove_tracked_device`: **SECURE**. Checks `if tracked.user_id != user_id`.
- `API Routes`: Uses `get_current_user_optional` then manually checks `if not current_user`.
- **Plan**:
    - Refactor API routes to use a strict dependency `get_current_user` (not optional) for protected endpoints. This ensures 401 Unauthorized is returned automatically and standardizes behavior.

### 1.4 Input Validation
**Context**: `web/routes/api.py` handles CSV/Excel uploads.
**Risk**: Large file uploads (DoS) or malformed files crashing the server.
**Plan**:
- Validate file size limits (e.g., max 5MB) before reading content.
- Wrap `pd.read_excel` in stricter error handling.

## 2. Secure Configuration

### 2.1 Secret Management
**Current**: `.env` is used.
**Plan**:
- Ensure `.env` is **never** committed (already in `.gitignore`).
- Verify `SESSION_SECRET_KEY` and `JWT_SECRET_KEY` are distinct and strong in the example `.env` (or documentation).

### 2.2 Security Headers
**Context**: `main.py` has basic CORS and Proxy headers.
**Plan**:
- Implement a simple middleware to add standard security headers to all responses:
    - `X-Content-Type-Options: nosniff`
    - `X-Frame-Options: DENY` (or `SAMEORIGIN`)
    - `Referrer-Policy: strict-origin-when-cross-origin`

## 3. Dependency Security (Software Composition Analysis)

### 3.1 Vulnerability Scanning
**Plan**:
- Add `safety` or `bandit` to `requirements.txt` (dev dependencies).
- Run `safety check` locally to identify known vulnerabilities in libraries like `pandas`, `fastapi`, or `python-jose`.

## 4. Implementation Checklist

### Immediate Code Fixes
- [ ] **Fix XSS in Email**: Update `alerts/email.py` to use `html.escape`.
- [ ] **Strict API Auth**: Create `get_current_user` dependency in `auth.py` that raises HTTPException(401) and use it in `api.py`.
- [ ] **Security Headers**: Add middleware in `main.py`.

### Configuration Policy
- [ ] Use `python-dotenv` to load secrets (Verified: usage in `main.py`).
- [ ] Ensure `Debug=False` behavior (or equivalent) in code when running in specific modes (though specific env var not seen yet).

### Verification
- [ ] Manual test: Try injecting `<b>Bold</b>` in device custom name and verify it displays as text, not HTML in emails.
- [ ] Automated scan: Run `bandit -r .` to find potential Python security issues.
