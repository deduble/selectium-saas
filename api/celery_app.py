"""
Celery configuration for task queue management and worker coordination.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from database import DATABASE_URL
from models import Task, TaskLog, User, UsageAnalytics
from schemas import TaskStatus


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://:devpassword@localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app
celery_app = Celery(
    "selectium_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["api.celery_app"]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "api.celery_app.execute_scraping_task": {"queue": "scraping"},
        "api.celery_app.execute_monitoring_task": {"queue": "monitoring"},
        "api.celery_app.cleanup_expired_tasks": {"queue": "maintenance"},
    },
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task time limits
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=False,
    
    # Task retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-tasks": {
            "task": "api.celery_app.cleanup_expired_tasks",
            "schedule": timedelta(hours=6),  # Every 6 hours
        },
        "update-task-metrics": {
            "task": "api.celery_app.update_task_metrics", 
            "schedule": timedelta(minutes=15),  # Every 15 minutes
        },
    },
)

# Database setup for Celery workers
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Get database session for Celery tasks."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def log_task_event(task_id: UUID, level: str, message: str, metadata: Optional[Dict[str, Any]] = None):
    """Log task execution event to database."""
    try:
        db = get_db_session()
        log_entry = TaskLog.create_log(
            task_id=task_id,
            level=level,
            message=message,
            metadata=metadata
        )
        db.add(log_entry)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to log task event: {e}")


def update_task_status(task_id: UUID, status: TaskStatus, **kwargs):
    """Update task status in database."""
    try:
        db = get_db_session()
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = status.value
            
            # Update timestamps based on status
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.now(timezone.utc)
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.now(timezone.utc)
                
                # Calculate compute units consumed (1 CU per minute)
                if task.started_at:
                    duration_minutes = max(1, int((task.completed_at - task.started_at).total_seconds() / 60))
                    task.compute_units_consumed = duration_minutes
                    
                    # Update user's compute units
                    user = task.user
                    if user:
                        user.consume_compute_units(duration_minutes)
                        
                        # Update daily analytics
                        today = datetime.now(timezone.utc).date()
                        analytics = db.query(UsageAnalytics).filter(
                            UsageAnalytics.user_id == user.id,
                            UsageAnalytics.date == today
                        ).first()
                        
                        if not analytics:
                            analytics = UsageAnalytics(
                                user_id=user.id,
                                date=today,
                                tasks_executed=0,
                                compute_units_used=0
                            )
                            db.add(analytics)
                        
                        analytics.add_task_execution(duration_minutes)
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            db.commit()
            
        db.close()
    except Exception as e:
        logger.error(f"Failed to update task status: {e}")


# Celery signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    """Handle task pre-execution."""
    if args and len(args) > 0:
        try:
            task_uuid = UUID(args[0])
            update_task_status(task_uuid, TaskStatus.RUNNING)
            log_task_event(task_uuid, "info", f"Task {task.name} started execution")
            logger.info(f"Starting task {task_uuid}")
        except (ValueError, IndexError):
            logger.warning(f"Could not parse task UUID from args: {args}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw):
    """Handle task post-execution."""
    if args and len(args) > 0:
        try:
            task_uuid = UUID(args[0])
            if state == "SUCCESS":
                update_task_status(
                    task_uuid, 
                    TaskStatus.COMPLETED,
                    result_file_path=retval.get("result_file_path") if isinstance(retval, dict) else None
                )
                log_task_event(task_uuid, "info", f"Task {task.name} completed successfully")
                logger.info(f"Task {task_uuid} completed successfully")
            else:
                update_task_status(task_uuid, TaskStatus.FAILED, error_message=f"Task failed with state: {state}")
                log_task_event(task_uuid, "error", f"Task {task.name} failed with state: {state}")
                logger.error(f"Task {task_uuid} failed with state: {state}")
        except (ValueError, IndexError):
            logger.warning(f"Could not parse task UUID from args: {args}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kw):
    """Handle task failure."""
    # Try to extract task UUID from sender name or other sources
    error_message = f"Task failed with exception: {str(exception)}"
    logger.error(f"Task {task_id} failed: {error_message}")
    
    # If we can determine the task UUID, update the database
    # This is a fallback in case the postrun handler doesn't catch it


# Task definitions
@celery_app.task(bind=True, name="api.celery_app.execute_scraping_task")
def execute_scraping_task(self, task_id: str, config: Dict[str, Any]):
    """
    Execute a scraping task.
    
    Args:
        task_id: UUID of the task to execute
        config: Task configuration dictionary
        
    Returns:
        Dict with execution results
    """
    task_uuid = UUID(task_id)
    
    try:
        log_task_event(task_uuid, "info", "Starting scraping execution", {"config": config})
        
        # Import here to avoid circular imports
        from worker.scraper import ScrapingEngine
        
        # Initialize scraping engine
        scraper = ScrapingEngine(config)
        
        # Execute scraping
        result = scraper.execute()
        
        # Save results to file system
        result_file_path = scraper.save_results(result)
        
        log_task_event(task_uuid, "info", f"Scraping completed. Results saved to: {result_file_path}")
        
        return {
            "status": "success",
            "result_file_path": result_file_path,
            "records_scraped": len(result.get("data", [])),
            "execution_time": result.get("execution_time", 0)
        }
        
    except Exception as exc:
        error_msg = f"Scraping task failed: {str(exc)}"
        log_task_event(task_uuid, "error", error_msg, {"exception": str(exc)})
        
        # Retry the task up to 3 times
        if self.request.retries < 3:
            log_task_event(task_uuid, "warning", f"Retrying task (attempt {self.request.retries + 1}/3)")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        
        # Mark as failed after max retries
        update_task_status(task_uuid, TaskStatus.FAILED, error_message=error_msg)
        raise exc


@celery_app.task(bind=True, name="api.celery_app.execute_monitoring_task")
def execute_monitoring_task(self, task_id: str, config: Dict[str, Any]):
    """
    Execute a monitoring task.
    
    Args:
        task_id: UUID of the task to execute
        config: Task configuration dictionary
        
    Returns:
        Dict with execution results
    """
    task_uuid = UUID(task_id)
    
    try:
        log_task_event(task_uuid, "info", "Starting monitoring execution", {"config": config})
        
        # Import here to avoid circular imports
        from worker.monitor import MonitoringEngine
        
        # Initialize monitoring engine
        monitor = MonitoringEngine(config)
        
        # Execute monitoring
        result = monitor.execute()
        
        # Check for changes and send notifications if needed
        if result.get("changes_detected"):
            monitor.send_notifications(result)
        
        # Save results
        result_file_path = monitor.save_results(result)
        
        log_task_event(task_uuid, "info", f"Monitoring completed. Results saved to: {result_file_path}")
        
        return {
            "status": "success",
            "result_file_path": result_file_path,
            "changes_detected": result.get("changes_detected", False),
            "execution_time": result.get("execution_time", 0)
        }
        
    except Exception as exc:
        error_msg = f"Monitoring task failed: {str(exc)}"
        log_task_event(task_uuid, "error", error_msg, {"exception": str(exc)})
        
        # Retry the task
        if self.request.retries < 3:
            log_task_event(task_uuid, "warning", f"Retrying task (attempt {self.request.retries + 1}/3)")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        
        # Mark as failed after max retries
        update_task_status(task_uuid, TaskStatus.FAILED, error_message=error_msg)
        raise exc


@celery_app.task(name="api.celery_app.cleanup_expired_tasks")
def cleanup_expired_tasks():
    """Clean up old completed/failed tasks and their logs."""
    try:
        db = get_db_session()
        
        # Define cleanup thresholds
        completed_task_retention = timedelta(days=30)
        failed_task_retention = timedelta(days=7)
        log_retention = timedelta(days=14)
        
        cutoff_completed = datetime.now(timezone.utc) - completed_task_retention
        cutoff_failed = datetime.now(timezone.utc) - failed_task_retention
        cutoff_logs = datetime.now(timezone.utc) - log_retention
        
        # Clean up old completed tasks
        completed_count = db.query(Task).filter(
            Task.status == TaskStatus.COMPLETED.value,
            Task.completed_at < cutoff_completed
        ).delete()
        
        # Clean up old failed tasks
        failed_count = db.query(Task).filter(
            Task.status == TaskStatus.FAILED.value,
            Task.completed_at < cutoff_failed
        ).delete()
        
        # Clean up old logs
        logs_count = db.query(TaskLog).filter(
            TaskLog.timestamp < cutoff_logs
        ).delete()
        
        db.commit()
        db.close()
        
        logger.info(f"Cleanup completed: {completed_count} completed tasks, "
                   f"{failed_count} failed tasks, {logs_count} log entries removed")
        
        return {
            "completed_tasks_removed": completed_count,
            "failed_tasks_removed": failed_count,
            "log_entries_removed": logs_count
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise


@celery_app.task(name="api.celery_app.update_task_metrics")
def update_task_metrics():
    """Update task execution metrics and queue status."""
    try:
        db = get_db_session()
        
        # Get queue statistics
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}
        
        # Count active tasks by type
        total_active = sum(len(tasks) for tasks in active_tasks.values())
        total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
        
        # Update database with current metrics
        # This could be stored in a metrics table for monitoring
        
        db.close()
        
        logger.info(f"Metrics updated: {total_active} active tasks, {total_scheduled} scheduled tasks")
        
        return {
            "active_tasks": total_active,
            "scheduled_tasks": total_scheduled,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics update failed: {e}")
        raise


def submit_task(task_id: UUID, task_type: str, config: Dict[str, Any], priority: int = 5) -> str:
    """
    Submit a task to the Celery queue.
    
    Args:
        task_id: UUID of the task
        task_type: Type of task (scraping, monitoring)
        config: Task configuration
        priority: Task priority (1-10, higher is more priority)
        
    Returns:
        Celery task ID
    """
    task_id_str = str(task_id)
    
    # Select appropriate task based on type
    if task_type in ["simple_scraping", "advanced_scraping", "bulk_scraping"]:
        task = execute_scraping_task
    elif task_type == "monitoring":
        task = execute_monitoring_task
    else:
        raise ValueError(f"Unknown task type: {task_type}")
    
    # Submit task with priority
    result = task.apply_async(
        args=[task_id_str, config],
        priority=priority,
        routing_key="scraping" if "scraping" in task_type else "monitoring"
    )
    
    logger.info(f"Submitted task {task_id} to queue with Celery ID: {result.id}")
    
    return result.id


def cancel_task(celery_task_id: str) -> bool:
    """
    Cancel a running Celery task.
    
    Args:
        celery_task_id: Celery task ID
        
    Returns:
        True if task was cancelled, False otherwise
    """
    try:
        celery_app.control.revoke(celery_task_id, terminate=True)
        logger.info(f"Cancelled Celery task: {celery_task_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {celery_task_id}: {e}")
        return False


def get_task_status(celery_task_id: str) -> Dict[str, Any]:
    """
    Get the status of a Celery task.
    
    Args:
        celery_task_id: Celery task ID
        
    Returns:
        Task status information
    """
    try:
        result = celery_app.AsyncResult(celery_task_id)
        return {
            "state": result.state,
            "info": result.info,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None
        }
    except Exception as e:
        logger.error(f"Failed to get task status for {celery_task_id}: {e}")
        return {"state": "UNKNOWN", "error": str(e)}


def get_queue_stats() -> Dict[str, Any]:
    """Get statistics about task queues."""
    try:
        inspect = celery_app.control.inspect()
        
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        
        stats = {
            "active_tasks": sum(len(tasks) for tasks in active.values()),
            "scheduled_tasks": sum(len(tasks) for tasks in scheduled.values()),
            "reserved_tasks": sum(len(tasks) for tasks in reserved.values()),
            "workers": list(active.keys()) if active else [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        return {"error": str(e)}


# Health check for Celery
def health_check() -> Dict[str, str]:
    """Check Celery health status."""
    try:
        # Check if broker is reachable
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            return {"status": "healthy", "workers": len(stats)}
        else:
            return {"status": "unhealthy", "error": "No workers available"}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}