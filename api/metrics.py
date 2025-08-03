"""
Prometheus metrics integration for Selextract Cloud API.

This module provides comprehensive metrics collection for monitoring
system performance, application health, and business metrics.
"""

from prometheus_client import (
    Counter, 
    Histogram, 
    Gauge, 
    generate_latest, 
    CONTENT_TYPE_LATEST,
    multiprocess,
    CollectorRegistry
)
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import asyncio
from typing import Dict, Any
import logging
from sqlalchemy.orm import Session
from database import get_db
from models import User, Task

logger = logging.getLogger(__name__)

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# Application Metrics
active_connections = Gauge(
    'selextract_active_connections',
    'Number of active HTTP connections'
)

# Business Metrics
user_registrations_total = Counter(
    'selextract_user_registrations_total',
    'Total number of user registrations'
)

compute_units_consumed_total = Counter(
    'selextract_compute_units_consumed_total',
    'Total compute units consumed',
    ['user_id', 'task_type']
)

compute_units_remaining = Gauge(
    'selextract_user_compute_units_remaining',
    'Remaining compute units per user',
    ['user_id']
)

tasks_created_total = Counter(
    'selextract_tasks_created_total',
    'Total tasks created',
    ['task_type', 'user_id']
)

tasks_completed_total = Counter(
    'selextract_tasks_completed_total',
    'Total tasks completed',
    ['task_type', 'status']
)

task_execution_duration_seconds = Histogram(
    'selextract_task_execution_duration_seconds',
    'Task execution duration in seconds',
    ['task_type'],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
)

# Proxy Metrics
proxy_requests_total = Counter(
    'selextract_proxy_requests_total',
    'Total proxy requests',
    ['proxy_provider']
)

proxy_failures_total = Counter(
    'selextract_proxy_failures_total',
    'Total proxy failures',
    ['proxy_provider', 'failure_type']
)

# Security Metrics
failed_login_attempts_total = Counter(
    'selextract_failed_login_attempts_total',
    'Total failed login attempts',
    ['ip_address']
)

rate_limit_violations_total = Counter(
    'selextract_rate_limit_violations_total',
    'Total rate limit violations',
    ['endpoint', 'ip_address']
)

# System Health Metrics
database_connections_active = Gauge(
    'selextract_database_connections_active',
    'Active database connections'
)

cache_hit_ratio = Gauge(
    'selextract_cache_hit_ratio',
    'Cache hit ratio',
    ['cache_type']
)

# User Activity Metrics
active_users_total = Gauge(
    'selextract_active_users_total',
    'Number of active users in the last period',
    ['period']
)

user_sessions_active = Gauge(
    'selextract_user_sessions_active',
    'Number of active user sessions'
)

# API Endpoint Specific Metrics
api_endpoint_requests = Counter(
    'selextract_api_endpoint_requests_total',
    'Total requests per API endpoint',
    ['endpoint', 'method', 'version']
)

api_endpoint_errors = Counter(
    'selextract_api_endpoint_errors_total',
    'Total errors per API endpoint',
    ['endpoint', 'method', 'error_type']
)

# Task Queue Metrics
celery_queue_length = Gauge(
    'celery_queue_length',
    'Number of tasks in Celery queue',
    ['queue']
)

celery_workers_active = Gauge(
    'celery_workers_active',
    'Number of active Celery workers'
)

celery_task_runtime_seconds = Histogram(
    'celery_task_runtime_seconds',
    'Celery task runtime in seconds',
    ['task_name'],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
)

celery_task_failed_total = Counter(
    'celery_task_failed_total',
    'Total failed Celery tasks',
    ['task_name', 'error_type']
)

celery_task_timeout_total = Counter(
    'celery_task_timeout_total',
    'Total timed out Celery tasks',
    ['task_name']
)

celery_task_total = Counter(
    'celery_task_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

# Worker Memory Metrics
celery_worker_memory_usage = Gauge(
    'celery_worker_memory_usage',
    'Memory usage of Celery workers',
    ['worker']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for collecting Prometheus metrics."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Track active connections
        active_connections.inc()
        
        try:
            # Get request size
            request_size = int(request.headers.get('content-length', 0))
            
            # Process request
            response = await call_next(request)
            
            # Calculate metrics
            duration = time.time() - start_time
            method = request.method
            endpoint = self._get_endpoint_name(request)
            status_code = str(response.status_code)
            
            # Get response size
            response_size = int(response.headers.get('content-length', 0))
            
            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            if request_size > 0:
                http_request_size_bytes.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(request_size)
            
            if response_size > 0:
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(response_size)
            
            # API specific metrics
            api_endpoint_requests.labels(
                endpoint=endpoint,
                method=method,
                version='v1'
            ).inc()
            
            # Track errors
            if response.status_code >= 400:
                error_type = self._get_error_type(response.status_code)
                api_endpoint_errors.labels(
                    endpoint=endpoint,
                    method=method,
                    error_type=error_type
                ).inc()
            
            return response
            
        except Exception as e:
            # Record exception metrics
            endpoint = self._get_endpoint_name(request)
            api_endpoint_errors.labels(
                endpoint=endpoint,
                method=request.method,
                error_type='exception'
            ).inc()
            
            logger.error(f"Error in metrics middleware: {e}")
            raise
        
        finally:
            # Decrease active connections
            active_connections.dec()
    
    def _get_endpoint_name(self, request: Request) -> str:
        """Extract endpoint name from request."""
        if hasattr(request, 'url'):
            path = request.url.path
            # Normalize path parameters
            if '/tasks/' in path and path.count('/') > 2:
                return '/tasks/{id}'
            elif '/users/' in path and path.count('/') > 2:
                return '/users/{id}'
            return path
        return 'unknown'
    
    def _get_error_type(self, status_code: int) -> str:
        """Categorize HTTP status codes."""
        if 400 <= status_code < 500:
            return 'client_error'
        elif 500 <= status_code < 600:
            return 'server_error'
        else:
            return 'other'


def setup_metrics(app: FastAPI):
    """Setup Prometheus metrics for FastAPI application."""
    
    # Add middleware properly
    app.add_middleware(PrometheusMiddleware)
    
    # Add metrics endpoint
    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        try:
            # Update business metrics
            await update_business_metrics()
            
            # Generate metrics
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            return generate_latest(registry)
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return generate_latest()


async def update_business_metrics():
    """Update business and user activity metrics."""
    try:
        # This would typically get a database session
        # For now, we'll update with placeholder logic
        
        # Update active users (would query database)
        # active_users_total.labels(period='1h').set(active_users_1h)
        # active_users_total.labels(period='24h').set(active_users_24h)
        
        # Update user sessions (would query session store)
        # user_sessions_active.set(active_sessions_count)
        
        pass
    except Exception as e:
        logger.error(f"Error updating business metrics: {e}")


def record_user_registration():
    """Record a new user registration."""
    user_registrations_total.inc()


def record_compute_unit_consumption(user_id: str, task_type: str, units: int):
    """Record compute unit consumption."""
    compute_units_consumed_total.labels(
        user_id=user_id,
        task_type=task_type
    ).inc(units)


def update_user_compute_units(user_id: str, remaining_units: int):
    """Update remaining compute units for a user."""
    compute_units_remaining.labels(user_id=user_id).set(remaining_units)


def record_task_creation(task_type: str, user_id: str):
    """Record a new task creation."""
    tasks_created_total.labels(
        task_type=task_type,
        user_id=user_id
    ).inc()


def record_task_completion(task_type: str, status: str, duration: float):
    """Record task completion."""
    tasks_completed_total.labels(
        task_type=task_type,
        status=status
    ).inc()
    
    task_execution_duration_seconds.labels(
        task_type=task_type
    ).observe(duration)


def record_proxy_request(proxy_provider: str):
    """Record a proxy request."""
    proxy_requests_total.labels(proxy_provider=proxy_provider).inc()


def record_proxy_failure(proxy_provider: str, failure_type: str):
    """Record a proxy failure."""
    proxy_failures_total.labels(
        proxy_provider=proxy_provider,
        failure_type=failure_type
    ).inc()


def record_failed_login(ip_address: str):
    """Record a failed login attempt."""
    failed_login_attempts_total.labels(ip_address=ip_address).inc()


def record_rate_limit_violation(endpoint: str, ip_address: str):
    """Record a rate limit violation."""
    rate_limit_violations_total.labels(
        endpoint=endpoint,
        ip_address=ip_address
    ).inc()


def update_database_connections(active_count: int):
    """Update active database connections count."""
    database_connections_active.set(active_count)


def update_cache_hit_ratio(cache_type: str, ratio: float):
    """Update cache hit ratio."""
    cache_hit_ratio.labels(cache_type=cache_type).set(ratio)


def update_celery_queue_length(queue: str, length: int):
    """Update Celery queue length."""
    celery_queue_length.labels(queue=queue).set(length)


def update_celery_workers_active(count: int):
    """Update active Celery workers count."""
    celery_workers_active.set(count)


def record_celery_task_runtime(task_name: str, runtime: float):
    """Record Celery task runtime."""
    celery_task_runtime_seconds.labels(task_name=task_name).observe(runtime)


def record_celery_task_failure(task_name: str, error_type: str):
    """Record Celery task failure."""
    celery_task_failed_total.labels(
        task_name=task_name,
        error_type=error_type
    ).inc()


def record_celery_task_timeout(task_name: str):
    """Record Celery task timeout."""
    celery_task_timeout_total.labels(task_name=task_name).inc()


def record_celery_task(task_name: str, status: str):
    """Record Celery task execution."""
    celery_task_total.labels(
        task_name=task_name,
        status=status
    ).inc()


def update_worker_memory_usage(worker: str, memory_bytes: int):
    """Update worker memory usage."""
    celery_worker_memory_usage.labels(worker=worker).set(memory_bytes)


# Health check metrics
def get_health_metrics() -> Dict[str, Any]:
    """Get current health metrics for health check endpoint."""
    try:
        return {
            'active_connections': getattr(active_connections, '_value', 0),
            'total_requests': 0,  # Simplified for health check
            'active_workers': getattr(celery_workers_active, '_value', 0),
            'queue_length': 0  # Simplified for health check
        }
    except Exception as e:
        logger.error(f"Error getting health metrics: {e}")
        return {
            'active_connections': 0,
            'total_requests': 0,
            'active_workers': 0,
            'queue_length': 0
        }