# Selextract Cloud Developer Guide

This guide provides comprehensive information for developers working on Selextract Cloud, including architecture overview, local development setup, and contribution guidelines.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [🔥 Hot Reload Development Setup](#hot-reload-development-setup)
- [Local Development Setup](#local-development-setup)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Database Development](#database-development)
- [API Development](#api-development)
- [Frontend Development](#frontend-development)
- [Worker Development](#worker-development)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Contribution Guidelines](#contribution-guidelines)
- [Performance Considerations](#performance-considerations)
- [Security Guidelines](#security-guidelines)

---

## Architecture Overview

### System Architecture

Selextract Cloud follows a microservices architecture designed for single-server deployment with clear scaling paths.

```
┌─────────────────────────────────────────────────────────────┐
│                    Selextract Cloud Architecture             │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js)  │  API (FastAPI)  │  Workers (Celery)  │
│  ┌─────────────────┐ │ ┌─────────────┐ │ ┌─────────────────┐ │
│  │ React Components│ │ │ REST API    │ │ │ Playwright      │ │
│  │ Authentication  │ │ │ JWT Auth    │ │ │ Selenium        │ │
│  │ Task Management │ │ │ Billing     │ │ │ Proxy Management│ │
│  │ Dashboard       │ │ │ Webhooks    │ │ │ Task Processing │ │
│  └─────────────────┘ │ └─────────────┘ │ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                         Nginx (Reverse Proxy)               │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL         │  Redis          │  Monitoring         │
│  ┌─────────────┐    │ ┌─────────────┐ │ ┌─────────────────┐ │
│  │ Users       │    │ │ Sessions    │ │ │ Prometheus      │ │
│  │ Tasks       │    │ │ Queue       │ │ │ Grafana         │ │
│  │ Billing     │    │ │ Cache       │ │ │ Alertmanager    │ │
│  │ Metrics     │    │ │ Rate Limits │ │ │ Loki            │ │
│  └─────────────┘    │ └─────────────┘ │ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. API Layer (`/api`)
- **Framework:** FastAPI with Python 3.11+
- **Authentication:** JWT tokens with Google OAuth integration
- **Database ORM:** SQLAlchemy with Alembic migrations
- **Billing:** Lemon Squeezy integration
- **Documentation:** Auto-generated OpenAPI/Swagger

#### 2. Frontend (`/frontend`)
- **Framework:** Next.js 13+ with TypeScript
- **Styling:** Tailwind CSS
- **Authentication:** NextAuth.js
- **State Management:** React hooks and context
- **Build Target:** Static export for production

#### 3. Worker Layer (`/worker`)
- **Task Queue:** Celery with Redis broker
- **Browser Automation:** Playwright (primary), Selenium (fallback)
- **Proxy Management:** Webshare.io integration
- **Task Processing:** Async/concurrent execution

#### 4. Data Layer
- **Primary Database:** PostgreSQL 15+
- **Cache/Queue:** Redis 7+
- **File Storage:** Local filesystem (MinIO for scaling)
- **Monitoring Data:** Prometheus TSDB

#### 5. Infrastructure
- **Reverse Proxy:** Nginx with SSL termination
- **Containerization:** Docker with Docker Compose
- **Monitoring:** Prometheus + Grafana + Alertmanager
- **Logging:** Structured JSON logging with Loki

### Data Flow

```
1. User Request → Nginx → Frontend (Next.js)
2. API Call → Nginx → API (FastAPI) → Database (PostgreSQL)
3. Task Creation → API → Redis Queue → Worker (Celery)
4. Task Execution → Worker → Target Websites (via Proxies)
5. Results Storage → Worker → Database → API → Frontend
6. Monitoring → All Services → Prometheus → Grafana
```

### Security Architecture

- **External Traffic:** HTTPS only with automatic HTTP redirect
- **Internal Communication:** Docker network isolation
- **Authentication:** Multi-factor with OAuth and JWT
- **Data Protection:** AES encryption for sensitive data
- **API Security:** Rate limiting, input validation, CORS policies
- **Infrastructure:** Firewall, fail2ban, regular security updates

---

## 🔥 Hot Reload Development Setup

### Quick Start (5 Minutes)

For instant hot reloading development with 94% faster iteration cycles, use the new hybrid development environment:

```bash
# 1. Quick setup and launch
cd dev && ./quick-start.sh

# 2. Start API (Terminal 1)
./start-api.sh

# 3. Start Frontend (Terminal 2)
./start-frontend.sh
```

**Benefits:**
- **API Changes**: ~2 seconds (vs ~50 seconds with Docker)
- **Frontend Changes**: ~0.5 seconds (vs ~40 seconds with Docker)
- **No Docker rebuilds** during development

### Detailed Setup

For comprehensive setup with all validations and cross-platform support:

```bash
# 1. Run full setup with prerequisite checking
cd dev && ./setup-dev.sh

# 2. Use VS Code integration
# Ctrl+Shift+P → "Tasks: Run Task" → Select task
```

### Architecture

The hot reload setup uses a **hybrid architecture**:
- **Native Hot Reloading**: FastAPI and Next.js run natively with hot reload
- **Containerized Infrastructure**: PostgreSQL, Redis, and Celery Worker run in Docker
- **Localhost Connectivity**: Native services connect to containerized infrastructure

### Documentation

- **Quick Guide**: [`QUICK_START_HOT_RELOAD.md`](QUICK_START_HOT_RELOAD.md) - 5-minute setup
- **Comprehensive Plan**: [`FINAL_HOT_RELOAD_DEVELOPMENT_PLAN.md`](FINAL_HOT_RELOAD_DEVELOPMENT_PLAN.md) - Expert-validated implementation

### VS Code Integration

The setup includes complete VS Code integration:
- **Tasks**: One-click start for API and Frontend
- **Debug Configurations**: Full-stack debugging with breakpoints
- **Settings**: Optimized for Python and TypeScript development

---

## Local Development Setup

### Prerequisites

- **Docker Desktop:** Latest version with Compose V2
- **Git:** For version control
- **Code Editor:** VSCode recommended with extensions
- **Node.js:** 18+ (for frontend development)
- **Python:** 3.11+ (for API development)

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/selextract-cloud.git
cd selextract-cloud

# 2. Copy environment configuration
cp .env.example .env

# 3. Generate development secrets
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))" >> .env
python -c "import secrets; print('NEXTAUTH_SECRET=' + secrets.token_urlsafe(64))" >> .env

# 4. Start development environment
docker-compose up -d

# 5. Run database migrations
docker-compose exec api alembic upgrade head

# 6. Create test user (optional)
docker-compose exec api python -c "
from api.database import get_db
from api.models import User
from sqlalchemy.orm import Session
db = next(get_db())
user = User(email='dev@selextract.com', name='Developer')
db.add(user)
db.commit()
print('Test user created')
"
```

### Development Environment Variables

Update `.env` with these development-specific values:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/selextract_dev
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
LOG_LEVEL=DEBUG

# Frontend Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_dev_secret_here

# Development OAuth (create test app in Google Console)
GOOGLE_CLIENT_ID=your_dev_client_id
GOOGLE_CLIENT_SECRET=your_dev_client_secret

# Development API Keys (use test/sandbox accounts)
WEBSHARE_API_KEY=test_key_or_empty_for_mock
LEMON_SQUEEZY_API_KEY=test_key_or_empty_for_mock

# Worker Configuration
CELERY_WORKER_CONCURRENCY=2
CELERY_TASK_TIMEOUT=300

# Monitoring (optional for development)
ENABLE_METRICS=true
METRICS_PORT=8001
```

### Service Access

After starting the development environment:

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Grafana:** http://localhost:3001 (admin/admin)
- **Prometheus:** http://localhost:9090
- **Redis:** localhost:6379
- **PostgreSQL:** localhost:5432

### IDE Setup (VSCode)

Recommended extensions:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.pylint",
    "ms-python.black-formatter",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode-remote.remote-containers",
    "ms-vscode.docker"
  ]
}
```

Development settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "./api/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

---

## Development Workflow

### Branch Strategy

```
main
├── develop
│   ├── feature/task-management
│   ├── feature/billing-integration
│   └── feature/monitoring-dashboard
├── hotfix/security-patch
└── release/v1.2.0
```

### Commit Convention

Use Conventional Commits format:

```bash
# Features
git commit -m "feat(api): add task scheduling endpoint"
git commit -m "feat(frontend): implement dashboard charts"

# Bug fixes
git commit -m "fix(worker): resolve proxy rotation issue"
git commit -m "fix(auth): handle token expiration gracefully"

# Documentation
git commit -m "docs: update API reference for v1.2"

# Refactoring
git commit -m "refactor(database): optimize query performance"

# Tests
git commit -m "test(api): add integration tests for billing"

# CI/CD
git commit -m "ci: add automated security scanning"

# Chores
git commit -m "chore: update dependencies to latest versions"
```

### Development Process

1. **Create Feature Branch:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

2. **Make Changes:**
```bash
# Edit code
# Add tests
# Update documentation
```

3. **Test Locally:**
```bash
# Run unit tests
docker-compose exec api pytest
docker-compose exec frontend npm test

# Run integration tests
./scripts/test-integration.sh

# Check code quality
docker-compose exec api black --check .
docker-compose exec api pylint api/
docker-compose exec frontend npm run lint
```

4. **Commit and Push:**
```bash
git add .
git commit -m "feat(component): description of changes"
git push origin feature/your-feature-name
```

5. **Create Pull Request:**
- Target: `develop` branch
- Include: description, testing notes, breaking changes
- Ensure: all CI checks pass

### Code Review Checklist

**General:**
- [ ] Code follows project conventions
- [ ] Commit messages follow conventional format
- [ ] No sensitive data in code
- [ ] Documentation updated if needed

**Backend (API/Worker):**
- [ ] Type hints included
- [ ] Error handling implemented
- [ ] SQL injection prevention
- [ ] Input validation added
- [ ] Tests cover new functionality

**Frontend:**
- [ ] TypeScript types defined
- [ ] Responsive design tested
- [ ] Accessibility considered
- [ ] Performance optimized
- [ ] Error boundaries implemented

**Database:**
- [ ] Migrations are reversible
- [ ] Indexes added where needed
- [ ] Foreign key constraints defined
- [ ] Data validation at DB level

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/
│   ├── api/
│   │   ├── test_auth.py
│   │   ├── test_billing.py
│   │   └── test_tasks.py
│   ├── worker/
│   │   ├── test_proxies.py
│   │   └── test_task_execution.py
│   └── frontend/
│       ├── components/
│       └── pages/
├── integration/
│   ├── test_api_worker_flow.py
│   ├── test_auth_flow.py
│   └── test_billing_webhooks.py
├── e2e/
│   ├── test_user_journey.py
│   └── test_task_lifecycle.py
└── load/
    ├── locustfile.py
    ├── k6-load-tests.js
    └── artillery-tests.yml
```

### Running Tests

```bash
# Unit tests
docker-compose exec api pytest tests/unit/ -v
docker-compose exec frontend npm test

# Integration tests
docker-compose exec api pytest tests/integration/ -v

# End-to-end tests
python tests/e2e/test_user_journey.py

# Load tests
cd tests/load
locust -f locustfile.py --host=http://localhost:8000

# Test coverage
docker-compose exec api pytest --cov=api --cov-report=html
```

### Writing Tests

#### API Tests (Python/pytest)

```python
# tests/unit/api/test_tasks.py
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.models import Task, User
from api.database import get_db

client = TestClient(app)

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(email="test@example.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user

def test_create_task(test_user, auth_headers):
    """Test task creation endpoint."""
    task_data = {
        "name": "Test Task",
        "task_type": "simple_scraping",
        "config": {
            "urls": ["https://example.com"],
            "selectors": {"title": "h1"}
        }
    }
    
    response = client.post(
        "/api/v1/tasks",
        json=task_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Task"
    assert data["status"] == "PENDING"

def test_task_validation_error():
    """Test task creation with invalid data."""
    response = client.post(
        "/api/v1/tasks",
        json={"invalid": "data"}
    )
    
    assert response.status_code == 422
```

#### Frontend Tests (Jest/React Testing Library)

```typescript
// tests/unit/frontend/components/TaskStatus.test.tsx
import { render, screen } from '@testing-library/react';
import { TaskStatus } from '@/components/TaskStatus';

describe('TaskStatus Component', () => {
  it('displays pending status correctly', () => {
    render(<TaskStatus status="PENDING" />);
    
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByTestId('status-icon')).toHaveClass('text-yellow-500');
  });

  it('displays completed status correctly', () => {
    render(<TaskStatus status="COMPLETED" />);
    
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByTestId('status-icon')).toHaveClass('text-green-500');
  });

  it('displays failed status correctly', () => {
    render(<TaskStatus status="FAILED" />);
    
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByTestId('status-icon')).toHaveClass('text-red-500');
  });
});
```

#### Worker Tests (Python/pytest)

```python
# tests/unit/worker/test_task_execution.py
import pytest
from unittest.mock import Mock, patch
from worker.tasks import scrape_task
from worker.proxies import ProxyManager

@pytest.fixture
def mock_browser():
    """Mock Playwright browser."""
    browser = Mock()
    page = Mock()
    browser.new_page.return_value = page
    return browser, page

def test_scrape_task_success(mock_browser):
    """Test successful task execution."""
    browser, page = mock_browser
    page.goto.return_value = None
    page.locator.return_value.text_content.return_value = "Test Title"
    
    with patch('worker.tasks.playwright') as mock_playwright:
        mock_playwright.chromium.launch.return_value = browser
        
        result = scrape_task("task_123")
        
        assert result["status"] == "COMPLETED"
        assert "Test Title" in result["data"]

def test_proxy_rotation():
    """Test proxy rotation logic."""
    proxy_manager = ProxyManager()
    
    # Mock API response
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [
                {"proxy_address": "1.1.1.1", "port": 8000},
                {"proxy_address": "2.2.2.2", "port": 8000}
            ]
        }
        
        proxies = proxy_manager.get_working_proxies()
        assert len(proxies) == 2
        
        # Test rotation
        proxy1 = proxy_manager.get_random_proxy()
        proxy2 = proxy_manager.get_random_proxy()
        # Should potentially be different due to rotation
```

### Test Data Management

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.database import Base, get_db
from api.main import app

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    return create_engine("sqlite:///./test.db")

@pytest.fixture(scope="session")
def test_db(test_engine):
    """Create test database."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session(test_engine, test_db):
    """Create database session for tests."""
    TestingSessionLocal = sessionmaker(bind=test_engine)
    session = TestingSessionLocal()
    
    # Override dependency
    def override_get_db():
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers for testing."""
    from api.auth import create_access_token
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}
```

---

## Database Development

### Database Schema

The database follows a normalized design with clear relationships:

```sql
-- Core Tables
Users (id, email, name, created_at, subscription_status)
Tasks (id, user_id, name, type, config, status, result, created_at, updated_at)
Billing (id, user_id, plan, status, amount, period_start, period_end)

-- Supporting Tables
Task_Executions (id, task_id, worker_id, started_at, completed_at, error_details)
User_Sessions (id, user_id, token, created_at, expires_at)
System_Metrics (id, metric_name, value, timestamp)

-- Indexes
idx_tasks_user_id, idx_tasks_status, idx_tasks_created_at
idx_billing_user_id, idx_sessions_token
```

### Migration Management

```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "add user preferences table"

# Apply migrations
docker-compose exec api alembic upgrade head

# Downgrade one revision
docker-compose exec api alembic downgrade -1

# Check current revision
docker-compose exec api alembic current

# Show migration history
docker-compose exec api alembic history --verbose
```

### Database Models

```python
# api/models.py example
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="user")
    billing = relationship("Billing", back_populates="user")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    status = Column(String, default="PENDING", index=True)
    result = Column(Text)
    error_details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
```

### Query Optimization

```python
# Efficient querying patterns
from sqlalchemy.orm import joinedload, selectinload

# Use eager loading for relationships
tasks = session.query(Task)\
    .options(joinedload(Task.user))\
    .filter(Task.status == "COMPLETED")\
    .limit(100)\
    .all()

# Use select loading for collections
users = session.query(User)\
    .options(selectinload(User.tasks))\
    .filter(User.created_at > datetime.now() - timedelta(days=30))\
    .all()

# Efficient counting
task_count = session.query(Task)\
    .filter(Task.user_id == user_id)\
    .count()

# Raw SQL for complex queries
result = session.execute(text("""
    SELECT DATE(created_at) as date, COUNT(*) as task_count
    FROM tasks 
    WHERE created_at >= :start_date
    GROUP BY DATE(created_at)
    ORDER BY date DESC
"""), {"start_date": start_date}).fetchall()
```

---

## API Development

### API Structure

```
api/
├── __init__.py
├── main.py              # FastAPI app and routes
├── auth.py              # Authentication logic
├── billing.py           # Billing endpoints
├── database.py          # Database connection
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── compute_units.py     # Usage tracking
├── metrics.py           # Prometheus metrics
├── webhooks.py          # External webhook handlers
└── requirements.txt     # Python dependencies
```

### Adding New Endpoints

1. **Define Pydantic Schema:**

```python
# api/schemas.py
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class TaskCreate(BaseModel):
    name: str
    task_type: str
    config: dict
    
    @validator('task_type')
    def validate_task_type(cls, v):
        allowed_types = ['simple_scraping', 'advanced_scraping', 'monitoring']
        if v not in allowed_types:
            raise ValueError(f'task_type must be one of {allowed_types}')
        return v

class TaskResponse(BaseModel):
    id: int
    name: str
    task_type: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # For SQLAlchemy models
```

2. **Create Database Model:**

```python
# api/models.py
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # ... other fields
```

3. **Implement Endpoint:**

```python
# api/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .auth import get_current_user
from .schemas import TaskCreate, TaskResponse
from .models import Task

@app.post("/api/v1/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task for the current user."""
    
    # Validate user has sufficient compute units
    if not current_user.has_sufficient_compute_units(task.estimated_cost):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient compute units"
        )
    
    # Create task
    db_task = Task(
        name=task.name,
        task_type=task.task_type,
        config=task.config,
        user_id=current_user.id
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Queue task for processing
    from worker.tasks import scrape_task
    scrape_task.delay(db_task.id)
    
    return db_task
```

### Authentication Implementation

```python
# api/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user
```

### Error Handling

```python
# api/main.py
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "message": "Invalid input data"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

# Custom exceptions
class InsufficientComputeUnitsError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=402,
            detail="Insufficient compute units to process this task"
        )

class TaskNotFoundError(HTTPException):
    def __init__(self, task_id: int):
        super().__init__(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
```

### Input Validation

```python
# api/schemas.py
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Any, Optional
import re

class URLValidator:
    @classmethod
    def validate_url(cls, url: str) -> str:
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            raise ValueError('Invalid URL format')
        return url

class SelectorValidator:
    @classmethod
    def validate_css_selector(cls, selector: str) -> str:
        # Basic CSS selector validation
        if not selector or len(selector.strip()) == 0:
            raise ValueError('Selector cannot be empty')
        if len(selector) > 500:
            raise ValueError('Selector too long')
        return selector.strip()

class TaskConfigSchema(BaseModel):
    urls: List[str] = Field(..., min_items=1, max_items=100)
    selectors: Dict[str, str] = Field(..., min_items=1)
    output_format: str = Field(default="json", regex="^(json|csv|xml)$")
    wait_time: Optional[int] = Field(default=5, ge=1, le=60)
    
    @validator('urls', each_item=True)
    def validate_urls(cls, v):
        return URLValidator.validate_url(v)
    
    @validator('selectors')
    def validate_selectors(cls, v):
        for key, selector in v.items():
            SelectorValidator.validate_css_selector(selector)
        return v
```

---

## Frontend Development

### Frontend Structure

```
frontend/
├── components/          # Reusable React components
│   ├── Navbar.tsx
│   ├── TaskStatus.tsx
│   ├── DashboardStats.tsx
│   └── RecentTasksTable.tsx
├── pages/              # Next.js pages (file-based routing)
│   ├── _app.tsx        # App wrapper
│   ├── index.tsx       # Landing page
│   ├── login.tsx       # Login page
│   ├── dashboard.tsx   # Main dashboard
│   └── api/           # API routes
├── lib/               # Utility libraries
│   ├── api.ts         # API client
│   └── auth.tsx       # Authentication context
├── styles/            # CSS styles
│   └── globals.css    # Global styles with Tailwind
├── types/             # TypeScript type definitions
│   ├── api.ts         # API response types
│   └── auth.ts        # Authentication types
└── public/            # Static assets
```

### Component Development

```typescript
// components/TaskStatus.tsx
import React from 'react';
import { Task } from '@/types/api';

interface TaskStatusProps {
  status: Task['status'];
  className?: string;
}

export const TaskStatus: React.FC<TaskStatusProps> = ({ status, className = '' }) => {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'PENDING':
        return { color: 'text-yellow-600', bg: 'bg-yellow-100', text: 'Pending' };
      case 'RUNNING':
        return { color: 'text-blue-600', bg: 'bg-blue-100', text: 'Running' };
      case 'COMPLETED':
        return { color: 'text-green-600', bg: 'bg-green-100', text: 'Completed' };
      case 'FAILED':
        return { color: 'text-red-600', bg: 'bg-red-100', text: 'Failed' };
      default:
        return { color: 'text-gray-600', bg: 'bg-gray-100', text: 'Unknown' };
    }
  };

  const config = getStatusConfig(status);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.color} ${className}`}
      data-testid="status-badge"
    >
      <span
        className={`w-2 h-2 rounded-full mr-1.5 ${config.color.replace('text-', 'bg-')}`}
        data-testid="status-icon"
      />
      {config.text}
    </span>
  );
};
```

### API Integration

```typescript
// lib/api.ts
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { getSession } from 'next-auth/react';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: 30000,
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(async (config) => {
      const session = await getSession();
      if (session?.accessToken) {
        config.headers.Authorization = `Bearer ${session.accessToken}`;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Redirect to login
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Task operations
  async getTasks(params?: { status?: string; page?: number; limit?: number }) {
    const response = await this.client.get('/api/v1/tasks', { params });
    return response.data;
  }

  async createTask(taskData: CreateTaskRequest) {
    const response = await this.client.post('/api/v1/tasks', taskData);
    return response.data;
  }

  async getTask(taskId: number) {
    const response = await this.client.get(`/api/v1/tasks/${taskId}`);
    return response.data;
  }

  async deleteTask(taskId: number) {
    await this.client.delete(`/api/v1/tasks/${taskId}`);
  }

  // User operations
  async getCurrentUser() {
    const response = await this.client.get('/api/v1/users/me');
    return response.data;
  }

  async getUserUsage() {
    const response = await this.client.get('/api/v1/users/me/usage');
    return response.data;
  }
}

export const apiClient = new ApiClient();

// Hook for API operations
export const useApi = () => {
  return {
    tasks: {
      list: apiClient.getTasks.bind(apiClient),
      create: apiClient.createTask.bind(apiClient),
      get: apiClient.getTask.bind(apiClient),
      delete: apiClient.deleteTask.bind(apiClient),
    },
    user: {
      current: apiClient.getCurrentUser.bind(apiClient),
      usage: apiClient.getUserUsage.bind(apiClient),
    },
  };
};
```

### State Management

```typescript
// lib/hooks/useTasks.ts
import { useState, useEffect, useCallback } from 'react';
import { useApi } from '@/lib/api';
import { Task } from '@/types/api';

export const useTasks = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const api = useApi();

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.tasks.list();
      setTasks(response.tasks);
    } catch (err) {
      setError('Failed to fetch tasks');
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
    }
  }, [api]);

  const createTask = useCallback(async (taskData: any) => {
    try {
      const newTask = await api.tasks.create(taskData);
      setTasks(prev => [newTask, ...prev]);
      return newTask;
    } catch (err) {
      setError('Failed to create task');
      throw err;
    }
  }, [api]);

  const deleteTask = useCallback(async (taskId: number) => {
    try {
      await api.tasks.delete(taskId);
      setTasks(prev => prev.filter(task => task.id !== taskId));
    } catch (err) {
      setError('Failed to delete task');
      throw err;
    }
  }, [api]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  return {
    tasks,
    loading,
    error,
    refetch: fetchTasks,
    createTask,
    deleteTask,
  };
};
```

### Form Handling

```typescript
// components/CreateTaskForm.tsx
import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

const taskSchema = yup.object({
  name: yup.string().required('Task name is required').max(100),
  urls: yup.array().of(yup.string().url('Invalid URL')).min(1, 'At least one URL required'),
  selectors: yup.object().test('selectors', 'At least one selector required', (value) => {
    return value && Object.keys(value).length > 0;
  }),
});

interface CreateTaskFormProps {
  onSubmit: (data: any) => Promise<void>;
  loading?: boolean;
}

export const CreateTaskForm: React.FC<CreateTaskFormProps> = ({ onSubmit, loading }) => {
  const [urls, setUrls] = useState<string[]>(['']);
  const [selectors, setSelectors] = useState<{ [key: string]: string }>({ title: '' });

  const { control, handleSubmit, formState: { errors }, setValue } = useForm({
    resolver: yupResolver(taskSchema),
    defaultValues: {
      name: '',
      urls: [''],
      selectors: { title: '' },
    },
  });

  const addUrl = () => {
    const newUrls = [...urls, ''];
    setUrls(newUrls);
    setValue('urls', newUrls);
  };

  const removeUrl = (index: number) => {
    const newUrls = urls.filter((_, i) => i !== index);
    setUrls(newUrls);
    setValue('urls', newUrls);
  };

  const addSelector = () => {
    const key = `selector_${Object.keys(selectors).length + 1}`;
    const newSelectors = { ...selectors, [key]: '' };
    setSelectors(newSelectors);
    setValue('selectors', newSelectors);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Task Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Task Name</label>
        <Controller
          name="name"
          control={control}
          render={({ field }) => (
            <input
              {...field}
              type="text"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Enter task name"
            />
          )}
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
        )}
      </div>

      {/* URLs */}
      <div>
        <label className="block text-sm font-medium text-gray-700">URLs to Scrape</label>
        {urls.map((url, index) => (
          <div key={index} className="flex mt-2">
            <Controller
              name={`urls.${index}`}
              control={control}
              render={({ field }) => (
                <input
                  {...field}
                  type="url"
                  className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="https://example.com"
                  onChange={(e) => {
                    field.onChange(e);
                    const newUrls = [...urls];
                    newUrls[index] = e.target.value;
                    setUrls(newUrls);
                  }}
                />
              )}
            />
            {urls.length > 1 && (
              <button
                type="button"
                onClick={() => removeUrl(index)}
                className="ml-2 px-3 py-2 text-red-600 hover:text-red-800"
              >
                Remove
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={addUrl}
          className="mt-2 text-blue-600 hover:text-blue-800"
        >
          + Add URL
        </button>
        {errors.urls && (
          <p className="mt-1 text-sm text-red-600">{errors.urls.message}</p>
        )}
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Creating Task...' : 'Create Task'}
      </button>
    </form>
  );
};
```

---

## Worker Development

### Worker Architecture

```
worker/
├── __init__.py
├── main.py              # Worker entry point
├── celery_config.py     # Celery configuration
├── tasks.py             # Task definitions
├── proxies.py           # Proxy management
├── task_schemas.py      # Task validation schemas
├── browsers.py          # Browser management
├── utils.py             # Utility functions
└── requirements.txt     # Python dependencies
```

### Task Implementation

```python
# worker/tasks.py
import asyncio
from celery import Celery
from playwright.async_api import async_playwright
from .proxies import ProxyManager
from .task_schemas import validate_task_config
from api.database import get_db
from api.models import Task
import json
import traceback
from datetime import datetime

app = Celery('worker')

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_task(self, task_id: int):
    """Execute scraping task with retry logic."""
    try:
        # Run async task in event loop
        return asyncio.run(_execute_scrape_task(self, task_id))
    except Exception as exc:
        # Classify error type for retry logic
        if should_retry_error(exc):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
        else:
            return handle_task_failure(task_id, exc)

async def _execute_scrape_task(celery_task, task_id: int):
    """Main task execution logic."""
    db = next(get_db())
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise Exception(f"Task {task_id} not found")
    
    try:
        # Update task status
        task.status = "RUNNING"
        task.updated_at = datetime.utcnow()
        db.commit()
        
        # Validate task configuration
        config = validate_task_config(task.config, task.task_type)
        
        # Initialize proxy manager
        proxy_manager = ProxyManager()
        
        # Execute scraping
        results = await execute_scraping_logic(config, proxy_manager)
        
        # Save results
        task.status = "COMPLETED"
        task.result = json.dumps(results)
        task.updated_at = datetime.utcnow()
        db.commit()
        
        return {"status": "COMPLETED", "task_id": task_id, "results": results}
        
    except Exception as e:
        task.status = "FAILED"
        task.error_details = str(e)
        task.updated_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()

async def execute_scraping_logic(config, proxy_manager):
    """Execute the actual scraping logic."""
    results = []
    
    async with async_playwright() as p:
        # Launch browser with proxy
        proxy = proxy_manager.get_random_proxy()
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": f"http://{proxy['host']}:{proxy['port']}"} if proxy else None,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-gpu'
            ]
        )
        
        try:
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            for url in config['urls']:
                page = await context.new_page()
                
                try:
                    # Navigate to page
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    
                    # Wait for content to load
                    await page.wait_for_timeout(config.get('wait_time', 5) * 1000)
                    
                    # Extract data using selectors
                    page_data = {"url": url}
                    for key, selector in config['selectors'].items():
                        try:
                            element = await page.locator(selector).first
                            if element:
                                page_data[key] = await element.text_content()
                            else:
                                page_data[key] = None
                        except Exception as e:
                            page_data[key] = None
                            print(f"Error extracting {key} with selector {selector}: {e}")
                    
                    results.append(page_data)
                    
                except Exception as e:
                    results.append({"url": url, "error": str(e)})
                    
                finally:
                    await page.close()
                    
        finally:
            await browser.close()
    
    return results

def should_retry_error(exc):
    """Determine if error should trigger retry."""
    retriable_errors = [
        "TimeoutError",
        "NetworkError",
        "ProxyError",
        "TemporaryError"
    ]
    return any(error in str(exc) for error in retriable_errors)

def handle_task_failure(task_id, exc):
    """Handle permanent task failure."""
    return {
        "status": "FAILED",
        "task_id": task_id,
        "error": str(exc),
        "traceback": traceback.format_exc()
    }
```

### Proxy Management

```python
# worker/proxies.py
import requests
import redis
import json
import random
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

class ProxyManager:
    def __init__(self):
        self.api_key = os.getenv("WEBSHARE_API_KEY")
        self.redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"))
        self.cache_key = "proxy:working_proxies"
        self.cache_ttl = 300  # 5 minutes
        
    def get_working_proxies(self) -> List[Dict]:
        """Get list of working proxies with caching."""
        # Try cache first
        cached_proxies = self.redis_client.get(self.cache_key)
        if cached_proxies:
            return json.loads(cached_proxies)
        
        # Fetch from API
        proxies = self._fetch_proxies_from_api()
        
        # Test and filter working proxies
        working_proxies = self._test_proxies(proxies)
        
        # Cache working proxies
        self.redis_client.setex(
            self.cache_key,
            self.cache_ttl,
            json.dumps(working_proxies)
        )
        
        return working_proxies
    
    def _fetch_proxies_from_api(self) -> List[Dict]:
        """Fetch proxies from Webshare API."""
        if not self.api_key:
            return []  # Return empty list for development
        
        try:
            response = requests.get(
                "https://proxy.webshare.io/api/v2/proxy/list/",
                headers={"Authorization": f"Token {self.api_key}"},
                params={"mode": "direct", "page_size": 100}
            )
            response.raise_for_status()
            
            data = response.json()
            return [
                {
                    "host": proxy["proxy_address"],
                    "port": proxy["port"],
                    "username": proxy["username"],
                    "password": proxy["password"]
                }
                for proxy in data.get("results", [])
            ]
        except Exception as e:
            print(f"Error fetching proxies: {e}")
            return []
    
    def _test_proxies(self, proxies: List[Dict], max_workers=10) -> List[Dict]:
        """Test proxies and return only working ones."""
        import concurrent.futures
        
        def test_proxy(proxy):
            try:
                proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                response = requests.get(
                    "http://httpbin.org/ip",
                    proxies={"http": proxy_url, "https": proxy_url},
                    timeout=10
                )
                return proxy if response.status_code == 200 else None
            except:
                return None
        
        working_proxies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(test_proxy, proxy) for proxy in proxies[:50]]  # Test first 50
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    working_proxies.append(result)
        
        return working_proxies
    
    def get_random_proxy(self) -> Optional[Dict]:
        """Get a random working proxy."""
        proxies = self.get_working_proxies()
        return random.choice(proxies) if proxies else None
    
    def refresh_proxies(self):
        """Force refresh proxy cache."""
        self.redis_client.delete(self.cache_key)
        return self.get_working_proxies()
```

### Task Schemas

```python
# worker/task_schemas.py
from pydantic import BaseModel, validator
from typing import Dict, List, Any, Optional
import json

class SimpleScrapeConfig(BaseModel):
    urls: List[str]
    selectors: Dict[str, str]
    output_format: str = "json"
    wait_time: int = 5
    use_proxy: bool = True
    
    @validator('urls')
    def validate_urls(cls, v):
        if not v:
            raise ValueError("URLs list cannot be empty")
        if len(v) > 100:
            raise ValueError("Maximum 100 URLs allowed")
        return v
    
    @validator('selectors')
    def validate_selectors(cls, v):
        if not v:
            raise ValueError("Selectors cannot be empty")
        for key, selector in v.items():
            if not selector.strip():
                raise ValueError(f"Selector for '{key}' cannot be empty")
        return v

class AdvancedScrapeConfig(BaseModel):
    urls: List[str]
    selectors: Dict[str, str]
    actions: Optional[List[Dict[str, Any]]] = []
    pagination: Optional[Dict[str, Any]] = None
    output_format: str = "json"
    wait_time: int = 5
    screenshot: bool = False
    
    @validator('actions')
    def validate_actions(cls, v):
        if v:
            for action in v:
                if 'type' not in action:
                    raise ValueError("Action must have 'type' field")
                if action['type'] not in ['click', 'type', 'scroll', 'wait']:
                    raise ValueError(f"Invalid action type: {action['type']}")
        return v

def validate_task_config(config: Dict[str, Any], task_type: str) -> Dict[str, Any]:
    """Validate task configuration based on task type."""
    if task_type == "simple_scraping":
        validated = SimpleScrapeConfig(**config)
    elif task_type == "advanced_scraping":
        validated = AdvancedScrapeConfig(**config)
    else:
        raise ValueError(f"Unknown task type: {task_type}")
    
    return validated.dict()
```

---

## Monitoring and Debugging

### Logging Configuration

```python
# api/main.py
import logging
import json
from datetime import datetime
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "request_completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )
    
    return response
```

### Performance Monitoring

```python
# api/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import functools

# Metrics definitions
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_tasks = Gauge('active_tasks_total', 'Number of active tasks')
task_execution_time = Histogram('task_execution_duration_seconds', 'Task execution time', ['task_type'])

def monitor_endpoint(endpoint_name: str):
    """Decorator to monitor API endpoint performance."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                request_duration.labels(
                    method="POST",  # Adjust based on actual method
                    endpoint=endpoint_name
                ).observe(duration)
                request_count.labels(
                    method="POST",
                    endpoint=endpoint_name,
                    status=status
                ).inc()
        
        return wrapper
    return decorator

# Usage in endpoints
@app.post("/api/v1/tasks")
@monitor_endpoint("create_task")
async def create_task(task: TaskCreate, current_user: User = Depends(get_current_user)):
    # Task creation logic
    pass

@app.get("/metrics")
async def get_metrics():
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type="text/plain")
```

### Debugging Tools

```python
# api/debug.py
from fastapi import Request
import json
import traceback

async def debug_request(request: Request):
    """Debug request details."""
    print("=== Request Debug ===")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {dict(request.headers)}")
    
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            print(f"Body: {body.decode()}")
        except:
            print("Body: Could not decode")
    
    print("=== End Debug ===")

class DebugMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and os.getenv("DEBUG") == "true":
            request = Request(scope, receive)
            await debug_request(request)
        
        await self.app(scope, receive, send)

# Add to app if DEBUG mode
if os.getenv("DEBUG") == "true":
    app.add_middleware(DebugMiddleware)
```

### Health Checks

```python
# api/health.py
from fastapi import Depends
from sqlalchemy.orm import Session
import redis
import requests

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check endpoint."""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database check
    try:
        db.execute("SELECT 1")
        checks["checks"]["database"] = "healthy"
    except Exception as e:
        checks["checks"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "unhealthy"
    
    # Redis check
    try:
        redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"))
        redis_client.ping()
        checks["checks"]["redis"] = "healthy"
    except Exception as e:
        checks["checks"]["redis"] = f"unhealthy: {str(e)}"
        checks["status"] = "unhealthy"
    
    # External API checks
    try:
        # Check Webshare API
        if os.getenv("WEBSHARE_API_KEY"):
            response = requests.get(
                "https://proxy.webshare.io/api/v2/proxy/list/",
                headers={"Authorization": f"Token {os.getenv('WEBSHARE_API_KEY')}"},
                timeout=5
            )
            checks["checks"]["webshare_api"] = "healthy" if response.status_code == 200 else "unhealthy"
        else:
            checks["checks"]["webshare_api"] = "not_configured"
    except Exception as e:
        checks["checks"]["webshare_api"] = f"unhealthy: {str(e)}"
    
    return checks

@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    return {"status": "ready"}

@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}
```

---

## Contribution Guidelines

### Getting Started

1. **Fork the repository** and clone your fork
2. **Create a feature branch** from `develop`
3. **Set up development environment** using Docker Compose
4. **Make your changes** following our coding standards
5. **Add tests** for new functionality
6. **Update documentation** if needed
7. **Submit a pull request** with clear description

### Coding Standards

#### Python (API/Worker)

```python
# Use type hints
def create_task(task_data: TaskCreate, user_id: int) -> Task:
    """Create a new task with proper type hints."""
    pass

# Use docstrings
def complex_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    Perform complex operation.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Dictionary containing operation results
        
    Raises:
        ValueError: If parameters are invalid
    """
    pass

# Use proper error handling
try:
    result = risky_operation()
except SpecificException as e:
    logger.error("Operation failed", error=str(e))
    raise HTTPException(status_code=500, detail="Operation failed")
```

#### TypeScript (Frontend)

```typescript
// Use proper interfaces
interface Task {
  id: number;
  name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  createdAt: string;
}

// Use proper error handling
const handleApiError = (error: any) => {
  if (error.response?.status === 401) {
    // Handle unauthorized
  } else if (error.response?.status >= 500) {
    // Handle server error
  }
};

// Use proper component structure
interface ComponentProps {
  data: Task[];
  onUpdate?: (task: Task) => void;
}

export const TaskList: React.FC<ComponentProps> = ({ data, onUpdate }) => {
  // Component implementation
};
```

### Testing Requirements

- **Unit tests** for all business logic
- **Integration tests** for API endpoints
- **Component tests** for React components
- **E2E tests** for critical user flows
- **Minimum 80% code coverage** for new code

### Documentation Standards

- **API documentation** using OpenAPI/Swagger
- **Code comments** for complex logic
- **README updates** for setup changes
- **Changelog entries** for user-facing changes

### Review Process

All pull requests must:

1. **Pass all CI checks** (tests, linting, security)
2. **Have at least one reviewer approval**
3. **Include updated documentation**
4. **Follow conventional commit format**
5. **Not decrease test coverage**

### Release Process

1. **Feature freeze** on `develop` branch
2. **Create release branch** `release/vX.Y.Z`
3. **Final testing** and bug fixes
4. **Merge to `main`** and tag release
5. **Deploy to production**
6. **Update documentation**

---

## Performance Considerations

### Database Optimization

```python
# Use proper indexes
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)  # Index for joins
    status = Column(String, index=True)  # Index for filtering
    created_at = Column(DateTime, index=True)  # Index for sorting

# Use efficient queries
def get_user_tasks_efficiently(db: Session, user_id: int, limit: int = 10):
    """Get user tasks with efficient query."""
    return db.query(Task)\
        .filter(Task.user_id == user_id)\
        .options(selectinload(Task.user))\
        .order_by(Task.created_at.desc())\
        .limit(limit)\
        .all()

# Use pagination for large datasets
def get_tasks_paginated(db: Session, page: int = 1, size: int = 20):
    """Get tasks with pagination."""
    offset = (page - 1) * size
    return db.query(Task)\
        .offset(offset)\
        .limit(size)\
        .all()
```

### Caching Strategy

```python
# Redis caching for expensive operations
import redis
import json
from functools import wraps

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"))

def cache_result(ttl: int = 300):
    """Cache function result in Redis."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        
        return wrapper
    return decorator

@cache_result(ttl=600)  # Cache for 10 minutes
def get_user_statistics(user_id: int):
    """Get user statistics with caching."""
    # Expensive database operations
    pass
```

### Worker Optimization

```python
# Optimize browser usage
async def optimized_scraping(urls: List[str], selectors: Dict[str, str]):
    """Optimized scraping with connection reuse."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-images',  # Skip images for faster loading
                '--disable-javascript',  # Skip JS if not needed
            ]
        )
        
        context = await browser.new_context()
        
        # Reuse single page for multiple URLs when possible
        page = await context.new_page()
        
        results = []
        for url in urls:
            try:
                await page.goto(url, wait_until='domcontentloaded')
                
                # Extract data concurrently
                tasks = []
                for key, selector in selectors.items():
                    tasks.append(extract_text(page, selector))
                
                values = await asyncio.gather(*tasks, return_exceptions=True)
                page_data = dict(zip(selectors.keys(), values))
                results.append({"url": url, "data": page_data})
                
            except Exception as e:
                results.append({"url": url, "error": str(e)})
        
        await browser.close()
        return results

async def extract_text(page, selector):
    """Extract text with timeout."""
    try:
        element = await page.wait_for_selector(selector, timeout=5000)
        return await element.text_content()
    except:
        return None
```

---

## Security Guidelines

### Input Validation

```python
# Validate all inputs
from pydantic import BaseModel, validator
import re

class TaskInput(BaseModel):
    name: str
    urls: List[str]
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) > 100:
            raise ValueError('Name too long')
        if re.search(r'[<>"\']', v):
            raise ValueError('Invalid characters in name')
        return v
    
    @validator('urls', each_item=True)
    def validate_url(cls, v):
        if not re.match(r'^https?://', v):
            raise ValueError('Only HTTP/HTTPS URLs allowed')
        return v
```

### Authentication Security

```python
# Secure JWT implementation
import jwt
from datetime import datetime, timedelta
import secrets

def create_secure_token(user_id: int) -> str:
    """Create secure JWT token."""
    payload = {
        'user_id': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=1),
        'jti': secrets.token_urlsafe(16)  # Unique token ID
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def validate_token(token: str) -> Optional[dict]:
    """Validate JWT token securely."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        
        # Check if token is not expired
        if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
            return None
            
        return payload
    except jwt.InvalidTokenError:
        return None
```

### SQL Injection Prevention

```python
# Always use parameterized queries
def get_user_tasks_secure(db: Session, user_id: int, status: str):
    """Secure database query."""
    return db.query(Task)\
        .filter(Task.user_id == user_id)\
        .filter(Task.status == status)\
        .all()

# Never use string formatting for SQL
# BAD: f"SELECT * FROM tasks WHERE user_id = {user_id}"
# GOOD: Use SQLAlchemy or parameterized queries
```

### Data Protection

```python
# Encrypt sensitive data
from cryptography.fernet import Fernet
import os

def get_encryption_key():
    """Get encryption key from environment."""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        key = Fernet.generate_key()
        print(f"Generated new encryption key: {key.decode()}")
    return key.encode() if isinstance(key, str) else key

cipher = Fernet(get_encryption_key())

def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data."""
    return cipher.encrypt(data.encode()).decode()

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    return cipher.decrypt(encrypted_data.encode()).decode()
```

---

This comprehensive developer guide provides all the necessary information for contributing to Selextract Cloud. Remember to follow the established patterns and always prioritize security and performance in your implementations.

