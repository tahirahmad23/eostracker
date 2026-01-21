"""
Comprehensive test suite for authentication module.

Tests cover:
- User registration (success, validation, duplicates)
- Login (success, invalid credentials, inactive users)
- Password hashing and verification
- JWT token creation and validation
- Token refresh flow
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from database.models import Base, User, UserTier
from auth.service import register, login, validate_token, refresh_tokens
from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    extract_user_id,
    JWT_SECRET,
    JWT_ALGORITHM
)


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


# ===== PASSWORD HASHING TESTS =====

def test_hash_password():
    """Test password hashing produces valid bcrypt hash."""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    # Bcrypt hashes start with $2b$
    assert hashed.startswith("$2b$")
    # Hash should be different from plain password
    assert hashed != password
    # Hash should be consistent length (60 chars for bcrypt)
    assert len(hashed) == 60


def test_hash_password_different_for_same_input():
    """Test that same password produces different hashes (salt is random)."""
    password = "SecurePassword123!"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    # Hashes should be different due to random salt
    assert hash1 != hash2
    # But both should verify correctly
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)


def test_verify_password_correct():
    """Test password verification with correct password."""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test password verification with wrong password."""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password("WrongPassword", hashed) is False


# ===== JWT TOKEN TESTS =====

def test_create_access_token():
    """Test access token creation."""
    user_id = 123
    token = create_access_token(user_id)
    
    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 50
    
    # Decode and verify payload
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_create_refresh_token():
    """Test refresh token creation."""
    user_id = 456
    token = create_refresh_token(user_id)
    
    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 50
    
    # Decode and verify payload
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


def test_decode_valid_token():
    """Test decoding a valid token."""
    user_id = 789
    token = create_access_token(user_id)
    payload = decode_token(token)
    
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert "exp" in payload


def test_decode_invalid_token():
    """Test decoding an invalid token returns None."""
    invalid_token = "invalid.token.here"
    payload = decode_token(invalid_token)
    
    assert payload is None


def test_decode_expired_token():
    """Test decoding an expired token returns None."""
    user_id = 999
    # Create token that expired 1 hour ago
    expire = datetime.utcnow() - timedelta(hours=1)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access"
    }
    expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    decoded = decode_token(expired_token)
    assert decoded is None


def test_extract_user_id_from_token():
    """Test extracting user ID from valid token."""
    user_id = 555
    token = create_access_token(user_id)
    extracted_id = extract_user_id(token)
    
    assert extracted_id == user_id


def test_extract_user_id_from_invalid_token():
    """Test extracting user ID from invalid token returns None."""
    invalid_token = "invalid.token.here"
    extracted_id = extract_user_id(invalid_token)
    
    assert extracted_id is None


# ===== REGISTRATION TESTS =====

def test_register_success(db_session):
    """Test successful user registration."""
    result = register(
        email="newuser@example.com",
        password="SecurePass123!",
        full_name="New User",
        db=db_session
    )
    
    assert result["success"] is True
    assert "data" in result
    
    # Check user data
    user_data = result["data"]["user"]
    assert user_data["email"] == "newuser@example.com"
    assert user_data["full_name"] == "New User"
    assert user_data["tier"] == "free"
    assert user_data["is_active"] is True
    assert "id" in user_data
    
    # Check tokens
    assert "access_token" in result["data"]
    assert "refresh_token" in result["data"]
    assert len(result["data"]["access_token"]) > 50


def test_register_email_normalization(db_session):
    """Test email is normalized to lowercase."""
    result = register(
        email="UPPERCASE@EXAMPLE.COM",
        password="SecurePass123!",
        full_name="User",
        db=db_session
    )
    
    assert result["success"] is True
    assert result["data"]["user"]["email"] == "uppercase@example.com"


def test_register_invalid_email(db_session):
    """Test registration fails with invalid email format."""
    result = register(
        email="not-an-email",
        password="SecurePass123!",
        full_name="User",
        db=db_session
    )
    
    assert result["success"] is False
    assert "invalid email" in result["error"].lower()


def test_register_duplicate_email(db_session):
    """Test registration fails with duplicate email."""
    # Register first user
    register(
        email="duplicate@example.com",
        password="Pass123!",
        full_name="First User",
        db=db_session
    )
    
    # Try to register with same email
    result = register(
        email="duplicate@example.com",
        password="DifferentPass123!",
        full_name="Second User",
        db=db_session
    )
    
    assert result["success"] is False
    assert "already registered" in result["error"].lower()


def test_register_weak_password_too_short(db_session):
    """Test registration fails with password too short."""
    result = register(
        email="user@example.com",
        password="Short1",
        full_name="User",
        db=db_session
    )
    
    assert result["success"] is False
    assert "8 characters" in result["error"]


def test_register_weak_password_no_uppercase(db_session):
    """Test registration fails with no uppercase letter."""
    result = register(
        email="user@example.com",
        password="lowercase123",
        full_name="User",
        db=db_session
    )
    
    assert result["success"] is False
    assert "uppercase" in result["error"].lower()


def test_register_weak_password_no_number(db_session):
    """Test registration fails with no number."""
    result = register(
        email="user@example.com",
        password="NoNumberHere",
        full_name="User",
        db=db_session
    )
    
    assert result["success"] is False
    assert "number" in result["error"].lower()


def test_register_password_hashed_in_db(db_session):
    """Test password is hashed in database, not stored plaintext."""
    password = "SecurePass123!"
    result = register(
        email="user@example.com",
        password=password,
        full_name="User",
        db=db_session
    )
    
    assert result["success"] is True
    
    # Get user from database
    user = db_session.query(User).filter(User.email == "user@example.com").first()
    
    # Password should be hashed (bcrypt hash starts with $2b$)
    assert user.hashed_password.startswith("$2b$")
    assert user.hashed_password != password


# ===== LOGIN TESTS =====

def test_login_success(db_session):
    """Test successful login with correct credentials."""
    # Register user first
    email = "loginuser@example.com"
    password = "SecurePass123!"
    register(email, password, "Login User", db=db_session)
    
    # Login
    result = login(email, password, db=db_session)
    
    assert result["success"] is True
    assert "data" in result
    
    # Check user data
    user_data = result["data"]["user"]
    assert user_data["email"] == email
    assert user_data["full_name"] == "Login User"
    
    # Check tokens
    assert "access_token" in result["data"]
    assert "refresh_token" in result["data"]


def test_login_wrong_password(db_session):
    """Test login fails with wrong password."""
    # Register user
    email = "user@example.com"
    register(email, "CorrectPass123!", "User", db=db_session)
    
    # Login with wrong password
    result = login(email, "WrongPass123!", db=db_session)
    
    assert result["success"] is False
    assert "invalid email or password" in result["error"].lower()


def test_login_nonexistent_email(db_session):
    """Test login fails with non-existent email."""
    result = login(
        "nonexistent@example.com",
        "SomePass123!",
        db=db_session
    )
    
    assert result["success"] is False
    assert "invalid email or password" in result["error"].lower()


def test_login_inactive_user(db_session):
    """Test login fails for inactive user."""
    # Register user
    email = "inactive@example.com"
    register(email, "Pass123!", "User", db=db_session)
    
    # Deactivate user
    user = db_session.query(User).filter(User.email == email).first()
    user.is_active = False
    db_session.commit()
    
    # Try to login
    result = login(email, "Pass123!", db=db_session)
    
    assert result["success"] is False
    assert "disabled" in result["error"].lower()


def test_login_email_case_insensitive(db_session):
    """Test login works with different email case."""
    # Register with lowercase
    register("user@example.com", "Pass123!", "User", db=db_session)
    
    # Login with uppercase
    result = login("USER@EXAMPLE.COM", "Pass123!", db=db_session)
    
    assert result["success"] is True


# ===== TOKEN VALIDATION TESTS =====

def test_validate_token_success(db_session):
    """Test successful token validation."""
    # Register user
    reg_result = register(
        "user@example.com",
        "Pass123!",
        "User",
        db=db_session
    )
    
    token = reg_result["data"]["access_token"]
    user_id = reg_result["data"]["user"]["id"]
    
    # Validate token
    result = validate_token(token, db=db_session)
    
    assert result["success"] is True
    assert result["data"] == user_id


def test_validate_token_invalid(db_session):
    """Test validation fails with invalid token."""
    result = validate_token("invalid.token.here", db=db_session)
    
    assert result["success"] is False
    assert "invalid or expired" in result["error"].lower()


def test_validate_token_wrong_type(db_session):
    """Test validation fails with refresh token instead of access token."""
    # Register user
    reg_result = register(
        "user@example.com",
        "Pass123!",
        "User",
        db=db_session
    )
    
    refresh_token = reg_result["data"]["refresh_token"]
    
    # Try to validate refresh token as access token
    result = validate_token(refresh_token, db=db_session)
    
    assert result["success"] is False
    assert "invalid token type" in result["error"].lower()


def test_validate_token_user_not_found(db_session):
    """Test validation fails when user doesn't exist."""
    # Create token for non-existent user
    token = create_access_token(99999)
    
    result = validate_token(token, db=db_session)
    
    assert result["success"] is False
    assert "user not found" in result["error"].lower()


def test_validate_token_inactive_user(db_session):
    """Test validation fails for inactive user."""
    # Register user
    reg_result = register(
        "user@example.com",
        "Pass123!",
        "User",
        db=db_session
    )
    
    token = reg_result["data"]["access_token"]
    
    # Deactivate user
    user = db_session.query(User).filter(
        User.email == "user@example.com"
    ).first()
    user.is_active = False
    db_session.commit()
    
    # Try to validate token
    result = validate_token(token, db=db_session)
    
    assert result["success"] is False
    assert "disabled" in result["error"].lower()


# ===== REFRESH TOKEN TESTS =====

def test_refresh_tokens_success(db_session):
    """Test successful token refresh."""
    # Register user
    reg_result = register(
        "user@example.com",
        "Pass123!",
        "User",
        db=db_session
    )
    
    old_refresh_token = reg_result["data"]["refresh_token"]
    
    # Refresh tokens
    result = refresh_tokens(old_refresh_token, db=db_session)
    assert result["success"] is True
    assert "access_token" in result["data"]
    assert "refresh_token" in result["data"]
    
    # New tokens should be different from old ones
    assert result["data"]["refresh_token"] != old_refresh_token


def test_refresh_tokens_invalid(db_session):
    """Test refresh fails with invalid token."""
    result = refresh_tokens("invalid.token.here", db=db_session)
    
    assert result["success"] is False
    assert "invalid or expired" in result["error"].lower()


def test_refresh_tokens_wrong_type(db_session):
    """Test refresh fails with access token instead of refresh token."""
    # Register user
    reg_result = register(
        "user@example.com",
        "Pass123!",
        "User",
        db=db_session
    )
    
    access_token = reg_result["data"]["access_token"]
    
    # Try to use access token for refresh
    result = refresh_tokens(access_token, db=db_session)
    
    assert result["success"] is False
    assert "invalid token type" in result["error"].lower()


def test_refresh_tokens_inactive_user(db_session):
    """Test refresh fails for inactive user."""
    # Register user
    reg_result = register(
        "user@example.com",
        "Pass123!",
        "User",
        db=db_session
    )
    
    refresh_token = reg_result["data"]["refresh_token"]
    
    # Deactivate user
    user = db_session.query(User).filter(
        User.email == "user@example.com"
    ).first()
    user.is_active = False
    db_session.commit()
    
    # Try to refresh
    result = refresh_tokens(refresh_token, db=db_session)
    
    assert result["success"] is False
    assert "disabled" in result["error"].lower()


# ===== INTEGRATION TESTS =====

def test_full_auth_flow(db_session):
    """Test complete authentication flow: register -> login -> validate -> refresh."""
    # 1. Register
    reg_result = register(
        "flowtest@example.com",
        "SecurePass123!",
        "Flow Test User",
        db=db_session
    )
    assert reg_result["success"] is True
    
    # 2. Login
    login_result = login(
        "flowtest@example.com",
        "SecurePass123!",
        db=db_session
    )
    assert login_result["success"] is True
    
    # 3. Validate access token
    access_token = login_result["data"]["access_token"]
    validate_result = validate_token(access_token, db=db_session)
    assert validate_result["success"] is True
    
    # 4. Refresh tokens
    refresh_token = login_result["data"]["refresh_token"]
    refresh_result = refresh_tokens(refresh_token, db=db_session)
    assert refresh_result["success"] is True
    
    # 5. Validate new access token
    new_access_token = refresh_result["data"]["access_token"]
    final_validate = validate_token(new_access_token, db=db_session)
    assert final_validate["success"] is True
