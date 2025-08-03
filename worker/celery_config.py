"""
Celery Configuration for Selextract Cloud Worker

This module provides production-ready Celery settings with queue configuration,
retry policies, error handling, and task routing.
"""

import os
from datetime import timedelta
from kombu import Queue, Exchange

# Redis connection settings - use standardized names with legacy fallbacks
REDIS_HOST = os.getenv('SELEXTRACT_REDIS_HOST', os.getenv('REDIS_HOST', 'redis'))
REDIS_PORT = int(os.getenv('SELEXTRACT_REDIS_PORT', os.getenv('REDIS_PORT', 6379)))
REDIS_DB = int(os.getenv('SELEXTRACT_REDIS_DB', os.getenv('REDIS_DB', 0)))
REDIS_PASSWORD = os.getenv('SELEXTRACT_REDIS_PASSWORD', os.getenv('REDIS_PASSWORD', ''))

# Build Redis URL
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Celery configuration
class CeleryConfig:
    """Celery configuration class"""
    
    # Broker settings
    broker_url = REDIS_URL
    result_backend = REDIS_URL
    
    # Task serialization
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = 'UTC'
    enable_utc = True
    
    # Task execution settings
    task_always_eager = False  # Set to True for testing
    task_eager_propagates = False
    task_ignore_result = False
    task_store_eager_result = True
    
    # Worker settings
    worker_prefetch_multiplier = 1  # Prevent memory issues with large tasks
    worker_max_tasks_per_child = 100  # Restart worker after 100 tasks
    worker_disable_rate_limits = False
    worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
    worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
    
    # Task result settings
    result_expires = 3600  # Results expire after 1 hour
    result_compression = 'gzip'
    result_backend_transport_options = {
        'master_name': 'selextract',
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        }
    }
    
    # Task routing and queues
    task_default_queue = 'default'
    task_default_exchange = 'default'
    task_default_exchange_type = 'direct'
    task_default_routing_key = 'default'
    
    # Define task queues
    task_queues = (
        # High priority queue for urgent tasks
        Queue('high_priority', 
              Exchange('high_priority', type='direct'), 
              routing_key='high_priority',
              queue_arguments={'x-max-priority': 10}),
        
        # Default queue for regular scraping tasks
        Queue('default', 
              Exchange('default', type='direct'), 
              routing_key='default',
              queue_arguments={'x-max-priority': 5}),
        
        # Low priority queue for background tasks
        Queue('low_priority', 
              Exchange('low_priority', type='direct'), 
              routing_key='low_priority',
              queue_arguments={'x-max-priority': 1}),
        
        # Separate queue for cleanup tasks
        Queue('cleanup', 
              Exchange('cleanup', type='direct'), 
              routing_key='cleanup',
              queue_arguments={'x-max-priority': 1}),
    )
    
    # Task routing configuration
    task_routes = {
        # Scraping tasks go to default queue
        'execute_scraping_task': {'queue': 'default', 'routing_key': 'default'},
        
        # Background maintenance tasks
        'cleanup_old_results': {'queue': 'cleanup', 'routing_key': 'cleanup'},
        'refresh_user_compute_units': {'queue': 'low_priority', 'routing_key': 'low_priority'},
        'proxy_health_check': {'queue': 'low_priority', 'routing_key': 'low_priority'},
        
        # High priority tasks (if any)
        'urgent_*': {'queue': 'high_priority', 'routing_key': 'high_priority'},
    }
    
    # Retry configuration
    task_acks_late = True  # Acknowledge task after completion
    task_reject_on_worker_lost = True  # Reject tasks if worker dies
    
    # Default retry settings for all tasks
    task_annotations = {
        '*': {
            'rate_limit': '100/m',  # 100 tasks per minute max
            'time_limit': 1800,     # 30 minutes hard timeout
            'soft_time_limit': 1500, # 25 minutes soft timeout
            'retry_backoff': True,   # Exponential backoff
            'retry_backoff_max': 600, # Max 10 minutes between retries
            'retry_jitter': True,    # Add random jitter to retries
            'max_retries': 3,        # Maximum 3 retries
        },
        
        # Specific task configurations
        'execute_scraping_task': {
            'rate_limit': '50/m',    # 50 scraping tasks per minute max
            'time_limit': 3600,      # 1 hour hard timeout for scraping
            'soft_time_limit': 3300, # 55 minutes soft timeout
            'max_retries': 5,        # Allow more retries for scraping
        },
        
        'cleanup_old_results': {
            'rate_limit': '1/h',     # Once per hour max
            'time_limit': 300,       # 5 minutes timeout
            'max_retries': 1,        # Only 1 retry for cleanup
        },
        
        'proxy_health_check': {
            'rate_limit': '12/h',    # Every 5 minutes max
            'time_limit': 180,       # 3 minutes timeout
            'max_retries': 2,        # 2 retries for health checks
        }
    }
    
    # Monitoring and logging
    worker_send_task_events = True
    task_send_sent_event = True
    
    # Security settings
    worker_hijack_root_logger = False
    worker_log_color = False
    
    # Beat scheduler settings for periodic tasks
    beat_schedule = {
        # Cleanup old result files daily at 2 AM
        'cleanup-old-results': {
            'task': 'cleanup_old_results',
            'schedule': timedelta(hours=24),
            'args': (7,),  # Delete files older than 7 days
            'options': {'queue': 'cleanup'}
        },
        
        # Refresh user compute units every hour
        'refresh-compute-units': {
            'task': 'refresh_user_compute_units',
            'schedule': timedelta(hours=1),
            'options': {'queue': 'low_priority'}
        },
        
        # Proxy health check every 5 minutes
        'proxy-health-check': {
            'task': 'proxy_health_check',
            'schedule': timedelta(minutes=5),
            'options': {'queue': 'low_priority'}
        },
    }
    
    # Error handling
    task_soft_time_limit_delay = 10  # Grace period after soft timeout
    
    # Connection pool settings
    broker_pool_limit = 10
    broker_connection_retry_on_startup = True
    broker_connection_retry = True
    broker_connection_max_retries = 10
    
    # Redis-specific settings
    redis_max_connections = 20
    redis_socket_keepalive = True
    redis_socket_keepalive_options = {
        'TCP_KEEPIDLE': 1,
        'TCP_KEEPINTVL': 3,
        'TCP_KEEPCNT': 5,
    }


# Create Celery app instance
from celery import Celery

# Initialize Celery app
celery_app = Celery('selextract_worker')

# Load configuration
celery_app.config_from_object(CeleryConfig)

# Auto-discover tasks
celery_app.autodiscover_tasks(['tasks'])

# Additional Celery configuration
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup additional periodic tasks if needed"""
    pass


# Task error handlers
@celery_app.task(bind=True)
def task_failure_handler(self, task_id, error, traceback):
    """Handle task failures"""
    print(f'Task {task_id} failed: {error}')
    # Here you could send notifications, log to external systems, etc.


# Celery signals for monitoring
from celery.signals import (
    task_prerun, task_postrun, task_failure, task_success,
    worker_ready, worker_shutdown
)
import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Called before task execution"""
    logger.info(f'Task {task_id} ({task.name}) starting with args: {args}')


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Called after task execution"""
    logger.info(f'Task {task_id} ({task.name}) finished with state: {state}')


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kwds):
    """Called on task failure"""
    logger.error(f'Task {task_id} ({sender.name}) failed: {exception}')


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Called on task success"""
    logger.info(f'Task {sender.request.id} ({sender.name}) succeeded')


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Called when worker is ready"""
    logger.info(f'Worker {sender.hostname} is ready')


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Called when worker shuts down"""
    logger.info(f'Worker {sender.hostname} is shutting down')


# Health check task for monitoring
@celery_app.task(name='health_check')
def health_check():
    """Simple health check task for monitoring"""
    return {
        'status': 'healthy',
        'timestamp': os.popen('date').read().strip(),
        'worker_id': os.getpid()
    }


# Task state tracking
class TaskStateTracker:
    """Utility class for tracking task states"""
    
    @staticmethod
    def update_task_state(task_id: str, state: str, meta: dict = None):
        """Update task state in backend"""
        try:
            # This would typically update the database or cache
            # with task execution state for monitoring
            logger.info(f'Task {task_id} state updated to {state}')
            if meta:
                logger.debug(f'Task {task_id} metadata: {meta}')
        except Exception as e:
            logger.error(f'Failed to update task state: {e}')


# Configuration validation
def validate_celery_config():
    """Validate Celery configuration"""
    try:
        # Test Redis connection
        from redis import Redis
        redis_client = Redis.from_url(REDIS_URL)
        redis_client.ping()
        logger.info('Redis connection successful')
        
        # Validate queue configuration
        for queue in CeleryConfig.task_queues:
            logger.info(f'Queue configured: {queue.name}')
        
        return True
        
    except Exception as e:
        logger.error(f'Celery configuration validation failed: {e}')
        return False


# Environment-specific overrides
if os.getenv('CELERY_ENV') == 'development':
    # Development overrides
    CeleryConfig.task_always_eager = True
    CeleryConfig.task_eager_propagates = True
    CeleryConfig.worker_log_format = '[DEV] %(message)s'
    logger.info('Using development Celery configuration')

elif os.getenv('CELERY_ENV') == 'testing':
    # Testing overrides
    CeleryConfig.task_always_eager = True
    CeleryConfig.task_store_eager_result = True
    CeleryConfig.result_expires = 60
    logger.info('Using testing Celery configuration')

else:
    # Production configuration (default)
    logger.info('Using production Celery configuration')


# Export configuration
__all__ = [
    'celery_app',
    'CeleryConfig', 
    'validate_celery_config',
    'TaskStateTracker',
    'health_check'
]