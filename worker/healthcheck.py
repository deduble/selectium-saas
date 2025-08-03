#!/usr/bin/env python3
"""
Selextract Cloud Worker Health Check Script
Verifies that the worker container is healthy and operational
"""

import sys
import os
import subprocess
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_supervisord():
    """Check if supervisord is running"""
    try:
        result = subprocess.run(['supervisorctl', 'status'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Supervisord check failed: {e}")
        return False

def check_celery_worker():
    """Check if celery worker is running"""
    try:
        result = subprocess.run(['supervisorctl', 'status', 'celery-worker'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'RUNNING' in result.stdout:
            return True
        logger.error(f"Celery worker not running: {result.stdout}")
        return False
    except Exception as e:
        logger.error(f"Celery worker check failed: {e}")
        return False

def check_celery_beat():
    """Check if celery beat is running"""
    try:
        result = subprocess.run(['supervisorctl', 'status', 'celery-beat'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'RUNNING' in result.stdout:
            return True
        logger.error(f"Celery beat not running: {result.stdout}")
        return False
    except Exception as e:
        logger.error(f"Celery beat check failed: {e}")
        return False

def check_celery_connectivity():
    """Check if celery can connect to broker and backend"""
    try:
        # Change to app directory for proper imports
        os.chdir('/app')
        sys.path.insert(0, '/app')
        
        # Try to import and ping celery
        from main import celery_app
        
        # Check broker connectivity
        result = celery_app.control.ping(timeout=5)
        if not result:
            logger.error("Celery broker ping failed")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Celery connectivity check failed: {e}")
        return False

def main():
    """Main health check function"""
    checks = [
        ("Supervisord", check_supervisord),
        ("Celery Worker", check_celery_worker),
        ("Celery Beat", check_celery_beat),
        ("Celery Connectivity", check_celery_connectivity)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                failed_checks.append(check_name)
                logger.error(f"Health check failed: {check_name}")
        except Exception as e:
            failed_checks.append(check_name)
            logger.error(f"Health check error for {check_name}: {e}")
    
    if failed_checks:
        logger.error(f"Health check failed for: {', '.join(failed_checks)}")
        sys.exit(1)
    else:
        logger.info("All health checks passed")
        sys.exit(0)

if __name__ == "__main__":
    main()