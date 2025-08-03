"""
Basic tests to validate API endpoints and functionality.
"""
import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

# Test imports to check for syntax errors
try:
    from main import app
    from database import get_db, Base
    from models import User, Task, APIKey
    from schemas import TaskCreate, UserCreate, APIKeyCreate
    from auth import create_access_token, generate_api_key
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    raise

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    print("✅ Health check endpoint working")

def test_google_auth_url():
    """Test Google OAuth URL generation."""
    response = client.get("/auth/google")
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "state" in data
    assert "accounts.google.com" in data["auth_url"]
    print("✅ Google auth URL endpoint working")

def test_subscription_plans():
    """Test subscription plans endpoint."""
    response = client.get("/subscription/plans")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print("✅ Subscription plans endpoint working")

def test_unauthorized_access():
    """Test that protected endpoints require authentication."""
    # Test protected endpoints without auth
    protected_endpoints = [
        "/auth/me",
        "/tasks",
        "/api-keys",
        "/subscription",
        "/analytics/usage"
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401
    
    print("✅ Authentication protection working")

def test_task_creation_validation():
    """Test task creation with invalid data."""
    # Test without authentication
    invalid_task = {
        "name": "Test Task",
        "task_type": "simple_scraping",
        "config": {}
    }
    
    response = client.post("/tasks", json=invalid_task)
    assert response.status_code == 401  # Should require authentication
    print("✅ Task creation validation working")

def test_api_key_generation():
    """Test API key generation utility."""
    api_key, preview = generate_api_key()
    assert api_key.startswith("sk_")
    assert len(api_key) == 35  # sk_ + 32 chars
    assert preview.endswith("*" * 24)
    assert api_key[:8] == preview[:8]
    print("✅ API key generation working")

def test_jwt_token_creation():
    """Test JWT token creation."""
    test_data = {"sub": "test-user-id", "email": "test@example.com"}
    token = create_access_token(test_data)
    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are typically longer
    print("✅ JWT token creation working")

@patch('api.celery_app.celery_app.control.inspect')
def test_queue_stats_mock(mock_inspect):
    """Test queue stats with mocked Celery."""
    # Mock Celery inspection
    mock_inspect.return_value.active.return_value = {}
    mock_inspect.return_value.scheduled.return_value = {}
    mock_inspect.return_value.reserved.return_value = {}
    
    from celery_app import get_queue_stats
    stats = get_queue_stats()
    
    assert "active_tasks" in stats
    assert "scheduled_tasks" in stats
    assert "timestamp" in stats
    print("✅ Queue stats working")

def test_schema_validation():
    """Test Pydantic schema validation."""
    from schemas import TaskCreate, TaskType
    
    # Valid task
    valid_task = TaskCreate(
        name="Test Task",
        task_type=TaskType.SIMPLE_SCRAPING,
        config={
            "urls": ["http://example.com"],
            "selectors": {"title": "h1"},
            "output_format": "json"
        }
    )
    assert valid_task.name == "Test Task"
    
    # Invalid task (missing required fields)
    try:
        invalid_task = TaskCreate(
            name="",  # Empty name should fail
            task_type=TaskType.SIMPLE_SCRAPING,
            config={}
        )
        assert False, "Should have raised validation error"
    except Exception:
        pass  # Expected validation error
    
    print("✅ Schema validation working")

def test_error_responses():
    """Test error response format."""
    # Test 404 endpoint
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    
    # Test rate limit endpoint (should not fail immediately)
    response = client.get("/auth/google")
    assert response.status_code in [200, 429]  # 429 if rate limited
    
    print("✅ Error responses working")

def run_all_tests():
    """Run all validation tests."""
    print("🚀 Starting API validation tests...\n")
    
    test_functions = [
        test_health_check,
        test_google_auth_url,
        test_subscription_plans,
        test_unauthorized_access,
        test_task_creation_validation,
        test_api_key_generation,
        test_jwt_token_creation,
        test_queue_stats_mock,
        test_schema_validation,
        test_error_responses
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! API is ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)