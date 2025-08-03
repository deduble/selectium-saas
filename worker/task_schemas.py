"""
Task Schema Validation for Selextract Cloud Worker

This module defines Pydantic models for validating scraping task configurations
according to schema v1.0 specifications.
"""

from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, validator, HttpUrl
from enum import Enum


class FieldType(str, Enum):
    """Supported field extraction types"""
    TEXT = "text"
    ATTRIBUTE = "attribute" 
    LINK = "link"
    IMAGE = "image"


class WaitCondition(BaseModel):
    """Wait condition configuration"""
    type: Literal["element", "timeout", "network"] = Field(..., description="Type of wait condition")
    selector: Optional[str] = Field(None, description="CSS selector for element wait")
    timeout: Optional[int] = Field(5000, description="Timeout in milliseconds", ge=1000, le=60000)
    network_idle: Optional[bool] = Field(False, description="Wait for network idle")


class FieldConfig(BaseModel):
    """Configuration for a single field to extract"""
    name: str = Field(..., description="Field name", min_length=1, max_length=100)
    type: FieldType = Field(..., description="Type of field extraction")
    selector: str = Field(..., description="CSS selector for the field", min_length=1)
    attribute: Optional[str] = Field(None, description="Attribute name for attribute/link/image types")
    multiple: bool = Field(False, description="Extract multiple elements")
    required: bool = Field(True, description="Field is required")
    default_value: Optional[str] = Field(None, description="Default value if extraction fails")
    
    @validator('attribute')
    def validate_attribute(cls, v, values):
        """Validate attribute field based on type"""
        field_type = values.get('type')
        if field_type in [FieldType.ATTRIBUTE, FieldType.LINK, FieldType.IMAGE] and not v:
            if field_type == FieldType.LINK:
                return 'href'
            elif field_type == FieldType.IMAGE:
                return 'src'
            else:
                raise ValueError(f'attribute is required for type {field_type}')
        return v


class PaginationConfig(BaseModel):
    """Configuration for pagination handling"""
    enabled: bool = Field(False, description="Enable pagination")
    next_selector: Optional[str] = Field(None, description="CSS selector for next page button/link")
    max_pages: int = Field(10, description="Maximum pages to scrape", ge=1, le=100)
    wait_after_click: int = Field(2000, description="Wait time after clicking next", ge=500, le=10000)
    stop_condition: Optional[str] = Field(None, description="CSS selector to detect end of pagination")
    
    @validator('next_selector')
    def validate_next_selector(cls, v, values):
        """Validate next selector is provided when pagination is enabled"""
        if values.get('enabled') and not v:
            raise ValueError('next_selector is required when pagination is enabled')
        return v


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    requests_per_minute: int = Field(30, description="Requests per minute", ge=1, le=120)
    delay_between_requests: int = Field(1000, description="Delay between requests in ms", ge=100, le=10000)
    random_delay: bool = Field(True, description="Add random delay variation")
    max_random_delay: int = Field(2000, description="Max random delay in ms", ge=0, le=5000)


class ProxyConfig(BaseModel):
    """Proxy configuration"""
    enabled: bool = Field(False, description="Enable proxy usage")
    country: Optional[str] = Field(None, description="Country code for geo-targeting")
    sticky_session: bool = Field(False, description="Use sticky session for consistency")
    max_failures: int = Field(3, description="Max failures before switching proxy", ge=1, le=10)


class BrowserConfig(BaseModel):
    """Browser configuration"""
    headless: bool = Field(True, description="Run browser in headless mode")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    viewport_width: int = Field(1920, description="Viewport width", ge=800, le=3840)
    viewport_height: int = Field(1080, description="Viewport height", ge=600, le=2160)
    javascript_enabled: bool = Field(True, description="Enable JavaScript execution")
    load_images: bool = Field(False, description="Load images for faster scraping")
    timeout: int = Field(30000, description="Page load timeout in ms", ge=5000, le=120000)


class TaskConfig(BaseModel):
    """Complete task configuration schema"""
    # Basic task information
    url: HttpUrl = Field(..., description="Target URL to scrape")
    fields: List[FieldConfig] = Field(..., description="Fields to extract", min_items=1, max_items=50)
    
    # Optional configurations
    pagination: Optional[PaginationConfig] = Field(default_factory=PaginationConfig)
    rate_limit: Optional[RateLimitConfig] = Field(default_factory=RateLimitConfig)
    proxy: Optional[ProxyConfig] = Field(default_factory=ProxyConfig)
    browser: Optional[BrowserConfig] = Field(default_factory=BrowserConfig)
    
    # Wait conditions
    wait_conditions: List[WaitCondition] = Field(default_factory=list, max_items=10)
    
    # Advanced options
    custom_headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    cookies: Optional[Dict[str, str]] = Field(default_factory=dict)
    login_required: bool = Field(False, description="Task requires authentication")
    max_retries: int = Field(3, description="Maximum retry attempts", ge=0, le=10)
    retry_delay: int = Field(5000, description="Delay between retries in ms", ge=1000, le=30000)
    
    @validator('fields')
    def validate_fields(cls, v):
        """Validate field configurations"""
        field_names = [field.name for field in v]
        if len(field_names) != len(set(field_names)):
            raise ValueError('Field names must be unique')
        return v
    
    @validator('custom_headers')
    def validate_headers(cls, v):
        """Validate custom headers"""
        if v:
            # Limit header count and size
            if len(v) > 20:
                raise ValueError('Maximum 20 custom headers allowed')
            for key, value in v.items():
                if len(key) > 100 or len(value) > 500:
                    raise ValueError('Header key/value too long')
        return v
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Reject unknown fields


class TaskResult(BaseModel):
    """Schema for task execution results"""
    task_id: str = Field(..., description="Unique task identifier")
    status: Literal["completed", "failed", "partial"] = Field(..., description="Task execution status")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted data")
    pages_scraped: int = Field(0, description="Number of pages successfully scraped", ge=0)
    total_records: int = Field(0, description="Total records extracted", ge=0)
    compute_units_used: float = Field(0.0, description="Compute units consumed", ge=0.0)
    execution_time: float = Field(0.0, description="Total execution time in seconds", ge=0.0)
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional execution metadata")
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True


class ProxyInfo(BaseModel):
    """Proxy information schema"""
    proxy_id: str = Field(..., description="Proxy identifier")
    endpoint: str = Field(..., description="Proxy endpoint")
    country: Optional[str] = Field(None, description="Proxy country")
    city: Optional[str] = Field(None, description="Proxy city")
    is_healthy: bool = Field(True, description="Proxy health status")
    failure_count: int = Field(0, description="Number of consecutive failures", ge=0)
    last_used: Optional[str] = Field(None, description="Last usage timestamp")
    response_time: Optional[float] = Field(None, description="Average response time in ms")


class TaskValidationError(Exception):
    """Custom exception for task validation errors"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_task_config(config_dict: Dict[str, Any]) -> TaskConfig:
    """
    Validate and parse task configuration dictionary
    
    Args:
        config_dict: Raw configuration dictionary
        
    Returns:
        TaskConfig: Validated configuration object
        
    Raises:
        TaskValidationError: If validation fails
    """
    try:
        return TaskConfig(**config_dict)
    except Exception as e:
        raise TaskValidationError(f"Task configuration validation failed: {str(e)}")


def get_default_task_config() -> Dict[str, Any]:
    """
    Get default task configuration template
    
    Returns:
        Dict: Default configuration dictionary
    """
    return {
        "url": "https://example.com",
        "fields": [
            {
                "name": "title",
                "type": "text",
                "selector": "h1",
                "multiple": False,
                "required": True
            }
        ],
        "pagination": {
            "enabled": False,
            "max_pages": 1
        },
        "rate_limit": {
            "requests_per_minute": 30,
            "delay_between_requests": 1000
        },
        "browser": {
            "headless": True,
            "javascript_enabled": True,
            "load_images": False
        }
    }


# Export all schemas
__all__ = [
    'FieldType',
    'WaitCondition', 
    'FieldConfig',
    'PaginationConfig',
    'RateLimitConfig',
    'ProxyConfig',
    'BrowserConfig',
    'TaskConfig',
    'TaskResult',
    'ProxyInfo',
    'TaskValidationError',
    'validate_task_config',
    'get_default_task_config'
]