"""
Compute Unit Management Service

Handles compute unit allocation, tracking, renewal, and overage management
for the Selextract Cloud billing system.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database import get_db
from models import User, ComputeUnitTransaction, ComputeUnitUsage, SubscriptionPlan, UserSubscription

logger = logging.getLogger(__name__)

class ComputeUnitError(Exception):
    """Base exception for compute unit operations"""
    pass

class InsufficientComputeUnitsError(ComputeUnitError):
    """Raised when user doesn't have enough compute units"""
    pass

class OverageExceededError(ComputeUnitError):
    """Raised when overage limit is exceeded"""
    pass

class ComputeUnitManager:
    """Manages compute unit allocation, consumption, and tracking"""
    
    def __init__(self, db):
        self.db = db
    
    def get_user_compute_units(self, user_id: int) -> Dict:
        """Get current compute unit status for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ComputeUnitError(f"User {user_id} not found")
        
        # Get current period info
        current_period = self._get_current_billing_period(user_id)
        
        # Calculate total allocated units for current period
        total_allocated = self._calculate_allocated_units(user_id, current_period)
        
        # Calculate consumed units for current period
        consumed_units = self._calculate_consumed_units(user_id, current_period)
        
        # Calculate remaining units
        remaining_units = max(0, total_allocated - consumed_units)
        
        # Check overage
        overage_units = max(0, consumed_units - total_allocated)
        
        # Get plan limits
        plan_info = self._get_user_plan_info(user_id)
        
        return {
            'total_allocated': total_allocated,
            'consumed': consumed_units,
            'remaining': remaining_units,
            'overage': overage_units,
            'period_start': current_period['start'],
            'period_end': current_period['end'],
            'plan': plan_info,
            'next_renewal': current_period['end']
        }
    
    def consume_compute_units(self, user_id: int, amount: int, task_id: str = None, 
                            description: str = None) -> bool:
        """
        Consume compute units for a user
        
        Returns True if consumption was successful, raises exception if insufficient units
        """
        if amount <= 0:
            raise ComputeUnitError("Consumption amount must be positive")
        
        # Get current status
        status = self.get_user_compute_units(user_id)
        
        # Check if consumption would exceed overage limits
        max_overage = self._get_max_overage_allowed(user_id)
        potential_overage = status['overage'] + max(0, amount - status['remaining'])
        
        if potential_overage > max_overage:
            raise OverageExceededError(
                f"Consumption would exceed maximum overage limit of {max_overage} units"
            )
        
        # Record the consumption
        self._record_consumption(
            user_id=user_id,
            amount=amount,
            task_id=task_id,
            description=description or f"Task execution: {task_id}" if task_id else "Compute unit consumption"
        )
        
        # Log the consumption
        logger.info(f"User {user_id} consumed {amount} compute units. "
                   f"Remaining: {status['remaining'] - amount}, "
                   f"Overage: {max(0, potential_overage)}")
        
        return True
    
    def allocate_compute_units(self, user_id: int, amount: int, source: str = "subscription",
                              description: str = None, expires_at: datetime = None) -> bool:
        """Allocate compute units to a user"""
        if amount <= 0:
            raise ComputeUnitError("Allocation amount must be positive")
        
        # Default expiration to end of current billing period
        if expires_at is None:
            current_period = self._get_current_billing_period(user_id)
            expires_at = current_period['end']
        
        # Record the allocation
        transaction = ComputeUnitTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type='credit',
            source=source,
            description=description or f"Compute unit allocation: {source}",
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(transaction)
        self.db.commit()
        
        logger.info(f"Allocated {amount} compute units to user {user_id} from {source}")
        return True
    
    def renew_monthly_allocation(self, user_id: int) -> bool:
        """Renew monthly compute unit allocation based on user's plan"""
        plan_info = self._get_user_plan_info(user_id)
        
        if not plan_info or plan_info['id'] == 'free':
            # Free plan users get their allocation renewed
            monthly_units = 100  # Free plan allocation
        else:
            monthly_units = plan_info['monthly_compute_units']
        
        # Calculate next period
        now = datetime.now(timezone.utc)
        next_period_end = now.replace(day=1) + timedelta(days=32)
        next_period_end = next_period_end.replace(day=1) - timedelta(days=1)
        next_period_end = next_period_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Allocate units for the new period
        self.allocate_compute_units(
            user_id=user_id,
            amount=monthly_units,
            source="monthly_renewal",
            description=f"Monthly allocation renewal for {plan_info['name'] if plan_info else 'Free'} plan",
            expires_at=next_period_end
        )
        
        logger.info(f"Renewed monthly allocation of {monthly_units} compute units for user {user_id}")
        return True
    
    def get_usage_analytics(self, user_id: int, period_days: int = 30) -> Dict:
        """Get usage analytics for a user over a specified period"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=period_days)
        
        # Get consumption transactions
        consumption_query = self.db.query(ComputeUnitTransaction).filter(
            and_(
                ComputeUnitTransaction.user_id == user_id,
                ComputeUnitTransaction.transaction_type == 'debit',
                ComputeUnitTransaction.created_at >= start_date,
                ComputeUnitTransaction.created_at <= end_date
            )
        )
        
        # Calculate daily usage
        daily_usage = {}
        total_consumed = 0
        
        for transaction in consumption_query:
            day_key = transaction.created_at.date().isoformat()
            if day_key not in daily_usage:
                daily_usage[day_key] = 0
            daily_usage[day_key] += transaction.amount
            total_consumed += transaction.amount
        
        # Get task statistics
        task_stats = self._get_task_statistics(user_id, start_date, end_date)
        
        # Calculate averages
        avg_daily_usage = total_consumed / period_days if period_days > 0 else 0
        
        return {
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'total_consumed': total_consumed,
            'avg_daily_usage': round(avg_daily_usage, 2),
            'daily_usage': daily_usage,
            'task_statistics': task_stats,
            'period_days': period_days
        }
    
    def calculate_overage_cost(self, user_id: int) -> Dict:
        """Calculate overage costs for the current billing period"""
        from os import getenv
        
        status = self.get_user_compute_units(user_id)
        overage_units = status['overage']
        
        if overage_units <= 0:
            return {
                'overage_units': 0,
                'overage_cost_cents': 0,
                'overage_cost_formatted': '$0.00'
            }
        
        # Get overage rate from environment (default 5 cents per unit)
        overage_rate_cents = int(getenv('COMPUTE_UNITS_OVERAGE_RATE_CENTS', '5'))
        total_overage_cost_cents = overage_units * overage_rate_cents
        
        return {
            'overage_units': overage_units,
            'overage_cost_cents': total_overage_cost_cents,
            'overage_cost_formatted': f"${total_overage_cost_cents / 100:.2f}",
            'rate_per_unit_cents': overage_rate_cents
        }
    
    def _get_current_billing_period(self, user_id: int) -> Dict:
        """Get the current billing period for a user"""
        now = datetime.now(timezone.utc)
        
        # For simplicity, using monthly periods starting on the 1st
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate end of month
        if now.month == 12:
            period_end = period_start.replace(year=now.year + 1, month=1) - timedelta(days=1)
        else:
            period_end = period_start.replace(month=now.month + 1) - timedelta(days=1)
        
        period_end = period_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return {
            'start': period_start,
            'end': period_end
        }
    
    def _calculate_allocated_units(self, user_id: int, period: Dict) -> int:
        """Calculate total allocated units for the current period"""
        allocated_query = self.db.query(func.sum(ComputeUnitTransaction.amount)).filter(
            and_(
                ComputeUnitTransaction.user_id == user_id,
                ComputeUnitTransaction.transaction_type == 'credit',
                ComputeUnitTransaction.created_at >= period['start'],
                ComputeUnitTransaction.expires_at >= period['start']
            )
        )
        
        result = allocated_query.scalar()
        return result if result is not None else 0
    
    def _calculate_consumed_units(self, user_id: int, period: Dict) -> int:
        """Calculate total consumed units for the current period"""
        consumed_query = self.db.query(func.sum(ComputeUnitTransaction.amount)).filter(
            and_(
                ComputeUnitTransaction.user_id == user_id,
                ComputeUnitTransaction.transaction_type == 'debit',
                ComputeUnitTransaction.created_at >= period['start'],
                ComputeUnitTransaction.created_at <= period['end']
            )
        )
        
        result = consumed_query.scalar()
        return result if result is not None else 0
    
    def _get_user_plan_info(self, user_id: int) -> Optional[Dict]:
        """Get user's current plan information"""
        subscription = self.db.query(UserSubscription).filter(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status.in_(['active', 'past_due'])
            )
        ).first()
        
        if not subscription:
            return None
        
        plan = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == subscription.plan_id
        ).first()
        
        if not plan:
            return None
        
        return {
            'id': plan.id,
            'name': plan.name,
            'monthly_compute_units': plan.monthly_compute_units,
            'max_concurrent_tasks': plan.max_concurrent_tasks,
            'price_cents': plan.price_cents
        }
    
    def _get_max_overage_allowed(self, user_id: int) -> int:
        """Get maximum overage allowed for a user"""
        from os import getenv
        
        plan_info = self._get_user_plan_info(user_id)
        
        if not plan_info or plan_info['id'] == 'free':
            # Free plan users have no overage allowance
            return 0
        
        # Get overage percentage from environment (default 50%)
        max_overage_percent = float(getenv('MAX_COMPUTE_UNITS_OVERAGE_PERCENT', '50'))
        base_allocation = plan_info['monthly_compute_units']
        
        return int(base_allocation * (max_overage_percent / 100))
    
    def _record_consumption(self, user_id: int, amount: int, task_id: str = None, 
                           description: str = None):
        """Record compute unit consumption"""
        transaction = ComputeUnitTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type='debit',
            source='task_execution',
            task_id=task_id,
            description=description,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(transaction)
        self.db.commit()
    
    def _get_task_statistics(self, user_id: int, start_date: datetime, 
                            end_date: datetime) -> Dict:
        """Get task execution statistics for analytics"""
        # This would integrate with the task system to get detailed statistics
        # For now, we'll return basic information from compute unit transactions
        
        task_transactions = self.db.query(ComputeUnitTransaction).filter(
            and_(
                ComputeUnitTransaction.user_id == user_id,
                ComputeUnitTransaction.transaction_type == 'debit',
                ComputeUnitTransaction.created_at >= start_date,
                ComputeUnitTransaction.created_at <= end_date,
                ComputeUnitTransaction.task_id.isnot(None)
            )
        ).all()
        
        total_tasks = len(task_transactions)
        total_compute_units = sum(t.amount for t in task_transactions)
        avg_units_per_task = total_compute_units / total_tasks if total_tasks > 0 else 0
        
        return {
            'total_tasks': total_tasks,
            'total_compute_units': total_compute_units,
            'avg_units_per_task': round(avg_units_per_task, 2),
            'completed_tasks': total_tasks,  # Assuming all recorded tasks completed
            'failed_tasks': 0  # Would need integration with task system for accurate data
        }

def get_compute_unit_manager(db = None) -> ComputeUnitManager:
    """Get a ComputeUnitManager instance"""
    if db is None:
        db = next(get_db())
    return ComputeUnitManager(db)

# Utility functions for easy access
def consume_compute_units(user_id: int, amount: int, task_id: str = None, 
                         description: str = None, db = None) -> bool:
    """Convenience function to consume compute units"""
    manager = get_compute_unit_manager(db)
    return manager.consume_compute_units(user_id, amount, task_id, description)

def get_user_compute_units(user_id: int, db = None) -> Dict:
    """Convenience function to get user compute unit status"""
    manager = get_compute_unit_manager(db)
    return manager.get_user_compute_units(user_id)

def allocate_compute_units(user_id: int, amount: int, source: str = "subscription",
                          description: str = None, expires_at: datetime = None,
                          db = None) -> bool:
    """Convenience function to allocate compute units"""
    manager = get_compute_unit_manager(db)
    return manager.allocate_compute_units(user_id, amount, source, description, expires_at)