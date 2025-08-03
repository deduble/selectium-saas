"""
Locust Distributed Load Testing for Selextract Cloud
Comprehensive performance testing with user behavior simulation and distributed execution
"""

import json
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
from locust.env import Environment
from locust.runners import MasterRunner, WorkerRunner

# Test configuration
API_BASE = "/api/v1"
TEST_DATA_FILE = "tests/load/test-data.csv"

# Test users pool
TEST_USERS = [
    {"email": f"loadtest{i}@example.com", "password": "LoadTest123!"} 
    for i in range(1, 21)
]

# Sample task configurations for testing
SAMPLE_TASKS = [
    {
        "name": "E-commerce Product Scraping",
        "url": "https://example-shop.com/products",
        "selectors": {
            "title": ".product-title, h1, .product-name",
            "price": ".price, .cost, .amount",
            "availability": ".stock-status, .in-stock"
        },
        "config": {
            "wait_for_selector": True,
            "take_screenshot": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    },
    {
        "name": "News Article Extraction",
        "url": "https://example-news.com/article/123",
        "selectors": {
            "headline": "h1.article-title, .headline",
            "content": ".article-body, .content",
            "author": ".author-name, .byline",
            "publish_date": ".publish-date, .date"
        },
        "config": {
            "wait_for_selector": True,
            "take_screenshot": True,
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    },
    {
        "name": "Real Estate Listings",
        "url": "https://example-realty.com/listings",
        "selectors": {
            "price": ".listing-price, .price",
            "address": ".listing-address, .address",
            "bedrooms": ".bed-count, .bedrooms",
            "bathrooms": ".bath-count, .bathrooms",
            "sqft": ".square-footage, .sqft"
        },
        "config": {
            "wait_for_selector": True,
            "take_screenshot": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    },
    {
        "name": "Job Postings Scraper",
        "url": "https://example-jobs.com/listings",
        "selectors": {
            "job_title": ".job-title, h2.title",
            "company": ".company-name, .employer",
            "location": ".job-location, .location",
            "salary": ".salary-range, .pay",
            "description": ".job-description, .details"
        },
        "config": {
            "wait_for_selector": True,
            "take_screenshot": False,
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
    }
]

# Custom metrics tracking
task_creation_times = []
task_execution_times = []
auth_failure_count = 0
billing_operation_times = []


class BaseSelextractUser(FastHttpUser):
    """Base user class with common functionality"""
    
    abstract = True
    
    def __init__(self, environment):
        super().__init__(environment)
        self.access_token = None
        self.user_data = None
        self.created_tasks = []
        self.session_id = str(uuid.uuid4())
        
    def on_start(self):
        """Initialize user session"""
        self.user_data = random.choice(TEST_USERS)
        self.authenticate()
        
    def on_stop(self):
        """Cleanup user session"""
        if self.access_token:
            self.logout()
            
    def authenticate(self):
        """Authenticate user and store access token"""
        global auth_failure_count
        
        response = self.client.post(
            f"{API_BASE}/auth/login",
            json={
                "email": self.user_data["email"],
                "password": self.user_data["password"]
            },
            name="auth_login"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
        else:
            auth_failure_count += 1
            
    def logout(self):
        """Logout user"""
        if self.access_token:
            self.client.post(
                f"{API_BASE}/auth/logout",
                name="auth_logout"
            )
            self.access_token = None
            
    def get_random_task(self):
        """Get random task configuration"""
        task = random.choice(SAMPLE_TASKS).copy()
        task["name"] = f"{task['name']} (Locust Test {random.randint(1000, 9999)})"
        return task


class RegularUser(BaseSelextractUser):
    """Regular user behavior simulation"""
    
    wait_time = between(5, 15)
    weight = 40
    
    @task(4)
    def create_and_manage_task(self):
        """Create task and monitor its progress"""
        if not self.access_token:
            return
            
        # Create task
        task_data = self.get_random_task()
        start_time = time.time()
        
        response = self.client.post(
            f"{API_BASE}/tasks",
            json=task_data,
            name="create_task"
        )
        
        creation_time = (time.time() - start_time) * 1000
        task_creation_times.append(creation_time)
        
        if response.status_code == 201:
            task = response.json()
            task_id = task["id"]
            self.created_tasks.append(task_id)
            
            # Monitor task progress
            execution_start = time.time()
            max_polls = 10  # Maximum 5 minutes of polling
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(30)  # Poll every 30 seconds
                
                status_response = self.client.get(
                    f"{API_BASE}/tasks/{task_id}",
                    name="get_task_status"
                )
                
                if status_response.status_code == 200:
                    task_status = status_response.json()
                    
                    if task_status["status"] in ["completed", "failed", "cancelled"]:
                        execution_time = (time.time() - execution_start) * 1000
                        task_execution_times.append(execution_time)
                        break
                        
                poll_count += 1
                
            # Get task results
            self.client.get(
                f"{API_BASE}/tasks/{task_id}/results",
                name="get_task_results"
            )
            
    @task(2)
    def view_dashboard(self):
        """View dashboard statistics"""
        if not self.access_token:
            return
            
        self.client.get(
            f"{API_BASE}/dashboard/stats",
            name="dashboard_stats"
        )
        
        self.client.get(
            f"{API_BASE}/dashboard/recent-tasks",
            name="recent_tasks"
        )
        
    @task(1)
    def manage_existing_tasks(self):
        """Manage existing tasks"""
        if not self.access_token:
            return
            
        # List tasks
        self.client.get(
            f"{API_BASE}/tasks?limit=20&offset=0",
            name="list_tasks"
        )
        
        # Cancel random task (10% chance)
        if self.created_tasks and random.random() < 0.1:
            task_id = random.choice(self.created_tasks)
            self.client.post(
                f"{API_BASE}/tasks/{task_id}/cancel",
                name="cancel_task"
            )
            
    @task(1)
    def check_billing(self):
        """Check billing and usage information"""
        if not self.access_token:
            return
            
        start_time = time.time()
        
        self.client.get(
            f"{API_BASE}/billing/usage",
            name="billing_usage"
        )
        
        billing_time = (time.time() - start_time) * 1000
        billing_operation_times.append(billing_time)
        
        self.client.get(
            f"{API_BASE}/billing/history",
            name="billing_history"
        )


class PowerUser(BaseSelextractUser):
    """Power user behavior - creates multiple tasks quickly"""
    
    wait_time = between(2, 8)
    weight = 20
    
    @task(6)
    def batch_create_tasks(self):
        """Create multiple tasks in quick succession"""
        if not self.access_token:
            return
            
        num_tasks = random.randint(2, 5)
        
        for _ in range(num_tasks):
            task_data = self.get_random_task()
            
            response = self.client.post(
                f"{API_BASE}/tasks",
                json=task_data,
                name="batch_create_task"
            )
            
            if response.status_code == 201:
                task = response.json()
                self.created_tasks.append(task["id"])
                
            time.sleep(random.uniform(1, 3))  # Short delay between tasks
            
    @task(2)
    def analyze_performance(self):
        """Analyze performance metrics"""
        if not self.access_token:
            return
            
        self.client.get(
            f"{API_BASE}/analytics/usage?period=7days",
            name="analytics_usage"
        )
        
        self.client.get(
            f"{API_BASE}/analytics/performance?period=24hours",
            name="analytics_performance"
        )
        
    @task(1)
    def bulk_operations(self):
        """Perform bulk operations on tasks"""
        if not self.access_token or len(self.created_tasks) < 2:
            return
            
        # Get multiple task statuses
        for task_id in self.created_tasks[:5]:  # Check up to 5 tasks
            self.client.get(
                f"{API_BASE}/tasks/{task_id}",
                name="bulk_task_status"
            )


class BillingFocusedUser(BaseSelextractUser):
    """User focused on billing operations"""
    
    wait_time = between(10, 30)
    weight = 15
    
    @task(3)
    def intensive_billing_checks(self):
        """Perform intensive billing operations"""
        if not self.access_token:
            return
            
        start_time = time.time()
        
        # Check current usage
        self.client.get(
            f"{API_BASE}/billing/usage",
            name="billing_usage_detailed"
        )
        
        # Get billing plans
        self.client.get(
            f"{API_BASE}/billing/plans",
            name="billing_plans"
        )
        
        # Get subscription details
        self.client.get(
            f"{API_BASE}/billing/subscription",
            name="billing_subscription"
        )
        
        # Get detailed history
        self.client.get(
            f"{API_BASE}/billing/history?limit=50",
            name="billing_history_detailed"
        )
        
        billing_time = (time.time() - start_time) * 1000
        billing_operation_times.append(billing_time)
        
    @task(1)
    def plan_management(self):
        """Simulate plan changes (rarely)"""
        if not self.access_token:
            return
            
        # Only 2% chance to actually attempt plan change
        if random.random() < 0.02:
            plans = ["starter", "professional", "enterprise"]
            new_plan = random.choice(plans)
            
            self.client.post(
                f"{API_BASE}/billing/change-plan",
                json={"plan_id": new_plan},
                name="change_plan"
            )


class DatabaseIntensiveUser(BaseSelextractUser):
    """User that performs database-intensive operations"""
    
    wait_time = between(3, 10)
    weight = 15
    
    @task(3)
    def complex_queries(self):
        """Perform complex database queries"""
        if not self.access_token:
            return
            
        # Search tasks with complex filters
        params = {
            "status": random.choice(["completed", "failed", "running"]),
            "limit": 50,
            "offset": random.randint(0, 100),
            "sort": "created_at",
            "order": "desc"
        }
        
        self.client.get(
            f"{API_BASE}/tasks",
            params=params,
            name="complex_task_search"
        )
        
        # Get analytics with date ranges
        end_date = datetime.now()
        start_date = end_date - timedelta(days=random.randint(7, 30))
        
        self.client.get(
            f"{API_BASE}/analytics/usage",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            name="analytics_date_range"
        )
        
    @task(2)
    def aggregation_queries(self):
        """Perform aggregation queries"""
        if not self.access_token:
            return
            
        # Get usage summaries
        self.client.get(
            f"{API_BASE}/analytics/summary?period=monthly",
            name="monthly_summary"
        )
        
        # Get performance metrics
        self.client.get(
            f"{API_BASE}/analytics/performance-summary",
            name="performance_summary"
        )


class APIStressUser(BaseSelextractUser):
    """User that stresses API endpoints rapidly"""
    
    wait_time = between(1, 3)
    weight = 10
    
    @task(5)
    def rapid_api_calls(self):
        """Make rapid API calls"""
        if not self.access_token:
            return
            
        # Rapid task creation
        task_data = self.get_random_task()
        response = self.client.post(
            f"{API_BASE}/tasks",
            json=task_data,
            name="rapid_task_creation"
        )
        
        if response.status_code == 201:
            task_id = response.json()["id"]
            
            # Immediate status check
            self.client.get(
                f"{API_BASE}/tasks/{task_id}",
                name="immediate_status_check"
            )
            
    @task(3)
    def health_monitoring(self):
        """Monitor system health rapidly"""
        self.client.get(
            f"{API_BASE}/health",
            name="rapid_health_check"
        )
        
        self.client.get(
            f"{API_BASE}/metrics",
            name="rapid_metrics_check"
        )


# Event handlers for custom metrics collection
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Collect custom metrics on each request"""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment"""
    print("Starting Selextract Cloud distributed load test")
    print(f"Environment: {environment}")
    
    if isinstance(environment.runner, MasterRunner):
        print("Running as master node")
    elif isinstance(environment.runner, WorkerRunner):
        print("Running as worker node")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Collect final metrics and cleanup"""
    print("Load test completed")
    
    # Print custom metrics
    if task_creation_times:
        avg_creation = sum(task_creation_times) / len(task_creation_times)
        print(f"Average task creation time: {avg_creation:.2f}ms")
        
    if task_execution_times:
        avg_execution = sum(task_execution_times) / len(task_execution_times)
        print(f"Average task execution time: {avg_execution:.2f}ms")
        
    if billing_operation_times:
        avg_billing = sum(billing_operation_times) / len(billing_operation_times)
        print(f"Average billing operation time: {avg_billing:.2f}ms")
        
    print(f"Authentication failures: {auth_failure_count}")


# For standalone execution
if __name__ == "__main__":
    import sys
    from locust.main import main
    
    # Default to RegularUser if no specific user class is specified
    sys.argv.extend(["--host", "http://localhost:8000"])
    main()