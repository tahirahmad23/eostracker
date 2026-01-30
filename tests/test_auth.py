
from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest

def test_register_page(client: TestClient):
    response = client.get("/register")
    assert response.status_code == 200
    assert "Register" in response.text

def test_login_page(client: TestClient):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text

@patch("web.routes.auth.send_welcome_email")
def test_register_flow_success(mock_email, client: TestClient, db):
    # Mock return value for email
    mock_email.return_value = {"success": True}
    
    data = {
        "email": "register@test.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "full_name": "Register Test",
        "agree_terms": True
    }
    
    response = client.post("/register", data=data, follow_redirects=False)
    
    # Expect redirect to dashboard
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    
    # Check cookie
    assert "access_token" in response.cookies

@patch("web.routes.auth.send_welcome_email")
def test_register_password_mismatch(mock_email, client: TestClient):
    data = {
        "email": "fail@test.com",
        "password": "Password123!",
        "password_confirm": "Mismatch!",
        "full_name": "Register Test",
        "agree_terms": True
    }
    
    response = client.post("/register", data=data)
    # Should redirect back to register
    assert response.status_code == 200 # It follows redirects by default? No, usually testclient follows redirects unless parameterized
    # Ah, if I don't set follow_redirects=False, it might follow. 
    # Let's check the previous test. I set follow_redirects=False there.
    # Default behavior for TestClient is follow_redirects=True.
    
    # If it redirects back to register, we should see the page content
    assert "Passwords do not match" in response.text

def test_login_success(client: TestClient, test_user):
    # We need to create a user with a Known password first.
    # The 'test_user' fixture creates one with 'hashed_secret', which might not be valid for login
    # if the login function re-hashes the input.
    # Let's create a fresh user via the register route or manually using the hashing util?
    # Better: Use the register function from auth module or just modify test_user fixture?
    # The 'login' function verifies password.
    # Let's just create a new user via API for this test to be safe & integration-style.
    
    # Register first
    with patch("web.routes.auth.send_welcome_email") as mock_email:
        mock_email.return_value = {"success": True}
        client.post("/register", data={
            "email": "login@test.com",
            "password": "LoginPass123",
            "password_confirm": "LoginPass123",
            "full_name": "Login User",
            "agree_terms": True
        })
    
    # Now login
    response = client.post("/login", data={
        "email": "login@test.com",
        "password": "LoginPass123"
    }, follow_redirects=False)
    
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "access_token" in response.cookies

def test_login_failure(client: TestClient):
    response = client.post("/login", data={
        "email": "nonexistent@test.com",
        "password": "wrong"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "Invalid email or password" in response.text

def test_logout(client: TestClient):
    # Login first (set cookie manually or via login)
    # Let's just manually set a cookie
    client.cookies.set("access_token", "fake_token")
    
    response = client.post("/logout", follow_redirects=False)
    
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    # Check cookie is cleared/expired (TestClient handles this by updating cookies)
    # Note: TestClient.cookies might still have it if max-age=0, but we can check the Set-Cookie header
    assert 'access_token=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]
