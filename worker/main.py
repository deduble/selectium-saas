"""
Main Entry Point for Selextract Cloud Worker

This module initializes and starts the Selextract Cloud worker system
with all necessary components including proxy management, Celery configuration,
and logging setup.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery_config import celery_app, validate_celery_config
from proxies import initialize_proxy_manager, cleanup_proxy_manager
from task_schemas import validate_task_config, get_default_task_config


# Configure logging
def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create logs directory
    log_dir = Path("/app/logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "worker.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configure specific loggers
    loggers_config = {
        'worker': logging.INFO,
        'worker.tasks': logging.INFO,
        'worker.proxies': logging.INFO,
        'worker.celery_config': logging.INFO,
        'celery': logging.WARNING,
        'celery.worker': logging.INFO,
        'celery.task': logging.INFO,
        'playwright': logging.WARNING,
        'urllib3': logging.WARNING,
        'requests': logging.WARNING,
        'aiohttp': logging.WARNING
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Create worker-specific logger
    worker_logger = logging.getLogger('worker.main')
    worker_logger.info("Logging system initialized")
    
    return worker_logger


class WorkerManager:
    """Main worker manager class for handling initialization and lifecycle"""
    
    def __init__(self):
        self.logger = logging.getLogger('worker.main')
        self.proxy_manager_initialized = False
        self.celery_validated = False
        self.shutdown_requested = False
        
    def initialize(self) -> bool:
        """
        Initialize all worker components
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Starting Selextract Cloud Worker initialization...")
            
            # Validate environment variables
            if not self._validate_environment():
                return False
            
            # Validate Celery configuration
            if not self._validate_celery():
                return False
            
            # Initialize proxy manager if configured
            self._initialize_proxy_manager()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Create necessary directories
            self._create_directories()
            
            # Validate system dependencies
            if not self._validate_system_dependencies():
                return False
            
            self.logger.info("Worker initialization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Worker initialization failed: {str(e)}")
            return False
    
    def _validate_environment(self) -> bool:
        """Validate required environment variables"""
        try:
            self.logger.info("Validating environment configuration...")
            
            # Check Redis configuration - use standardized names with legacy fallbacks
            redis_host = os.getenv('SELEXTRACT_REDIS_HOST', os.getenv('REDIS_HOST'))
            redis_port = os.getenv('SELEXTRACT_REDIS_PORT', os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('SELEXTRACT_REDIS_PASSWORD', os.getenv('REDIS_PASSWORD'))
            
            if not redis_host:
                self.logger.warning("Redis host not configured, using default: redis")
            
            self.logger.info(f"Redis configuration: {redis_host}:{redis_port}")
            
            # Check optional but recommended variables
            webshare_api_key = os.getenv('SELEXTRACT_WEBSHARE_API_KEY', os.getenv('WEBSHARE_API_KEY'))
            proxy_country = os.getenv('PROXY_COUNTRY_PREFERENCE')
            celery_concurrency = os.getenv('CELERY_CONCURRENCY', '2')
            celery_env = os.getenv('CELERY_ENV', 'production')
            
            if not webshare_api_key:
                self.logger.info("SELEXTRACT_WEBSHARE_API_KEY not set: Proxy functionality will be disabled")
            else:
                self.logger.info("Webshare API key configured, proxy functionality enabled")
            
            if not proxy_country:
                self.logger.info("PROXY_COUNTRY_PREFERENCE not set: No proxy country preference")
            
            self.logger.info(f"Celery configuration: concurrency={celery_concurrency}, env={celery_env}")
            
            self.logger.info("Environment validation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Environment validation failed: {str(e)}")
            return False
    
    def _validate_celery(self) -> bool:
        """Validate Celery configuration"""
        try:
            self.logger.info("Validating Celery configuration...")
            
            if validate_celery_config():
                self.celery_validated = True
                self.logger.info("Celery configuration is valid")
                return True
            else:
                self.logger.error("Celery configuration validation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Celery validation error: {str(e)}")
            return False
    
    def _initialize_proxy_manager(self) -> None:
        """Initialize proxy manager if configured"""
        try:
            # Use standardized environment variables with legacy fallbacks
            webshare_api_key = os.getenv('SELEXTRACT_WEBSHARE_API_KEY', os.getenv('WEBSHARE_API_KEY'))
            
            if webshare_api_key:
                self.logger.info("Initializing proxy manager...")
                
                success = initialize_proxy_manager(
                    webshare_api_key=webshare_api_key,
                    health_check_interval=int(os.getenv('PROXY_HEALTH_CHECK_INTERVAL', 300)),
                    max_failures=int(os.getenv('PROXY_MAX_FAILURES', 3)),
                    country_preference=os.getenv('PROXY_COUNTRY_PREFERENCE')
                )
                
                if success:
                    self.proxy_manager_initialized = True
                    self.logger.info("Proxy manager initialized successfully")
                else:
                    self.logger.warning("Proxy manager initialization failed, continuing without proxies")
            else:
                self.logger.info("No Webshare API key provided, proxy functionality disabled")
                
        except Exception as e:
            self.logger.error(f"Proxy manager initialization error: {str(e)}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_requested = True
            self.shutdown()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Handle SIGUSR1 for log rotation
        def log_rotation_handler(signum, frame):
            self.logger.info("Received SIGUSR1, rotating logs...")
            # Log rotation would be handled by external logrotate
        
        signal.signal(signal.SIGUSR1, log_rotation_handler)
    
    def _create_directories(self) -> None:
        """Create necessary directories"""
        directories = [
            Path("/app/results"),
            Path("/app/logs"),
            Path("/app/tmp")
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True, parents=True)
            self.logger.debug(f"Created directory: {directory}")
    
    def _validate_system_dependencies(self) -> bool:
        """Validate system dependencies like Playwright browsers"""
        try:
            self.logger.info("Validating system dependencies...")
            
            # Check Playwright browsers
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browsers = ['chromium', 'firefox', 'webkit']
                available_browsers = []
                
                for browser_name in browsers:
                    try:
                        browser = getattr(p, browser_name)
                        # Test browser launch
                        b = browser.launch(headless=True)
                        b.close()
                        available_browsers.append(browser_name)
                        self.logger.debug(f"{browser_name} browser is available")
                    except Exception as e:
                        self.logger.warning(f"{browser_name} browser not available: {str(e)}")
                
                if not available_browsers:
                    self.logger.error("No Playwright browsers are available")
                    return False
                
                self.logger.info(f"Available browsers: {', '.join(available_browsers)}")
            
            # Check file permissions
            test_dirs = ["/app/results", "/app/logs", "/app/tmp"]
            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if not test_path.exists() or not os.access(test_path, os.W_OK):
                    self.logger.error(f"Directory {test_dir} is not writable")
                    return False
            
            self.logger.info("System dependencies validation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"System dependencies validation failed: {str(e)}")
            return False
    
    def run_health_check(self) -> bool:
        """Run comprehensive health check"""
        try:
            self.logger.info("Running health check...")
            
            # Test task schema validation
            try:
                config = get_default_task_config()
                validate_task_config(config)
                self.logger.debug("Task schema validation: OK")
            except Exception as e:
                self.logger.error(f"Task schema validation failed: {str(e)}")
                return False
            
            # Test Celery connectivity
            try:
                celery_app.control.inspect().ping()
                self.logger.debug("Celery connectivity: OK")
            except Exception as e:
                self.logger.warning(f"Celery connectivity check failed: {str(e)}")
                # Don't fail health check as Celery might not be fully started yet
            
            self.logger.info("Health check completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    def shutdown(self) -> None:
        """Graceful shutdown of worker components"""
        try:
            self.logger.info("Starting graceful shutdown...")
            
            # Cleanup proxy manager
            if self.proxy_manager_initialized:
                self.logger.info("Cleaning up proxy manager...")
                cleanup_proxy_manager()
            
            # Stop Celery worker gracefully
            try:
                celery_app.control.shutdown()
                self.logger.info("Celery shutdown signal sent")
            except Exception as e:
                self.logger.warning(f"Error during Celery shutdown: {str(e)}")
            
            self.logger.info("Graceful shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
    
    def start_worker(self, concurrency: Optional[int] = None, loglevel: str = "info") -> None:
        """
        Start Celery worker
        
        Args:
            concurrency: Number of worker processes
            loglevel: Logging level
        """
        try:
            concurrency = concurrency or int(os.getenv('CELERY_CONCURRENCY', 2))
            
            self.logger.info(f"Starting Celery worker with concurrency: {concurrency}")
            
            # Start worker using Celery's API
            argv = [
                'worker',
                f'--concurrency={concurrency}',
                f'--loglevel={loglevel}',
                f'--max-tasks-per-child={os.getenv("CELERY_MAX_TASKS_PER_CHILD", 100)}',
                f'--time-limit={os.getenv("CELERY_TIME_LIMIT", 3600)}',
                f'--soft-time-limit={os.getenv("CELERY_SOFT_TIME_LIMIT", 3300)}'
            ]
            
            celery_app.worker_main(argv)
            
        except KeyboardInterrupt:
            self.logger.info("Worker interrupted by user")
        except Exception as e:
            self.logger.error(f"Worker error: {str(e)}")
        finally:
            self.shutdown()


def main():
    """Main entry point for the worker"""
    
    # Setup logging first
    logger = setup_logging()
    logger.info("=== Selextract Cloud Worker Starting ===")
    
    try:
        # Create and initialize worker manager
        worker_manager = WorkerManager()
        
        if not worker_manager.initialize():
            logger.error("Worker initialization failed, exiting")
            sys.exit(1)
        
        # Run health check
        if not worker_manager.run_health_check():
            logger.error("Health check failed, exiting")
            sys.exit(1)
        
        # Start worker based on command line arguments
        import argparse
        parser = argparse.ArgumentParser(description='Selextract Cloud Worker')
        parser.add_argument('--concurrency', type=int, default=None, 
                          help='Number of worker processes')
        parser.add_argument('--loglevel', default='info', 
                          choices=['debug', 'info', 'warning', 'error'],
                          help='Logging level')
        parser.add_argument('--health-check', action='store_true',
                          help='Run health check and exit')
        
        args = parser.parse_args()
        
        if args.health_check:
            logger.info("Health check requested")
            if worker_manager.run_health_check():
                logger.info("Health check passed")
                sys.exit(0)
            else:
                logger.error("Health check failed")
                sys.exit(1)
        
        # Start the worker
        logger.info("Starting worker...")
        worker_manager.start_worker(
            concurrency=args.concurrency,
            loglevel=args.loglevel
        )
        
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    main()