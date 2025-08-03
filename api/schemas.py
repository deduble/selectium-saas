"""
Pydantic schemas for request/response validation and serialization.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Generic, TypeVar
from enum import Enum
from pydantic import BaseModel, Field, validator, EmailStr
from uuid import UUID

# Type variables
T = TypeVar('T')

# Enums
class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubscriptionTier(str, Enum):
    """Subscription tier types."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TaskType(str, Enum):
    """Task configuration types."""
    SIMPLE_SCRAPING = "simple_scraping"
    ADVANCED_SCRAPING = "advanced_scraping"
    BULK_SCRAPING = "bulk_scraping"
    MONITORING = "monitoring"


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# User schemas
class UserBase(BaseSchema):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user creation."""
    google_id: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    google_id: str
    name: Optional[str] = Field(None, description="User's full name (mapped from full_name)")
    picture: Optional[str] = Field(None, description="User's avatar URL (mapped from avatar_url)")
    subscription_tier: SubscriptionTier
    subscription_status: str = Field(default="active", description="User's subscription status")
    compute_units_used: int = 0
    compute_units_remaining: int = Field(..., description="Remaining compute units for the user")
    compute_units_limit: int
    api_calls_used: int = Field(0, description="API calls used (alias for compute_units_used)")
    api_calls_limit: int = Field(0, description="API calls limit (alias for compute_units_limit)")
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    def __init__(self, **data):
        """Initialize UserResponse with field mapping."""
        # Map full_name to name for frontend compatibility
        if 'full_name' in data and 'name' not in data:
            data['name'] = data['full_name']
        
        # Map avatar_url to picture for frontend compatibility
        if 'avatar_url' in data and 'picture' not in data:
            data['picture'] = data['avatar_url']
        
        # Map compute units to API calls for frontend compatibility
        if 'compute_units_used' in data and 'api_calls_used' not in data:
            data['api_calls_used'] = data['compute_units_used']
        
        if 'compute_units_limit' in data and 'api_calls_limit' not in data:
            data['api_calls_limit'] = data['compute_units_limit']
        
        super().__init__(**data)


class UserUpdate(BaseSchema):
    """Schema for user updates."""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


# Authentication schemas
class GoogleAuthURL(BaseSchema):
    """Schema for Google auth URL response."""
    auth_url: str
    state: str


class GoogleCallback(BaseSchema):
    """Schema for Google OAuth callback."""
    code: str
    state: str


class TokenResponse(BaseSchema):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseSchema):
    """Schema for token data."""
    user_id: Optional[str] = None
    exp: Optional[datetime] = None


# Task configuration schemas
class ScrapingConfig(BaseSchema):
    """Base scraping configuration."""
    urls: List[str] = Field(..., min_items=1, max_items=1000)
    output_format: str = Field(default="json", pattern="^(json|csv|xlsx)$")
    include_metadata: bool = True
    follow_redirects: bool = True
    timeout: int = Field(default=30, ge=5, le=300)


class SimpleScrapingConfig(ScrapingConfig):
    """Simple scraping configuration."""
    selectors: Dict[str, str] = Field(..., min_items=1)
    
    @validator('selectors')
    def validate_selectors(cls, v):
        if not v:
            raise ValueError('At least one selector is required')
        return v


class AdvancedScrapingConfig(ScrapingConfig):
    """Advanced scraping configuration."""
    selectors: Dict[str, str] = Field(..., min_items=1)
    javascript_enabled: bool = False
    wait_for_selector: Optional[str] = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    cookies: Dict[str, str] = Field(default_factory=dict)
    user_agent: Optional[str] = None
    proxy_rotation: bool = False
    rate_limit: int = Field(default=1, ge=1, le=10)


class BulkScrapingConfig(AdvancedScrapingConfig):
    """Bulk scraping configuration."""
    batch_size: int = Field(default=10, ge=1, le=100)
    parallel_requests: int = Field(default=3, ge=1, le=10)
    retry_attempts: int = Field(default=3, ge=0, le=5)
    export_individual_files: bool = False


class MonitoringConfig(ScrapingConfig):
    """Monitoring configuration."""
    selectors: Dict[str, str] = Field(..., min_items=1)
    schedule: str = Field(..., pattern="^(hourly|daily|weekly)$")
    notification_email: Optional[EmailStr] = None
    change_threshold: float = Field(default=0.1, ge=0.0, le=1.0)


# Task schemas
class TaskConfigSchema(BaseSchema):
    """Task configuration schema."""
    simple_scraping: Optional[SimpleScrapingConfig] = None
    advanced_scraping: Optional[AdvancedScrapingConfig] = None
    bulk_scraping: Optional[BulkScrapingConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    
    @validator('*', pre=True)
    def validate_single_config(cls, v, values):
        # Ensure only one configuration type is provided
        configs = [k for k, v in values.items() if v is not None]
        if len(configs) > 1:
            raise ValueError('Only one task configuration type allowed')
        return v


class TaskCreate(BaseSchema):
    """Schema for task creation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    task_type: TaskType
    config: Dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10)
    
    def __init__(self, **data):
        super().__init__(**data)
    
    @validator('config')
    def validate_config(cls, v, values):
        task_type = values.get('task_type')
        print(f"DEBUG TaskCreate validator: task_type={task_type}")
        print(f"DEBUG TaskCreate validator: config={v}")
        
        if not task_type:
            return v
        
        try:
            # Validate config structure based on task type
            if task_type == TaskType.SIMPLE_SCRAPING:
                print("DEBUG: Validating against SimpleScrapingConfig")
                validated = SimpleScrapingConfig(**v)
                print(f"DEBUG: SimpleScrapingConfig validation successful: {validated}")
            elif task_type == TaskType.ADVANCED_SCRAPING:
                AdvancedScrapingConfig(**v)
            elif task_type == TaskType.BULK_SCRAPING:
                BulkScrapingConfig(**v)
            elif task_type == TaskType.MONITORING:
                MonitoringConfig(**v)
        except Exception as e:
            print(f"DEBUG: Config validation failed: {e}")
            print(f"DEBUG: Error type: {type(e)}")
            if hasattr(e, 'errors'):
                print(f"DEBUG: Error details: {e.errors()}")
            raise
        
        return v


class TaskResponse(BaseSchema):
    """Schema for task response."""
    id: UUID
    name: str
    description: Optional[str]
    task_type: TaskType
    status: TaskStatus
    config: Dict[str, Any]
    priority: int
    compute_units_consumed: int
    estimated_compute_units: int
    result_file_path: Optional[str]
    error_message: Optional[str]
    progress: int = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    user_id: UUID


class TaskUpdate(BaseSchema):
    """Schema for task updates."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[int] = Field(None, ge=1, le=10)
    config: Optional[Dict[str, Any]] = None
    
    @validator('config')
    def validate_config_if_provided(cls, v):
        """Validate config if provided."""
        if v is not None:
            # Basic validation for required fields
            if 'urls' in v:
                urls = v.get('urls', [])
                if not isinstance(urls, list) or not urls:
                    raise ValueError('URLs must be a non-empty list')
                for url in urls:
                    if not isinstance(url, str) or not url.strip():
                        raise ValueError('All URLs must be non-empty strings')
            
            if 'selectors' in v:
                selectors = v.get('selectors', {})
                if not isinstance(selectors, dict) or not selectors:
                    raise ValueError('Selectors must be a non-empty dictionary')
                for key, value in selectors.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        raise ValueError('Selector keys and values must be strings')
                    if not key.strip() or not value.strip():
                        raise ValueError('Selector keys and values must be non-empty')
            
            if 'timeout' in v:
                timeout = v.get('timeout')
                if not isinstance(timeout, int) or timeout < 5 or timeout > 300:
                    raise ValueError('Timeout must be an integer between 5 and 300 seconds')
        
        return v


class TaskLogEntry(BaseSchema):
    """Schema for task log entries."""
    id: UUID
    task_id: UUID
    level: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class TaskLogsResponse(BaseSchema):
    """Schema for task logs response."""
    task_id: UUID
    logs: List[TaskLogEntry]
    total_count: int
    page: int
    page_size: int


# API Key schemas
class APIKeyCreate(BaseSchema):
    """Schema for API key creation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    permissions: List[str] = Field(default_factory=lambda: ["tasks:read", "tasks:create"])


class APIKeyResponse(BaseSchema):
    """Schema for API key response."""
    id: UUID
    name: str
    description: Optional[str]
    key_preview: str  # Only first 8 characters
    permissions: List[str]
    last_used_at: Optional[datetime]
    created_at: datetime
    is_active: bool


class APIKeyCreatedResponse(APIKeyResponse):
    """Schema for newly created API key response."""
    api_key: str  # Full key only shown once


# Subscription schemas
class SubscriptionPlan(BaseSchema):
    """Schema for subscription plan."""
    id: str
    name: str
    tier: SubscriptionTier
    price: float
    currency: str = "USD"
    compute_units_limit: int
    features: List[str]
    billing_interval: str  # monthly, yearly


class SubscriptionResponse(BaseSchema):
    """Schema for user subscription response."""
    id: UUID
    user_id: UUID
    tier: SubscriptionTier
    compute_units_limit: int
    compute_units_used: int
    is_active: bool
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime
    updated_at: datetime


class SubscriptionUpdate(BaseSchema):
    """Schema for subscription updates."""
    tier: Optional[SubscriptionTier] = None


# Analytics schemas
class UsageAnalytics(BaseSchema):
    """Schema for usage analytics."""
    period: str  # daily, weekly, monthly
    start_date: datetime
    end_date: datetime
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    compute_units_consumed: int
    compute_units_limit: int
    top_task_types: List[Dict[str, Union[str, int]]]


class DashboardStats(BaseSchema):
    """Schema for dashboard statistics."""
    active_tasks: int
    completed_tasks_today: int
    compute_units_used_today: int
    compute_units_remaining: int
    success_rate: float
    recent_tasks: List[TaskResponse]


# Error schemas
class ErrorDetail(BaseSchema):
    """Schema for error details."""
    type: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseSchema):
    """Schema for error responses."""
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime
    request_id: Optional[str] = None


class ValidationError(BaseSchema):
    """Schema for validation errors."""
    field: str
    message: str
    rejected_value: Any


class ValidationErrorResponse(BaseSchema):
    """Schema for validation error responses."""
    error: str = "validation_error"
    message: str = "Request validation failed"
    details: List[ValidationError]
    timestamp: datetime


# Health and system schemas
class HealthCheck(BaseSchema):
    """Schema for health check response."""
    status: str = "healthy"
    version: str
    timestamp: datetime
    database: str
    redis: str
    celery: str


class SystemMetrics(BaseSchema):
    """Schema for system metrics."""
    active_users: int
    total_tasks: int
    queue_length: int
    average_response_time: float
    error_rate: float


# Pagination schemas
class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Schema for paginated responses."""
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# Task filtering schemas
class TaskFilters(BaseSchema):
    """Schema for task filtering."""
    status: Optional[List[TaskStatus]] = None
    task_type: Optional[List[TaskType]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    name_contains: Optional[str] = None