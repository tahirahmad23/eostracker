
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient
from main import app
from database.connection import Base, get_db
from database.models import User
from auth import create_access_token
import os
from unittest.mock import patch, MagicMock

# Mock scheduler before importing main
patch('alerts.scheduler.start_scheduler').start()
patch('alerts.scheduler.stop_scheduler').start()


# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Create tables once for the test session and drop them after.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database session for each test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    """
    FastAPI TestClient with overridden database dependency.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    """
    Create a test user.
    """
    user = User(
        email="test@example.com",
        hashed_password="hashed_secret", # In real auth tests we might use proper hashing
        full_name="Test User",
        tier="free",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_user_token(test_user):
    """
    Create a valid access token for the test user.
    """
    return create_access_token(user_id=test_user.id)

@pytest.fixture
def auth_headers(test_user_token):
    """
    Authorization headers for the test user.
    """
    return {"Cookie": f"access_token={test_user_token}"}
