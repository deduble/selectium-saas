from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid

Base = declarative_base()

class User(Base):
    """User accounts with Google OAuth integration and subscription management"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    google_id = Column(String(255), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String(50), default='free')
    compute_units_remaining = Column(Integer, default=100)
    compute_units_reset_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    usage_analytics = relationship("UsageAnalytics", back_populates="user", cascade="all, delete-orphan")

    def can_create_task(self) -> bool:
        """Check if user has enough compute units to create a task"""
        return self.compute_units_remaining > 0 and self.is_active

    def consume_compute_units(self, units: int) -> bool:
        """Consume compute units and return success status"""
        if self.compute_units_remaining >= units:
            self.compute_units_remaining -= units
            return True
        return False

    def add_compute_units(self, units: int) -> None:
        """Add compute units to user account"""
        self.compute_units_remaining += units

    def reset_compute_units(self, monthly_allowance: int) -> None:
        """Reset compute units for new billing period"""
        self.compute_units_remaining = monthly_allowance
        self.compute_units_reset_date = datetime.now(timezone.utc) + timedelta(days=30)

    def get_active_subscription(self) -> Optional["UserSubscription"]:
        """Get the user's active subscription"""
        for subscription in self.subscriptions:
            if subscription.status == 'active':
                return subscription
        return None

    @property
    def compute_units_limit(self) -> int:
        """Get compute units limit from active subscription plan"""
        active_subscription = self.get_active_subscription()
        if active_subscription and active_subscription.plan:
            return active_subscription.plan.monthly_compute_units
        # Default free tier limit
        return 100

    @property
    def compute_units_used(self) -> int:
        """Calculate compute units used this period"""
        return max(0, self.compute_units_limit - self.compute_units_remaining)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', tier='{self.subscription_tier}')>"

class Task(Base):
    """Scraping tasks with JSONB configuration and execution metadata"""
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)  # Optional task description
    task_type = Column(String(50), nullable=False)  # Task type (simple_scraping, etc.)
    config = Column(JSONB, nullable=False)  # Task configuration schema v1.0
    status = Column(String(50), default='pending', index=True)  # pending, queued, running, completed, failed
    priority = Column(Integer, default=0)
    scheduled_at = Column(DateTime(timezone=True), index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    compute_units_consumed = Column(Integer, default=0)
    estimated_compute_units = Column(Integer, default=1)  # Estimated compute units for task
    progress = Column(Integer, default=0)  # Task progress (0-100)
    error_message = Column(Text)
    result_file_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    # Additional indexes
    __table_args__ = (
        Index('idx_tasks_user_status', 'user_id', 'status'),
        Index('idx_tasks_user_created', 'user_id', 'created_at'),
    )

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate task duration in seconds"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None

    @property
    def duration_minutes(self) -> Optional[int]:
        """Calculate task duration in minutes (for compute unit billing)"""
        duration = self.duration_seconds
        if duration is not None:
            return max(1, int(duration / 60))  # Minimum 1 minute
        return None

    def is_finished(self) -> bool:
        """Check if task is in a terminal state"""
        return self.status in ['completed', 'failed']

    def is_running(self) -> bool:
        """Check if task is currently running"""
        return self.status == 'running'

    def can_be_cancelled(self) -> bool:
        """Check if task can be cancelled"""
        return self.status in ['pending', 'queued']

    def mark_as_started(self) -> None:
        """Mark task as started"""
        self.status = 'running'
        self.started_at = datetime.now(timezone.utc)

    def mark_as_completed(self, result_file_path: Optional[str] = None) -> None:
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_at = datetime.now(timezone.utc)
        if result_file_path:
            self.result_file_path = result_file_path

    def mark_as_failed(self, error_message: str) -> None:
        """Mark task as failed with error message"""
        self.status = 'failed'
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name='{self.name}', status='{self.status}')>"

class TaskLog(Base):
    """Execution logs for tasks with structured metadata"""
    __tablename__ = "task_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    level = Column(String(20), nullable=False)  # info, warning, error, debug
    message = Column(Text, nullable=False)
    log_data = Column("metadata", JSONB)  # Additional structured data
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    task = relationship("Task", back_populates="logs")

    @classmethod
    def create_log(cls, task_id: uuid.UUID, level: str, message: str, log_data: Optional[Dict[str, Any]] = None) -> "TaskLog":
        """Create a new log entry"""
        return cls(
            task_id=task_id,
            level=level,
            message=message,
            log_data=log_data or {}
        )

    def __repr__(self) -> str:
        return f"<TaskLog(task_id={self.task_id}, level='{self.level}', message='{self.message[:50]}...')>"

class SubscriptionPlan(Base):
    """Available billing plans with compute unit limits"""
    __tablename__ = "subscription_plans"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    monthly_compute_units = Column(Integer, nullable=False)
    max_concurrent_tasks = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)  # Price in cents
    lemon_squeezy_variant_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="plan")

    @property
    def price_dollars(self) -> float:
        """Get price in dollars"""
        return self.price_cents / 100.0

    @property
    def is_free(self) -> bool:
        """Check if this is the free plan"""
        return self.price_cents == 0

    def __repr__(self) -> str:
        return f"<SubscriptionPlan(id='{self.id}', name='{self.name}', price=${self.price_dollars})>"

class UserSubscription(Base):
    """Active user subscriptions with billing periods"""
    __tablename__ = "user_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(String(50), ForeignKey("subscription_plans.id"), nullable=False)
    lemon_squeezy_subscription_id = Column(String(100))
    status = Column(String(50), default='active', index=True)  # active, cancelled, expired, past_due
    current_period_start = Column(DateTime(timezone=True), server_default=func.now())
    current_period_end = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    # Additional indexes
    __table_args__ = (
        Index('idx_user_subscriptions_plan', 'plan_id'),
    )

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.status == 'active' and datetime.now(timezone.utc) <= self.current_period_end

    @property
    def days_until_renewal(self) -> int:
        """Get days until next renewal"""
        if self.current_period_end:
            delta = self.current_period_end - datetime.now(timezone.utc)
            return max(0, delta.days)
        return 0

    def is_expired(self) -> bool:
        """Check if subscription has expired"""
        return datetime.now(timezone.utc) > self.current_period_end

    def cancel_subscription(self, at_period_end: bool = True) -> None:
        """Cancel the subscription"""
        if at_period_end:
            self.cancel_at_period_end = True
        else:
            self.status = 'cancelled'

    def renew_subscription(self, new_period_end: datetime) -> None:
        """Renew the subscription for another period"""
        self.current_period_start = self.current_period_end
        self.current_period_end = new_period_end
        self.status = 'active'
        self.cancel_at_period_end = False

    def __repr__(self) -> str:
        return f"<UserSubscription(user_id={self.user_id}, plan_id='{self.plan_id}', status='{self.status}')>"

class APIKey(Base):
    """API keys for programmatic access to the platform"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))  # Optional description for the API key
    key_hash = Column(String(128), nullable=False, index=True)  # Hashed API key
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    last_used_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Additional indexes
    __table_args__ = (
        Index('idx_api_keys_user_active', 'user_id', 'is_active'),
    )

    def mark_as_used(self) -> None:
        """Mark API key as recently used"""
        self.last_used_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        """Deactivate the API key"""
        self.is_active = False

    @property
    def display_key(self) -> str:
        """Get a display-friendly version of the key"""
        return f"{self.key_prefix}{'*' * 24}"

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"

class UsageAnalytics(Base):
    """Daily usage tracking for billing and analytics"""
    __tablename__ = "usage_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    tasks_executed = Column(Integer, default=0)
    compute_units_used = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_analytics")
    
    # Unique constraint on user_id and date
    __table_args__ = (
        Index('idx_usage_analytics_user_date', 'user_id', 'date', unique=True),
    )

    @classmethod
    def create_or_update_daily_usage(cls, user_id: uuid.UUID, date: datetime.date, 
                                   tasks_executed: int = 0, compute_units_used: int = 0, 
                                   api_calls: int = 0) -> "UsageAnalytics":
        """Create or update daily usage analytics"""
        # This method would typically be used with SQLAlchemy session operations
        # to either create a new record or update an existing one
        return cls(
            user_id=user_id,
            date=date,
            tasks_executed=tasks_executed,
            compute_units_used=compute_units_used,
            api_calls=api_calls
        )

    def add_task_execution(self, compute_units: int = 0) -> None:
        """Add a task execution to daily stats"""
        self.tasks_executed += 1
        self.compute_units_used += compute_units

    def add_api_call(self) -> None:
        """Add an API call to daily stats"""
        self.api_calls += 1

    def __repr__(self) -> str:
        return f"<UsageAnalytics(user_id={self.user_id}, date={self.date}, tasks={self.tasks_executed})>"

# Additional utility functions for model operations
def get_or_create_daily_analytics(session, user_id: uuid.UUID, date: datetime.date) -> UsageAnalytics:
    """Get existing daily analytics or create new one"""
    analytics = session.query(UsageAnalytics).filter_by(user_id=user_id, date=date).first()
    if not analytics:
        analytics = UsageAnalytics(user_id=user_id, date=date)
        session.add(analytics)
    return analytics

def create_free_subscription_for_user(session, user: User) -> UserSubscription:
    """Create a free subscription for a new user"""
    free_plan = session.query(SubscriptionPlan).filter_by(id='free').first()
    if not free_plan:
        raise ValueError("Free plan not found in database")
    
    subscription = UserSubscription(
        user_id=user.id,
        plan_id=free_plan.id,
        status='active'
    )
    session.add(subscription)
    return subscription