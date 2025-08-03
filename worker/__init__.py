"""
Selextract Cloud Worker Package

This package provides the complete worker system for web scraping with Playwright,
proxy rotation, and Celery task queue integration.
"""

__version__ = "1.0.0"
__author__ = "Selextract Cloud Team"
__description__ = "Web scraping worker with Playwright and Celery"

# Import main components for easy access
from .tasks import execute_scraping_task, ScrapingWorker
from .proxies import ProxyManager, initialize_proxy_manager, get_proxy_manager
from .task_schemas import TaskConfig, TaskResult, validate_task_config
from .celery_config import celery_app

__all__ = [
    'execute_scraping_task',
    'ScrapingWorker', 
    'ProxyManager',
    'initialize_proxy_manager',
    'get_proxy_manager',
    'TaskConfig',
    'TaskResult',
    'validate_task_config',
    'celery_app'
]