#!/usr/bin/env python3
"""
Schema validation script for Selextract Cloud database
Validates that the implemented schema matches plan specifications
"""

import asyncio
import logging
from typing import Dict, List, Set
from sqlalchemy import inspect, text
from sqlalchemy.engine import reflection

from database import db_config, get_db_session
from models import (
    User, Task, TaskLog, SubscriptionPlan, UserSubscription,
    APIKey, UsageAnalytics, Base
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaValidator:
    """Validates database schema against plan requirements"""
    
    def __init__(self):
        self.required_tables = {
            'users', 'tasks', 'task_logs', 'subscription_plans',
            'user_subscriptions', 'api_keys', 'usage_analytics'
        }
        
        self.required_indexes = {
            'users': {'idx_users_email', 'idx_users_google_id'},
            'tasks': {
                'idx_tasks_user_id', 'idx_tasks_status', 
                'idx_tasks_scheduled_at', 'idx_tasks_created_at',
                'idx_tasks_user_status', 'idx_tasks_user_created'
            },
            'task_logs': {'idx_task_logs_task_id', 'idx_task_logs_timestamp'},
            'user_subscriptions': {
                'idx_user_subscriptions_user_id', 'idx_user_subscriptions_status',
                'idx_user_subscriptions_plan'
            },
            'api_keys': {'idx_api_keys_key_hash', 'idx_api_keys_user_id', 'idx_api_keys_user_active'},
            'usage_analytics': {'idx_usage_analytics_user_date'}
        }
        
        self.validation_results = {
            'tables': {},
            'columns': {},
            'indexes': {},
            'constraints': {},
            'data': {},
            'errors': [],
            'warnings': []
        }
    
    async def validate_complete_schema(self) -> Dict:
        """Run complete schema validation"""
        logger.info("Starting complete schema validation...")
        
        try:
            await self.validate_tables()
            await self.validate_columns()
            await self.validate_indexes()
            await self.validate_constraints()
            await self.validate_default_data()
            await self.validate_business_logic()
            
            # Summary
            error_count = len(self.validation_results['errors'])
            warning_count = len(self.validation_results['warnings'])
            
            if error_count == 0:
                logger.info(f"✅ Schema validation PASSED with {warning_count} warnings")
                self.validation_results['status'] = 'PASSED'
            else:
                logger.error(f"❌ Schema validation FAILED with {error_count} errors and {warning_count} warnings")
                self.validation_results['status'] = 'FAILED'
                
        except Exception as e:
            logger.error(f"Schema validation encountered an error: {e}")
            self.validation_results['errors'].append(f"Validation error: {str(e)}")
            self.validation_results['status'] = 'ERROR'
        
        return self.validation_results
    
    async def validate_tables(self):
        """Validate that all required tables exist"""
        logger.info("Validating table existence...")
        
        async with get_db_session() as session:
            # Get list of existing tables
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """))
            existing_tables = {row[0] for row in result.fetchall()}
        
        # Check required tables
        missing_tables = self.required_tables - existing_tables
        extra_tables = existing_tables - self.required_tables
        
        if missing_tables:
            self.validation_results['errors'].extend([
                f"Missing required table: {table}" for table in missing_tables
            ])
        
        if extra_tables:
            self.validation_results['warnings'].extend([
                f"Extra table found: {table}" for table in extra_tables
            ])
        
        self.validation_results['tables'] = {
            'required': list(self.required_tables),
            'existing': list(existing_tables),
            'missing': list(missing_tables),
            'extra': list(extra_tables)
        }
        
        logger.info(f"Table validation: {len(existing_tables)} tables found, {len(missing_tables)} missing")
    
    async def validate_columns(self):
        """Validate table columns match model definitions"""
        logger.info("Validating table columns...")
        
        # Expected columns for each table based on models
        expected_columns = {
            'users': {
                'id', 'email', 'full_name', 'google_id', 'is_active',
                'subscription_tier', 'compute_units_remaining', 'compute_units_reset_date',
                'created_at', 'updated_at'
            },
            'tasks': {
                'id', 'user_id', 'name', 'config', 'status', 'priority',
                'scheduled_at', 'started_at', 'completed_at', 'compute_units_consumed',
                'error_message', 'result_file_path', 'created_at', 'updated_at'
            },
            'task_logs': {
                'id', 'task_id', 'level', 'message', 'metadata', 'timestamp'
            },
            'subscription_plans': {
                'id', 'name', 'description', 'monthly_compute_units',
                'max_concurrent_tasks', 'price_cents', 'lemon_squeezy_variant_id',
                'is_active', 'created_at'
            },
            'user_subscriptions': {
                'id', 'user_id', 'plan_id', 'lemon_squeezy_subscription_id',
                'status', 'current_period_start', 'current_period_end',
                'cancel_at_period_end', 'created_at', 'updated_at'
            },
            'api_keys': {
                'id', 'user_id', 'name', 'key_hash', 'key_prefix',
                'last_used_at', 'is_active', 'created_at'
            },
            'usage_analytics': {
                'id', 'user_id', 'date', 'tasks_executed',
                'compute_units_used', 'api_calls', 'created_at'
            }
        }
        
        column_results = {}
        
        async with get_db_session() as session:
            for table_name, expected_cols in expected_columns.items():
                if table_name not in self.validation_results['tables']['existing']:
                    continue
                
                # Get actual columns
                result = await session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """))
                
                actual_columns = {row[0] for row in result.fetchall()}
                
                missing_cols = expected_cols - actual_columns
                extra_cols = actual_columns - expected_cols
                
                if missing_cols:
                    self.validation_results['errors'].extend([
                        f"Table {table_name} missing column: {col}" for col in missing_cols
                    ])
                
                if extra_cols:
                    self.validation_results['warnings'].extend([
                        f"Table {table_name} has extra column: {col}" for col in extra_cols
                    ])
                
                column_results[table_name] = {
                    'expected': list(expected_cols),
                    'actual': list(actual_columns),
                    'missing': list(missing_cols),
                    'extra': list(extra_cols)
                }
        
        self.validation_results['columns'] = column_results
        logger.info("Column validation completed")
    
    async def validate_indexes(self):
        """Validate that required indexes exist"""
        logger.info("Validating database indexes...")
        
        index_results = {}
        
        async with get_db_session() as session:
            for table_name, required_idxs in self.required_indexes.items():
                if table_name not in self.validation_results['tables']['existing']:
                    continue
                
                # Get actual indexes
                result = await session.execute(text(f"""
                    SELECT indexname
                    FROM pg_indexes 
                    WHERE tablename = '{table_name}' AND schemaname = 'public'
                """))
                
                actual_indexes = {row[0] for row in result.fetchall()}
                
                missing_idxs = required_idxs - actual_indexes
                
                if missing_idxs:
                    self.validation_results['errors'].extend([
                        f"Table {table_name} missing index: {idx}" for idx in missing_idxs
                    ])
                
                index_results[table_name] = {
                    'required': list(required_idxs),
                    'actual': list(actual_indexes),
                    'missing': list(missing_idxs)
                }
        
        self.validation_results['indexes'] = index_results
        logger.info("Index validation completed")
    
    async def validate_constraints(self):
        """Validate database constraints"""
        logger.info("Validating database constraints...")
        
        async with get_db_session() as session:
            # Check foreign key constraints
            result = await session.execute(text("""
                SELECT 
                    tc.table_name,
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                LEFT JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.table_schema = 'public' AND tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name, tc.constraint_name
            """))
            
            foreign_keys = []
            for row in result.fetchall():
                foreign_keys.append({
                    'table': row[0],
                    'constraint': row[1],
                    'column': row[3],
                    'foreign_table': row[4],
                    'foreign_column': row[5]
                })
            
            # Validate expected foreign keys
            expected_fks = {
                ('tasks', 'user_id', 'users', 'id'),
                ('task_logs', 'task_id', 'tasks', 'id'),
                ('user_subscriptions', 'user_id', 'users', 'id'),
                ('user_subscriptions', 'plan_id', 'subscription_plans', 'id'),
                ('api_keys', 'user_id', 'users', 'id'),
                ('usage_analytics', 'user_id', 'users', 'id')
            }
            
            actual_fks = {
                (fk['table'], fk['column'], fk['foreign_table'], fk['foreign_column'])
                for fk in foreign_keys
            }
            
            missing_fks = expected_fks - actual_fks
            if missing_fks:
                self.validation_results['errors'].extend([
                    f"Missing foreign key: {fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}" 
                    for fk in missing_fks
                ])
            
            self.validation_results['constraints'] = {
                'foreign_keys': foreign_keys,
                'expected_fks': list(expected_fks),
                'missing_fks': list(missing_fks)
            }
        
        logger.info("Constraint validation completed")
    
    async def validate_default_data(self):
        """Validate that default subscription plans exist"""
        logger.info("Validating default data...")
        
        async with get_db_session() as session:
            # Check subscription plans
            result = await session.execute(text("SELECT id, name FROM subscription_plans"))
            plans = {row[0]: row[1] for row in result.fetchall()}
            
            expected_plans = {'free', 'starter', 'professional', 'enterprise'}
            missing_plans = expected_plans - set(plans.keys())
            
            if missing_plans:
                self.validation_results['errors'].extend([
                    f"Missing default subscription plan: {plan}" for plan in missing_plans
                ])
            
            self.validation_results['data'] = {
                'subscription_plans': plans,
                'expected_plans': list(expected_plans),
                'missing_plans': list(missing_plans)
            }
        
        logger.info("Default data validation completed")
    
    async def validate_business_logic(self):
        """Validate business logic requirements"""
        logger.info("Validating business logic requirements...")
        
        # Check UUID primary keys
        uuid_models = [User, Task, TaskLog, UserSubscription, APIKey, UsageAnalytics]
        for model in uuid_models:
            pk_column = inspect(model).primary_key[0]
            if not str(pk_column.type).startswith('UUID'):
                self.validation_results['errors'].append(
                    f"Model {model.__name__} should have UUID primary key, found {pk_column.type}"
                )
        
        # Check JSONB fields
        if not hasattr(Task.config.type, 'python_type') or 'JSONB' not in str(Task.config.type):
            self.validation_results['errors'].append("Task.config should be JSONB type")
        
        if not hasattr(TaskLog.metadata.type, 'python_type') or 'JSONB' not in str(TaskLog.metadata.type):
            self.validation_results['errors'].append("TaskLog.metadata should be JSONB type")
        
        # Check timestamp auto-update triggers exist
        async with get_db_session() as session:
            result = await session.execute(text("""
                SELECT trigger_name, event_object_table 
                FROM information_schema.triggers 
                WHERE trigger_schema = 'public' 
                AND trigger_name LIKE '%updated_at%'
            """))
            
            triggers = {row[1]: row[0] for row in result.fetchall()}
            expected_trigger_tables = {'users', 'tasks', 'user_subscriptions'}
            
            missing_triggers = expected_trigger_tables - set(triggers.keys())
            if missing_triggers:
                self.validation_results['warnings'].extend([
                    f"Missing auto-update trigger for table: {table}" for table in missing_triggers
                ])
        
        logger.info("Business logic validation completed")

async def main():
    """Main validation function"""
    print("🔍 Selextract Cloud Schema Validation")
    print("=" * 50)
    
    # Initialize database connection
    db_config.create_engine()
    db_config.create_session_factory()
    
    # Run validation
    validator = SchemaValidator()
    results = await validator.validate_complete_schema()
    
    # Print detailed results
    print(f"\n📊 Validation Results:")
    print(f"Status: {results['status']}")
    print(f"Errors: {len(results['errors'])}")
    print(f"Warnings: {len(results['warnings'])}")
    
    if results['errors']:
        print(f"\n❌ Errors:")
        for error in results['errors']:
            print(f"  • {error}")
    
    if results['warnings']:
        print(f"\n⚠️ Warnings:")
        for warning in results['warnings']:
            print(f"  • {warning}")
    
    # Table summary
    if 'tables' in results:
        tables = results['tables']
        print(f"\n📋 Tables Summary:")
        print(f"  Required: {len(tables['required'])}")
        print(f"  Found: {len(tables['existing'])}")
        print(f"  Missing: {len(tables['missing'])}")
        
        if tables['missing']:
            print(f"  Missing tables: {', '.join(tables['missing'])}")
    
    # Index summary
    if 'indexes' in results:
        total_missing_indexes = sum(
            len(table_data['missing']) 
            for table_data in results['indexes'].values()
        )
        print(f"\n🗂️ Indexes Summary:")
        print(f"  Missing indexes: {total_missing_indexes}")
    
    # Data summary
    if 'data' in results:
        data = results['data']
        if 'subscription_plans' in data:
            print(f"\n📦 Default Data Summary:")
            print(f"  Subscription plans: {len(data['subscription_plans'])}")
            print(f"  Plans found: {', '.join(data['subscription_plans'].keys())}")
    
    print(f"\n{'='*50}")
    
    if results['status'] == 'PASSED':
        print("✅ Schema validation completed successfully!")
        print("The database schema matches plan specifications.")
    else:
        print("❌ Schema validation failed!")
        print("Please review and fix the issues above.")
        return 1
    
    return 0

def validate_task_config(config: dict, task_type: str) -> dict:
    """
    Validate task configuration against schema requirements.
    
    Args:
        config: Task configuration dictionary
        task_type: Type of task (simple_scraping, advanced_scraping, etc.)
        
    Returns:
        Dictionary with 'valid' boolean and optional 'errors' list
    """
    try:
        # Import schemas here to avoid circular imports
        from schemas import (
            SimpleScrapingConfig, AdvancedScrapingConfig,
            BulkScrapingConfig, MonitoringConfig
        )
        
        # Debug logging
        print(f"DEBUG: Validating task_type: {task_type}")
        print(f"DEBUG: Config: {config}")
        
        # Map task types to their validation schemas
        schema_mapping = {
            'simple_scraping': SimpleScrapingConfig,
            'advanced_scraping': AdvancedScrapingConfig,
            'bulk_scraping': BulkScrapingConfig,
            'monitoring': MonitoringConfig
        }
        
        if task_type not in schema_mapping:
            return {
                'valid': False,
                'errors': [f'Unknown task type: {task_type}']
            }
        
        # Validate configuration using the appropriate schema
        schema_class = schema_mapping[task_type]
        print(f"DEBUG: Using schema class: {schema_class}")
        
        validated_config = schema_class(**config)
        
        return {
            'valid': True,
            'validated_config': validated_config.dict()
        }
        
    except Exception as e:
        print(f"DEBUG: Validation error: {str(e)}")
        print(f"DEBUG: Validation error type: {type(e)}")
        if hasattr(e, 'errors'):
            print(f"DEBUG: Validation error details: {e.errors()}")
        return {
            'valid': False,
            'errors': [str(e)]
        }

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)