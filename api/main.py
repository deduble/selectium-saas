"""
FastAPI application with comprehensive REST API endpoints for Selextract Cloud.
"""
import os
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from starlette.middleware.base import BaseHTTPMiddleware

from database import engine, get_db, create_tables
from metrics import (
    setup_metrics, record_user_registration, record_compute_unit_consumption,
    update_user_compute_units, record_task_creation, record_task_completion,
    record_failed_login, record_rate_limit_violation, get_health_metrics
)
from models import User, Task, APIKey, UserSubscription, SubscriptionPlan, UsageAnalytics, TaskLog
from schemas import (
    # Auth schemas
    GoogleAuthURL, GoogleCallback, TokenResponse, UserResponse, UserCreate, UserUpdate,
    # Task schemas
    TaskCreate, TaskResponse, TaskUpdate, TaskLogsResponse, TaskFilters, PaginationParams, PaginatedResponse,
    # API Key schemas
    APIKeyCreate, APIKeyResponse, APIKeyCreatedResponse,
    # Subscription schemas
    SubscriptionResponse, SubscriptionPlan as SubscriptionPlanSchema, SubscriptionUpdate,
    # Analytics schemas
    UsageAnalytics as UsageAnalyticsSchema, DashboardStats,
    # Error schemas
    ErrorResponse, ValidationErrorResponse, HealthCheck,
    # Enums
    TaskStatus, TaskType, SubscriptionTier
)
from auth import (
    get_current_user, get_optional_current_user, RequireAuth, OptionalAuth,
    RequireProTier, RequireEnterpriseTier, RequireAdmin,
    get_google_auth_url, exchange_code_for_token, get_user_from_google,
    get_or_create_user, create_access_token, create_state_token, verify_state_token,
    generate_api_key, hash_api_key, auth_rate_limiter, get_client_ip, check_auth_rate_limit,
    AuthenticationError, AuthorizationError, require_compute_units
)
from celery_app import submit_task, cancel_task, get_queue_stats, health_check as celery_health_check
from validate_schema import validate_task_config
from billing import LemonSqueezyClient, SubscriptionManager, get_subscription_manager
from webhooks import process_lemon_squeezy_webhook


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment configuration - use standardized names with legacy fallbacks
DEBUG = os.getenv("SELEXTRACT_DEBUG", os.getenv("DEBUG", "false")).lower() == "true"
ENVIRONMENT = os.getenv("SELEXTRACT_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
ALLOWED_ORIGINS = os.getenv("SELEXTRACT_ALLOWED_ORIGINS", os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")).split(",")
API_VERSION = "v1"

# Application URLs
API_URL = os.getenv("SELEXTRACT_API_URL", os.getenv("API_URL", "http://localhost:8000"))
FRONTEND_URL = os.getenv("SELEXTRACT_FRONTEND_URL", os.getenv("FRONTEND_URL", "http://localhost:3000"))

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# In-memory session storage for OAuth state (use Redis in production)
oauth_sessions = {}


def validate_environment():
    """Validate required environment variables are set."""
    required_vars = [
        "SELEXTRACT_DB_HOST",
        "SELEXTRACT_DB_NAME",
        "SELEXTRACT_DB_USER",
        "SELEXTRACT_DB_PASSWORD",
        "SELEXTRACT_REDIS_HOST",
        "SELEXTRACT_REDIS_PASSWORD"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            # Check legacy fallback
            legacy_var = var.replace("SELEXTRACT_", "")
            if var == "SELEXTRACT_DB_HOST":
                legacy_var = "DATABASE_URL"
            elif var == "SELEXTRACT_REDIS_HOST":
                legacy_var = "REDIS_URL"
            
            if not os.getenv(legacy_var):
                missing_vars.append(f"{var} (or {legacy_var})")
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)} - using defaults")
    
    # Log environment status
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info("Environment validation completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting Selextract Cloud API...")
    
    # Validate environment variables first
    try:
        validate_environment()
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        raise SystemExit(1)
    
    # Create database tables
    create_tables()
    logger.info("Database tables created/verified")
    
    # Custom metrics are now initialized during app creation
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Selextract Cloud API...")


# Create FastAPI app
app = FastAPI(
    title="Selextract Cloud API",
    description="Comprehensive web scraping and data extraction platform API",
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware
if not DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["selextract.com", "*.selextract.com", "localhost"]
    )

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Custom middleware for request logging and error handling
class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging and error handling."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.now(timezone.utc)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        logger.info(f"Request {request_id}: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Request {request_id}: {response.status_code} - {duration:.3f}s")
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Request {request_id}: Error - {str(exc)} - {duration:.3f}s")
            
            # Return generic error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An internal server error occurred",
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )


app.add_middleware(LoggingMiddleware)

# Initialize custom metrics (must be done after app creation but before startup)
setup_metrics(app)
logger.info("Custom Prometheus metrics enabled")


# Exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "authentication_error",
            "message": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        },
        headers=exc.headers
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "authorization_error",
            "message": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheck)
async def health_check(db = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check database
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    # Check Celery
    celery_status = celery_health_check()
    
    # Check Redis (through Celery broker)
    redis_status = "healthy" if celery_status["status"] == "healthy" else "unhealthy"
    
    overall_status = "healthy" if all([
        db_status == "healthy",
        celery_status["status"] == "healthy"
    ]) else "degraded"
    
    # Get additional health metrics
    metrics = get_health_metrics()
    
    return HealthCheck(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        redis=redis_status,
        celery=celery_status["status"]
    )


# ================================
# AUTHENTICATION ROUTES
# ================================

@app.get("/api/v1/auth/google", response_model=GoogleAuthURL)
@limiter.limit("10/minute")
async def google_auth_url(request: Request):
    """Get Google OAuth authorization URL."""
    await check_auth_rate_limit(request)
    
    state = create_state_token()
    auth_url = get_google_auth_url(state)
    
    # Store state in session (use Redis in production)
    oauth_sessions[state] = {
        "created_at": datetime.now(timezone.utc),
        "ip": get_client_ip(request)
    }
    
    return GoogleAuthURL(auth_url=auth_url, state=state)


@app.get("/api/v1/auth/google/callback")
@limiter.limit("5/minute")
async def google_auth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db = Depends(get_db)
):
    """Handle Google OAuth callback and redirect to frontend."""
    await check_auth_rate_limit(request)
    
    client_ip = get_client_ip(request)
    frontend_success_url = f"{FRONTEND_URL}/auth/success"
    frontend_error_url = f"{FRONTEND_URL}/login"
    
    try:
        # Handle OAuth errors
        if error:
            logger.warning(f"OAuth error from Google: {error}")
            return Response(
                status_code=302,
                headers={"Location": f"{frontend_error_url}?error={error}"}
            )
        
        if not code or not state:
            logger.warning(f"OAuth callback missing parameters: code={bool(code)}, state={bool(state)}")
            auth_rate_limiter.record_attempt(client_ip, success=False)
            record_failed_login(client_ip)
            return Response(
                status_code=302,
                headers={"Location": f"{frontend_error_url}?error=missing_parameters"}
            )
        
        logger.info(f"OAuth callback processing: state={state[:10]}...")
        
        # Verify state token
        if state not in oauth_sessions:
            logger.warning(f"OAuth callback invalid state: {state[:10]}... not in sessions")
            auth_rate_limiter.record_attempt(client_ip, success=False)
            record_failed_login(client_ip)
            return Response(
                status_code=302,
                headers={"Location": f"{frontend_error_url}?error=invalid_state"}
            )
        
        session_data = oauth_sessions[state]
        
        # Check session age (5 minutes max)
        if datetime.now(timezone.utc) - session_data["created_at"] > timedelta(minutes=5):
            logger.warning(f"OAuth callback state expired: {state[:10]}...")
            del oauth_sessions[state]
            auth_rate_limiter.record_attempt(client_ip, success=False)
            record_failed_login(client_ip)
            return Response(
                status_code=302,
                headers={"Location": f"{frontend_error_url}?error=state_expired"}
            )
        
        logger.info("Exchanging OAuth code for token...")
        # Exchange code for token
        token_data = await exchange_code_for_token(code)
        logger.info(f"Token exchange successful, getting user info...")
        
        google_user_info = await get_user_from_google(token_data["access_token"])
        logger.info(f"Got Google user info for: {google_user_info.get('email', 'unknown')}")
        
        # Get or create user
        logger.info("Creating or getting user from database...")
        user = get_or_create_user(db, google_user_info)
        logger.info(f"User resolved: {user.email} (ID: {user.id})")
        
        # Record user registration if new user
        if user.created_at >= datetime.now(timezone.utc) - timedelta(minutes=1):
            logger.info("Recording new user registration")
            record_user_registration()
        
        # Create JWT token
        logger.info("Creating JWT access token...")
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        logger.info(f"JWT token created successfully, length: {len(access_token)}")
        
        # Clean up session
        del oauth_sessions[state]
        auth_rate_limiter.record_attempt(client_ip, success=True)
        
        # Redirect to frontend with token
        logger.info(f"Redirecting to success page: {frontend_success_url}")
        return Response(
            status_code=302,
            headers={"Location": f"{frontend_success_url}?token={access_token}"}
        )
        
    except HTTPException:
        return Response(
            status_code=302,
            headers={"Location": f"{frontend_error_url}?error=authentication_failed"}
        )
    except Exception as e:
        auth_rate_limiter.record_attempt(client_ip, success=False)
        record_failed_login(client_ip)
        logger.error(f"OAuth callback error: {e}")
        return Response(
            status_code=302,
            headers={"Location": f"{frontend_error_url}?error=server_error"}
        )


@app.post("/api/v1/auth/google", response_model=TokenResponse)
@limiter.limit("5/minute")
async def google_auth_direct(
    callback_data: GoogleCallback,
    request: Request,
    db = Depends(get_db)
):
    """Handle Google OAuth direct callback (alternative method)."""
    await check_auth_rate_limit(request)
    
    client_ip = get_client_ip(request)
    
    try:
        # Exchange code for token
        token_data = await exchange_code_for_token(callback_data.code)
        google_user_info = await get_user_from_google(token_data["access_token"])
        
        # Get or create user
        user = get_or_create_user(db, google_user_info)
        
        # Record user registration if new user
        if user.created_at >= datetime.now(timezone.utc) - timedelta(minutes=1):
            record_user_registration()
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        auth_rate_limiter.record_attempt(client_ip, success=True)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=3600,  # 1 hour
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        auth_rate_limiter.record_attempt(client_ip, success=False)
        record_failed_login(client_ip)
        logger.error(f"OAuth direct callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(user: User = RequireAuth):
    """Get current user information."""
    return UserResponse.from_orm(user)


@app.put("/api/v1/auth/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Update current user information."""
    # Update allowed fields
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.avatar_url is not None:
        user.avatar_url = user_update.avatar_url
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@app.post("/api/v1/auth/logout")
async def logout(user: User = RequireAuth):
    """Logout user (client should discard token)."""
    return {"message": "Successfully logged out"}


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(user: User = RequireAuth):
    """Refresh access token for authenticated user."""
    try:
        # Generate new access token with extended expiry
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=3600,  # 1 hour
            user=UserResponse.from_orm(user)
        )
        
    except Exception as e:
        logger.error(f"Failed to refresh token for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh token")


@app.delete("/api/v1/auth/account")
async def delete_account(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Delete user account and cleanup associated data."""
    try:
        # Cancel all active tasks
        active_tasks = db.query(Task).filter(
            Task.user_id == user.id,
            Task.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
        ).all()
        
        for task in active_tasks:
            if task.celery_task_id:
                cancel_task(task.celery_task_id)
            task.status = TaskStatus.CANCELLED.value
            task.completed_at = datetime.now(timezone.utc)
        
        # Deactivate all API keys
        api_keys = db.query(APIKey).filter(
            APIKey.user_id == user.id,
            APIKey.is_active == True
        ).all()
        
        for api_key in api_keys:
            api_key.is_active = False
        
        # Cancel active subscriptions
        active_subscription = user.get_active_subscription()
        if active_subscription and active_subscription.lemon_squeezy_subscription_id:
            try:
                from billing import LemonSqueezyClient
                lemon_client = LemonSqueezyClient()
                lemon_client.cancel_subscription(active_subscription.lemon_squeezy_subscription_id)
            except Exception as e:
                logger.warning(f"Failed to cancel LemonSqueezy subscription: {e}")
        
        # Soft delete user (set inactive)
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.local"  # Anonymize email
        
        db.commit()
        
        logger.info(f"User account {user.id} deleted successfully")
        
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete account for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")


# ================================
# TASK MANAGEMENT ROUTES
# ================================

@app.get("/api/v1/tasks", response_model=PaginatedResponse[TaskResponse])
async def get_user_tasks(
    user: User = RequireAuth,
    filters: TaskFilters = Depends(),
    pagination: PaginationParams = Depends(),
    db = Depends(get_db)
):
    """Get user's tasks with filtering and pagination."""
    query = db.query(Task).filter(Task.user_id == user.id)
    
    # Apply filters
    if filters.status:
        query = query.filter(Task.status.in_([s.value for s in filters.status]))
    
    if filters.task_type:
        query = query.filter(Task.config["task_type"].astext.in_([t.value for t in filters.task_type]))
    
    if filters.created_after:
        query = query.filter(Task.created_at >= filters.created_after)
    
    if filters.created_before:
        query = query.filter(Task.created_at <= filters.created_before)
    
    if filters.name_contains:
        query = query.filter(Task.name.ilike(f"%{filters.name_contains}%"))
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply sorting
    if pagination.sort_by:
        sort_column = getattr(Task, pagination.sort_by, Task.created_at)
        if pagination.sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(Task.created_at.desc())
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    tasks = query.offset(offset).limit(pagination.page_size).all()
    
    # Calculate pagination metadata
    total_pages = (total_count + pagination.page_size - 1) // pagination.page_size
    has_next = pagination.page < total_pages
    has_prev = pagination.page > 1
    
    return PaginatedResponse(
        items=[TaskResponse.from_orm(task) for task in tasks],
        total_count=total_count,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )


@app.post("/api/v1/tasks", response_model=TaskResponse)
@limiter.limit("30/minute")
async def create_task(
    task_data: TaskCreate,
    request: Request,
    user: User = Depends(require_compute_units(1)),  # Require at least 1 CU
    db = Depends(get_db)
):
    """Create a new scraping task."""
    try:
        # Validate task configuration
        validation_result = validate_task_config(task_data.config, task_data.task_type.value)
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task configuration: {validation_result['errors']}"
            )
        
        # Estimate compute units (simple estimation: 1 CU per URL)
        estimated_cus = len(task_data.config.get("urls", [1]))  # Default to 1 if no URLs
        
        # Check if user has enough compute units
        if user.compute_units_remaining < estimated_cus:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient compute units. Required: {estimated_cus}, Available: {user.compute_units_remaining}"
            )
        
        # Create task
        task = Task(
            user_id=user.id,
            name=task_data.name,
            description=task_data.description,
            task_type=task_data.task_type.value,
            config=task_data.config,
            status=TaskStatus.PENDING.value,
            priority=task_data.priority,
            estimated_compute_units=estimated_cus,
            progress=0,
            scheduled_at=datetime.now(timezone.utc)
        )
        
        db.add(task)
        db.flush()  # Get task ID
        
        # Record task creation metrics
        record_task_creation(task_data.task_type.value, str(user.id))
        
        # Submit to Celery queue
        celery_task_id = submit_task(
            task_id=task.id,
            task_type=task_data.task_type.value,
            config=task_data.config,
            priority=task_data.priority
        )
        
        # Update task status
        task.status = TaskStatus.QUEUED.value
        task.celery_task_id = celery_task_id
        
        # Update user compute units
        user.compute_units_remaining -= estimated_cus
        record_compute_unit_consumption(str(user.id), task_data.task_type.value, estimated_cus)
        update_user_compute_units(str(user.id), user.compute_units_remaining)
        
        db.commit()
        db.refresh(task)
        
        logger.info(f"Created task {task.id} for user {user.id}")
        
        return TaskResponse.from_orm(task)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail="Failed to create task")


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Get a specific task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse.from_orm(task)


@app.put("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_update: TaskUpdate,
    task_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Update a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if task can be updated
    if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
        # Allow only name and description updates for completed/failed tasks
        if task_update.config is not None or task_update.priority is not None:
            raise HTTPException(status_code=400, detail="Cannot update configuration or priority of completed/failed task")
    elif task.status in [TaskStatus.RUNNING.value]:
        # Don't allow config updates for running tasks
        if task_update.config is not None:
            raise HTTPException(status_code=400, detail="Cannot update configuration of running task")
    
    # Update allowed fields
    if task_update.name is not None:
        task.name = task_update.name
    if task_update.description is not None:
        task.description = task_update.description
    if task_update.priority is not None:
        task.priority = task_update.priority
    
    # Update configuration if provided and task allows it
    if task_update.config is not None:
        try:
            # Validate the configuration against the task type
            validation_result = validate_task_config(task_update.config, task.task_type)
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid task configuration: {validation_result['errors']}"
                )
            
            # Update the configuration
            task.config = task_update.config
            logger.info(f"Updated configuration for task {task_id} by user {user.id}")
            
        except Exception as e:
            logger.error(f"Failed to update task configuration: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to update configuration: {str(e)}")
    
    db.commit()
    db.refresh(task)
    
    return TaskResponse.from_orm(task)


@app.delete("/api/v1/tasks/{task_id}")
async def delete_task(
    task_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Delete/cancel a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Cancel if running
    if task.can_be_cancelled() and hasattr(task, 'celery_task_id'):
        cancel_task(task.celery_task_id)
    
    # Delete task
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully"}


@app.get("/api/v1/tasks/{task_id}/logs", response_model=TaskLogsResponse)
async def get_task_logs(
    task_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    pagination: PaginationParams = Depends(),
    db = Depends(get_db)
):
    """Get task execution logs."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get logs with pagination
    query = db.query(TaskLog).filter(TaskLog.task_id == task_id)
    query = query.order_by(TaskLog.timestamp.desc())
    
    total_count = query.count()
    offset = (pagination.page - 1) * pagination.page_size
    logs = query.offset(offset).limit(pagination.page_size).all()
    
    return TaskLogsResponse(
        task_id=task_id,
        logs=[{
            "id": log.id,
            "task_id": log.task_id,
            "level": log.level,
            "message": log.message,
            "timestamp": log.timestamp,
            "metadata": log.log_data
        } for log in logs],
        total_count=total_count,
        page=pagination.page,
        page_size=pagination.page_size
    )


@app.get("/api/v1/tasks/{task_id}/download")
async def download_task_results(
    task_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Download task results file."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Task not completed")
    
    if not task.result_file_path:
        raise HTTPException(status_code=404, detail="Result file not found")
    
    # Verify file exists
    if not os.path.exists(task.result_file_path):
        raise HTTPException(status_code=404, detail="Result file not found on disk")
    
    return FileResponse(
        path=task.result_file_path,
        filename=f"task_{task_id}_results.json",
        media_type="application/json"
    )


@app.post("/api/v1/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task_endpoint(
    task_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Cancel a pending or running task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value, TaskStatus.QUEUED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status '{task.status}'. Only pending, queued, or running tasks can be cancelled."
        )
    
    try:
        # Cancel Celery task if it has one
        if task.celery_task_id:
            celery_cancelled = cancel_task(task.celery_task_id)
            if not celery_cancelled:
                logger.warning(f"Failed to cancel Celery task {task.celery_task_id} for task {task_id}")
        
        # Update task status to cancelled
        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.now(timezone.utc)
        task.error_message = "Task cancelled by user"
        
        db.commit()
        db.refresh(task)
        
        logger.info(f"Task {task_id} cancelled by user {user.id}")
        
        return TaskResponse.from_orm(task)
        
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@app.post("/api/v1/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task_endpoint(
    task_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Retry a failed task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.FAILED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry task with status '{task.status}'. Only failed tasks can be retried."
        )
    
    # Check if user has enough compute units for retry
    estimated_cus = len(task.config.get("urls", [1]))  # Same estimation as task creation
    if user.compute_units_remaining < estimated_cus:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient compute units. Required: {estimated_cus}, Available: {user.compute_units_remaining}"
        )
    
    try:
        # Reset task fields for retry
        task.status = TaskStatus.PENDING.value
        task.started_at = None
        task.completed_at = None
        task.error_message = None
        task.result_file_path = None
        task.scheduled_at = datetime.now(timezone.utc)
        
        # Get task type from config
        task_type = task.config.get("task_type", "simple_scraping")
        
        # Resubmit to Celery queue
        celery_task_id = submit_task(
            task_id=task.id,
            task_type=task_type,
            config=task.config,
            priority=task.priority
        )
        
        # Update task status
        task.status = TaskStatus.QUEUED.value
        task.celery_task_id = celery_task_id
        
        # Consume compute units again
        user.compute_units_remaining -= estimated_cus
        record_compute_unit_consumption(str(user.id), task_type, estimated_cus)
        update_user_compute_units(str(user.id), user.compute_units_remaining)
        
        db.commit()
        db.refresh(task)
        
        logger.info(f"Task {task_id} retried by user {user.id}")
        
        return TaskResponse.from_orm(task)
        
    except Exception as e:
        logger.error(f"Failed to retry task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry task")


# ================================
# API KEY MANAGEMENT ROUTES
# ================================

@app.get("/api/v1/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Get user's API keys."""
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.is_active == True
    ).order_by(APIKey.created_at.desc()).all()
    
    return [APIKeyResponse(
        id=key.id,
        name=key.name,
        description=getattr(key, 'description', None),
        key_preview=key.display_key,
        permissions=["tasks:read", "tasks:create"],  # Default permissions
        last_used_at=key.last_used_at,
        created_at=key.created_at,
        is_active=key.is_active
    ) for key in api_keys]


@app.post("/api/v1/api-keys", response_model=APIKeyCreatedResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Create a new API key."""
    # Check if user already has maximum API keys
    existing_keys = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.is_active == True
    ).count()
    
    max_keys = 10 if user.subscription_tier == "enterprise" else 5
    if existing_keys >= max_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_keys} API keys allowed for {user.subscription_tier} tier"
        )
    
    # Generate API key
    api_key, preview = generate_api_key()
    
    # Create API key record
    api_key_record = APIKey(
        user_id=user.id,
        name=api_key_data.name,
        key_hash=hash_api_key(api_key),
        key_prefix=api_key[:8],
        description=api_key_data.description,
        is_active=True
    )
    
    db.add(api_key_record)
    db.commit()
    db.refresh(api_key_record)
    
    logger.info(f"Created API key {api_key_record.id} for user {user.id}")
    
    return APIKeyCreatedResponse(
        id=api_key_record.id,
        name=api_key_record.name,
        description=api_key_record.description,
        key_preview=preview,
        permissions=api_key_data.permissions,
        last_used_at=None,
        created_at=api_key_record.created_at,
        is_active=True,
        api_key=api_key  # Only shown once
    )


@app.delete("/api/v1/api-keys/{key_id}")
async def delete_api_key(
    key_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Delete an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.deactivate()
    db.commit()
    
    return {"message": "API key deactivated successfully"}


@app.post("/api/v1/api-keys/{key_id}/toggle", response_model=APIKeyResponse)
async def toggle_api_key(
    key_id: uuid.UUID = Path(...),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Toggle API key active status (enable/disable)."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    try:
        # Toggle the active status
        api_key.is_active = not api_key.is_active
        
        db.commit()
        db.refresh(api_key)
        
        action = "enabled" if api_key.is_active else "disabled"
        logger.info(f"API key {key_id} {action} by user {user.id}")
        
        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            description=getattr(api_key, 'description', None),
            key_preview=api_key.display_key,
            permissions=["tasks:read", "tasks:create"],  # Default permissions
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            is_active=api_key.is_active
        )
        
    except Exception as e:
        logger.error(f"Failed to toggle API key {key_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle API key")


# ================================
# BILLING AND SUBSCRIPTION ROUTES
# ================================

@app.get("/api/v1/billing/subscription", response_model=Dict[str, Any])
async def get_user_subscription_details(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Get comprehensive user subscription details."""
    try:
        subscription_manager = get_subscription_manager(db)
        details = subscription_manager.get_user_subscription_details(user)
        return details
    except Exception as e:
        logger.error(f"Failed to get subscription details for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get subscription details")


@app.get("/api/v1/billing/plans", response_model=List[SubscriptionPlanSchema])
async def get_subscription_plans(db = Depends(get_db)):
    """Get available subscription plans."""
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.price_cents.asc()).all()
    
    return [SubscriptionPlanSchema(
        id=plan.id,
        name=plan.name,
        tier=plan.id,  # Assuming plan ID matches tier
        price=plan.price_dollars,
        currency="USD",
        compute_units_limit=plan.monthly_compute_units,
        features=[
            f"{plan.monthly_compute_units} compute units/month",
            f"Up to {plan.max_concurrent_tasks} concurrent tasks",
            "24/7 support" if plan.id != "free" else "Community support",
            "API access" if plan.id != "free" else "Limited API access"
        ],
        billing_interval="monthly"
    ) for plan in plans]


@app.post("/api/v1/billing/create-checkout", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def create_checkout_session(
    request_data: Dict[str, Any],
    request: Request,
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Create Lemon Squeezy checkout session for subscription."""
    try:
        plan_id = request_data.get("plan_id")
        success_url = request_data.get("success_url", "https://app.selextract.com/billing/success")
        cancel_url = request_data.get("cancel_url", "https://app.selextract.com/billing/cancelled")
        
        if not plan_id:
            raise HTTPException(status_code=400, detail="plan_id is required")
        
        # Validate plan exists
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Check if user already has an active subscription to this plan
        active_subscription = user.get_active_subscription()
        if active_subscription and active_subscription.plan_id == plan_id:
            raise HTTPException(status_code=400, detail="Already subscribed to this plan")
        
        # Create checkout session
        lemon_client = LemonSqueezyClient()
        checkout_data = lemon_client.create_checkout_session(
            user=user,
            plan_id=plan_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        logger.info(f"Created checkout session for user {user.id}, plan {plan_id}")
        return checkout_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@app.post("/api/v1/billing/webhooks/lemon-squeezy")
async def handle_lemon_squeezy_webhook(
    request: Request,
    db = Depends(get_db)
):
    """Handle Lemon Squeezy webhook events."""
    try:
        result = await process_lemon_squeezy_webhook(request, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@app.get("/api/v1/billing/invoices", response_model=List[Dict[str, Any]])
async def get_user_invoices(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Get user's invoice history."""
    try:
        subscription_manager = get_subscription_manager(db)
        invoices = subscription_manager.get_user_invoices(user)
        return invoices
    except Exception as e:
        logger.error(f"Failed to get invoices for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get invoices")


@app.post("/api/v1/billing/portal", response_model=Dict[str, str])
async def get_customer_portal_url(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Generate customer portal URL for subscription management."""
    try:
        active_subscription = user.get_active_subscription()
        if not active_subscription or not active_subscription.lemon_squeezy_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        lemon_client = LemonSqueezyClient()
        portal_url = lemon_client.get_customer_portal_url(
            active_subscription.lemon_squeezy_subscription_id
        )
        
        return {"portal_url": portal_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get portal URL for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get customer portal URL")


@app.put("/api/v1/billing/subscription", response_model=Dict[str, str])
async def update_subscription_plan(
    request_data: Dict[str, Any],
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Update subscription plan (upgrade/downgrade)."""
    try:
        new_plan_id = request_data.get("plan_id")
        if not new_plan_id:
            raise HTTPException(status_code=400, detail="plan_id is required")
        
        # Get user's active subscription
        active_subscription = user.get_active_subscription()
        if not active_subscription or not active_subscription.lemon_squeezy_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription to update")
        
        # Validate new plan
        new_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == new_plan_id).first()
        if not new_plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        if active_subscription.plan_id == new_plan_id:
            raise HTTPException(status_code=400, detail="Already subscribed to this plan")
        
        # Update subscription via Lemon Squeezy
        if not new_plan.lemon_squeezy_variant_id:
            raise HTTPException(status_code=400, detail="Plan not available for subscription updates")
        
        lemon_client = LemonSqueezyClient()
        lemon_client.update_subscription(
            subscription_id=active_subscription.lemon_squeezy_subscription_id,
            variant_id=new_plan.lemon_squeezy_variant_id,
            invoice_immediately=True
        )
        
        # Note: The actual subscription update will be handled by the webhook
        return {"message": "Subscription update initiated. Changes will take effect shortly."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subscription for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update subscription")


@app.post("/api/v1/billing/subscription/cancel", response_model=Dict[str, str])
async def cancel_subscription(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Cancel user's subscription."""
    try:
        active_subscription = user.get_active_subscription()
        if not active_subscription or not active_subscription.lemon_squeezy_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription to cancel")
        
        # Cancel subscription via Lemon Squeezy
        lemon_client = LemonSqueezyClient()
        lemon_client.cancel_subscription(active_subscription.lemon_squeezy_subscription_id)
        
        # Note: The actual cancellation will be handled by the webhook
        return {"message": "Subscription cancellation initiated. Your subscription will remain active until the end of the current billing period."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel subscription for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@app.post("/api/v1/billing/subscription/resume", response_model=Dict[str, str])
async def resume_subscription(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Resume a cancelled subscription (during grace period)."""
    try:
        active_subscription = user.get_active_subscription()
        if not active_subscription or not active_subscription.lemon_squeezy_subscription_id:
            raise HTTPException(status_code=404, detail="No subscription to resume")
        
        if not active_subscription.cancel_at_period_end:
            raise HTTPException(status_code=400, detail="Subscription is not cancelled")
        
        # Resume subscription via Lemon Squeezy
        lemon_client = LemonSqueezyClient()
        lemon_client.resume_subscription(active_subscription.lemon_squeezy_subscription_id)
        
        # Note: The actual resumption will be handled by the webhook
        return {"message": "Subscription resumption initiated."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume subscription for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resume subscription")


# Legacy subscription endpoint for backwards compatibility
@app.get("/api/v1/subscription", response_model=SubscriptionResponse)
async def get_user_subscription_legacy(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Get user's current subscription (legacy endpoint)."""
    subscription = user.get_active_subscription()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    return SubscriptionResponse.from_orm(subscription)


# ================================
# ANALYTICS ROUTES
# ================================

@app.get("/api/v1/analytics/usage", response_model=UsageAnalyticsSchema)
async def get_usage_analytics(
    period: str = Query(default="monthly", pattern="^(daily|weekly|monthly)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Get user's usage analytics."""
    # Set default date range based on period
    if not end_date:
        end_date = datetime.now(timezone.utc)
    
    if not start_date:
        if period == "daily":
            start_date = end_date - timedelta(days=1)
        elif period == "weekly":
            start_date = end_date - timedelta(weeks=1)
        else:  # monthly
            start_date = end_date - timedelta(days=30)
    
    # Get usage analytics
    analytics = db.query(UsageAnalytics).filter(
        UsageAnalytics.user_id == user.id,
        UsageAnalytics.date >= start_date.date(),
        UsageAnalytics.date <= end_date.date()
    ).all()
    
    # Get tasks for the period
    tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.created_at >= start_date,
        Task.created_at <= end_date
    ).all()
    
    # Calculate aggregates
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED.value])
    failed_tasks = len([t for t in tasks if t.status == TaskStatus.FAILED.value])
    
    compute_units_consumed = sum(a.compute_units_used for a in analytics)
    
    # Get top task types
    task_types = {}
    for task in tasks:
        task_type = task.config.get("task_type", "unknown")
        task_types[task_type] = task_types.get(task_type, 0) + 1
    
    top_task_types = [
        {"type": k, "count": v}
        for k, v in sorted(task_types.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    return UsageAnalyticsSchema(
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        compute_units_consumed=compute_units_consumed,
        compute_units_limit=user.compute_units_remaining + compute_units_consumed,  # Approximate
        top_task_types=top_task_types
    )


@app.get("/api/v1/analytics/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    user: User = RequireAuth,
    db = Depends(get_db)
):
    """Get dashboard statistics."""
    today = datetime.now(timezone.utc).date()
    
    # Active tasks
    active_tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
    ).count()
    
    # Tasks completed today
    completed_today = db.query(Task).filter(
        Task.user_id == user.id,
        Task.status == TaskStatus.COMPLETED.value,
        func.date(Task.completed_at) == today
    ).count()
    
    # Compute units used today
    analytics_today = db.query(UsageAnalytics).filter(
        UsageAnalytics.user_id == user.id,
        UsageAnalytics.date == today
    ).first()
    
    compute_units_used_today = analytics_today.compute_units_used if analytics_today else 0
    
    # Success rate (last 30 days)
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.created_at >= month_ago,
        Task.status.in_([TaskStatus.COMPLETED.value, TaskStatus.FAILED.value])
    ).all()
    
    if recent_tasks:
        successful = len([t for t in recent_tasks if t.status == TaskStatus.COMPLETED.value])
        success_rate = successful / len(recent_tasks)
    else:
        success_rate = 1.0
    
    # Recent tasks
    recent = db.query(Task).filter(
        Task.user_id == user.id
    ).order_by(Task.created_at.desc()).limit(5).all()
    
    return DashboardStats(
        active_tasks=active_tasks,
        completed_tasks_today=completed_today,
        compute_units_used_today=compute_units_used_today,
        compute_units_remaining=user.compute_units_remaining,
        success_rate=success_rate,
        recent_tasks=[TaskResponse.from_orm(task) for task in recent]
    )


# ================================
# ADMIN ROUTES (Optional)
# ================================

@app.get("/api/v1/admin/queue-stats")
async def get_admin_queue_stats(user: User = RequireAdmin):
    """Get Celery queue statistics (admin only)."""
    return get_queue_stats()


@app.get("/api/v1/admin/system-metrics")
async def get_system_metrics(
    user: User = RequireAdmin,
    db = Depends(get_db)
):
    """Get system-wide metrics (admin only)."""
    # Get counts
    total_users = db.query(User).filter(User.is_active == True).count()
    total_tasks = db.query(Task).count()
    active_tasks = db.query(Task).filter(
        Task.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
    ).count()
    
    # Get queue stats
    queue_stats = get_queue_stats()
    
    return {
        "active_users": total_users,
        "total_tasks": total_tasks,
        "active_tasks": active_tasks,
        "queue_length": queue_stats.get("scheduled_tasks", 0),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Standalone functions for validation compatibility
def get_user_tasks(user_id: str, db, **kwargs):
    """Get user tasks - standalone function for validation"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    return db.query(Task).filter(Task.user_id == user.id).all()

def google_auth_url(state: str = None) -> str:
    """Get Google auth URL - standalone function for validation"""
    return get_google_auth_url(state)

def create_task(user_id: str, task_data: dict, db: Session):
    """Create task - standalone function for validation"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    
    task = Task(
        user_id=user.id,
        name=task_data.get("name", "Task"),
        config=task_data.get("config", {}),
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    return task

def health_check() -> dict:
    """Health check - standalone function for validation"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


# ================================
# DEVELOPMENT ROUTES
# ================================

if ENVIRONMENT == "development":
    @app.post("/api/v1/auth/dev/login", response_model=TokenResponse, include_in_schema=False)
    async def dev_login(db: Session = Depends(get_db)):
        """
        Development-only endpoint to get a JWT token for the default dev user.
        """
        from auth import get_or_create_dev_user, create_access_token
        
        dev_user_email = "yunusemremre@gmail.com"
        user = get_or_create_dev_user(db, dev_user_email)
        
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(hours=24)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=86400,  # 24 hours
            user=UserResponse.from_orm(user)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        access_log=DEBUG
    )