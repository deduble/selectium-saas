#!/usr/bin/env python3
"""
Worker Load Testing Script for Selextract Cloud
Tests worker performance under various load conditions
"""

import asyncio
import json
import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any
import random

# Configuration
API_BASE_URL = os.getenv('TARGET_URL', 'http://localhost:8000') + '/api/v1'
TEST_USER_EMAIL = 'loadtest1@example.com'
TEST_USER_PASSWORD = 'LoadTest123!'

# Sample tasks for worker testing
SAMPLE_TASKS = [
    {
        "name": "Worker Load Test - E-commerce",
        "url": "https://example-shop.com/products",
        "selectors": {
            "title": ".product-title",
            "price": ".price",
            "availability": ".stock-status"
        },
        "config": {
            "wait_for_selector": True,
            "take_screenshot": False,
            "user_agent": "Mozilla/5.0 (Worker Load Test)"
        }
    },
    {
        "name": "Worker Load Test - News",
        "url": "https://example-news.com/article",
        "selectors": {
            "headline": "h1",
            "content": ".article-body",
            "author": ".author"
        },
        "config": {
            "wait_for_selector": True,
            "take_screenshot": True,
            "user_agent": "Mozilla/5.0 (Worker Load Test)"
        }
    },
    {
        "name": "Worker Load Test - Real Estate",
        "url": "https://example-realty.com/listing",
        "selectors": {
            "price": ".price",
            "address": ".address",
            "bedrooms": ".bedrooms"
        },
        "config": {
            "wait_for_selector": True,
            "take_screenshot": False,
            "user_agent": "Mozilla/5.0 (Worker Load Test)"
        }
    }
]

class WorkerLoadTester:
    """Tests worker performance and queue handling"""
    
    def __init__(self):
        self.access_token = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Selextract-Worker-Load-Tester/1.0'
        })
        
    def authenticate(self) -> bool:
        """Authenticate and get access token"""
        try:
            response = self.session.post(
                f"{API_BASE_URL}/auth/login",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                return True
            else:
                print(f"Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single task"""
        try:
            start_time = time.time()
            response = self.session.post(f"{API_BASE_URL}/tasks", json=task_data)
            creation_time = time.time() - start_time
            
            if response.status_code == 201:
                task = response.json()
                return {
                    'success': True,
                    'task_id': task['id'],
                    'creation_time': creation_time,
                    'task_name': task_data['name']
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'creation_time': creation_time,
                    'task_name': task_data['name']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'creation_time': 0,
                'task_name': task_data['name']
            }
    
    def monitor_task(self, task_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """Monitor task execution until completion"""
        start_time = time.time()
        last_status = None
        poll_count = 0
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.session.get(f"{API_BASE_URL}/tasks/{task_id}")
                
                if response.status_code == 200:
                    task_data = response.json()
                    status = task_data['status']
                    
                    if status != last_status:
                        last_status = status
                        print(f"Task {task_id} status: {status}")
                    
                    if status in ['completed', 'failed', 'cancelled']:
                        execution_time = time.time() - start_time
                        return {
                            'success': True,
                            'final_status': status,
                            'execution_time': execution_time,
                            'poll_count': poll_count,
                            'task_data': task_data
                        }
                
                poll_count += 1
                time.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                print(f"Error monitoring task {task_id}: {e}")
                time.sleep(5)
        
        # Timeout
        return {
            'success': False,
            'error': 'timeout',
            'execution_time': max_wait_time,
            'poll_count': poll_count
        }
    
    def test_sequential_tasks(self, num_tasks: int = 5) -> Dict[str, Any]:
        """Test sequential task creation and execution"""
        print(f"\n=== Testing {num_tasks} Sequential Tasks ===")
        
        results = {
            'test_type': 'sequential',
            'num_tasks': num_tasks,
            'tasks': [],
            'total_time': 0,
            'success_count': 0,
            'failure_count': 0
        }
        
        start_time = time.time()
        
        for i in range(num_tasks):
            task_data = random.choice(SAMPLE_TASKS).copy()
            task_data['name'] = f"{task_data['name']} - Sequential {i+1}"
            
            print(f"Creating task {i+1}/{num_tasks}: {task_data['name']}")
            
            # Create task
            creation_result = self.create_task(task_data)
            
            if creation_result['success']:
                # Monitor task execution
                execution_result = self.monitor_task(creation_result['task_id'])
                
                task_result = {
                    **creation_result,
                    **execution_result
                }
                
                if execution_result['success'] and execution_result['final_status'] == 'completed':
                    results['success_count'] += 1
                else:
                    results['failure_count'] += 1
            else:
                task_result = creation_result
                results['failure_count'] += 1
            
            results['tasks'].append(task_result)
        
        results['total_time'] = time.time() - start_time
        return results
    
    def test_concurrent_tasks(self, num_tasks: int = 10, max_workers: int = 5) -> Dict[str, Any]:
        """Test concurrent task creation"""
        print(f"\n=== Testing {num_tasks} Concurrent Tasks (max {max_workers} workers) ===")
        
        results = {
            'test_type': 'concurrent',
            'num_tasks': num_tasks,
            'max_workers': max_workers,
            'tasks': [],
            'total_time': 0,
            'success_count': 0,
            'failure_count': 0
        }
        
        start_time = time.time()
        
        # Prepare tasks
        tasks_to_create = []
        for i in range(num_tasks):
            task_data = random.choice(SAMPLE_TASKS).copy()
            task_data['name'] = f"{task_data['name']} - Concurrent {i+1}"
            tasks_to_create.append(task_data)
        
        # Create tasks concurrently
        created_tasks = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.create_task, task_data): task_data 
                for task_data in tasks_to_create
            }
            
            for future in as_completed(future_to_task):
                task_data = future_to_task[future]
                try:
                    creation_result = future.result()
                    created_tasks.append(creation_result)
                    
                    if creation_result['success']:
                        results['success_count'] += 1
                        print(f"Created task: {creation_result['task_id']}")
                    else:
                        results['failure_count'] += 1
                        print(f"Failed to create task: {creation_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    results['failure_count'] += 1
                    print(f"Exception creating task: {e}")
        
        results['tasks'] = created_tasks
        results['total_time'] = time.time() - start_time
        
        # Monitor some of the created tasks
        print("Monitoring subset of created tasks...")
        monitored_tasks = [task for task in created_tasks if task['success']][:3]  # Monitor first 3 successful
        
        for task in monitored_tasks:
            monitor_result = self.monitor_task(task['task_id'], max_wait_time=120)  # 2 minute timeout
            task.update(monitor_result)
        
        return results
    
    def test_rapid_fire_tasks(self, num_tasks: int = 20, delay: float = 0.1) -> Dict[str, Any]:
        """Test rapid task creation with minimal delay"""
        print(f"\n=== Testing {num_tasks} Rapid Fire Tasks (delay: {delay}s) ===")
        
        results = {
            'test_type': 'rapid_fire',
            'num_tasks': num_tasks,
            'delay': delay,
            'tasks': [],
            'total_time': 0,
            'success_count': 0,
            'failure_count': 0,
            'rate_limited_count': 0
        }
        
        start_time = time.time()
        
        for i in range(num_tasks):
            task_data = random.choice(SAMPLE_TASKS).copy()
            task_data['name'] = f"{task_data['name']} - Rapid {i+1}"
            
            creation_result = self.create_task(task_data)
            
            if creation_result['success']:
                results['success_count'] += 1
            elif 'HTTP 429' in str(creation_result.get('error', '')):
                results['rate_limited_count'] += 1
            else:
                results['failure_count'] += 1
            
            results['tasks'].append(creation_result)
            
            if delay > 0:
                time.sleep(delay)
        
        results['total_time'] = time.time() - start_time
        return results
    
    def test_worker_queue_stress(self) -> Dict[str, Any]:
        """Test worker queue under stress"""
        print("\n=== Testing Worker Queue Stress ===")
        
        # Create many tasks quickly to stress the queue
        burst_result = self.test_rapid_fire_tasks(num_tasks=30, delay=0.05)
        
        # Wait and see how workers handle the load
        print("Waiting for workers to process tasks...")
        time.sleep(60)  # Wait 1 minute
        
        # Check status of created tasks
        completed_tasks = 0
        failed_tasks = 0
        pending_tasks = 0
        
        for task in burst_result['tasks']:
            if task['success']:
                try:
                    response = self.session.get(f"{API_BASE_URL}/tasks/{task['task_id']}")
                    if response.status_code == 200:
                        task_data = response.json()
                        status = task_data['status']
                        
                        if status == 'completed':
                            completed_tasks += 1
                        elif status == 'failed':
                            failed_tasks += 1
                        else:
                            pending_tasks += 1
                            
                except Exception as e:
                    print(f"Error checking task status: {e}")
        
        return {
            'test_type': 'queue_stress',
            'initial_burst': burst_result,
            'final_status': {
                'completed': completed_tasks,
                'failed': failed_tasks,
                'pending': pending_tasks,
                'total_checked': completed_tasks + failed_tasks + pending_tasks
            }
        }
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive worker load test"""
        print("=" * 60)
        print("SELEXTRACT CLOUD WORKER LOAD TEST")
        print("=" * 60)
        
        if not self.authenticate():
            return {'error': 'Authentication failed'}
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'api_base_url': API_BASE_URL,
            'tests': {}
        }
        
        # Run different test scenarios
        try:
            # Sequential tasks test
            test_results['tests']['sequential'] = self.test_sequential_tasks(num_tasks=3)
            
            # Concurrent tasks test
            test_results['tests']['concurrent'] = self.test_concurrent_tasks(num_tasks=8, max_workers=4)
            
            # Rapid fire test
            test_results['tests']['rapid_fire'] = self.test_rapid_fire_tasks(num_tasks=15, delay=0.2)
            
            # Queue stress test
            test_results['tests']['queue_stress'] = self.test_worker_queue_stress()
            
        except Exception as e:
            test_results['error'] = f"Test execution failed: {e}"
        
        return test_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("WORKER LOAD TEST SUMMARY")
        print("=" * 60)
        
        if 'error' in results:
            print(f"❌ Test failed: {results['error']}")
            return
        
        tests = results.get('tests', {})
        
        for test_name, test_data in tests.items():
            print(f"\n📊 {test_name.upper()} TEST:")
            
            if test_name in ['sequential', 'concurrent', 'rapid_fire']:
                success_count = test_data.get('success_count', 0)
                failure_count = test_data.get('failure_count', 0)
                total_tasks = test_data.get('num_tasks', 0)
                total_time = test_data.get('total_time', 0)
                
                print(f"  • Tasks: {total_tasks}")
                print(f"  • Successful: {success_count}")
                print(f"  • Failed: {failure_count}")
                print(f"  • Success Rate: {(success_count/total_tasks*100):.1f}%")
                print(f"  • Total Time: {total_time:.2f}s")
                
                if total_time > 0:
                    print(f"  • Tasks/sec: {total_tasks/total_time:.2f}")
                
                if test_name == 'rapid_fire':
                    rate_limited = test_data.get('rate_limited_count', 0)
                    if rate_limited > 0:
                        print(f"  • Rate Limited: {rate_limited}")
            
            elif test_name == 'queue_stress':
                initial = test_data.get('initial_burst', {})
                final = test_data.get('final_status', {})
                
                print(f"  • Initial Burst: {initial.get('num_tasks', 0)} tasks")
                print(f"  • Completed: {final.get('completed', 0)}")
                print(f"  • Failed: {final.get('failed', 0)}")
                print(f"  • Still Pending: {final.get('pending', 0)}")
        
        print("\n" + "=" * 60)


def main():
    """Main function"""
    try:
        tester = WorkerLoadTester()
        results = tester.run_comprehensive_test()
        
        # Print summary
        tester.print_summary(results)
        
        # Output JSON for analysis
        print("\n📄 Detailed Results (JSON):")
        print(json.dumps(results, indent=2, default=str))
        
        # Return exit code based on results
        if 'error' in results:
            sys.exit(1)
        
        # Check if any tests failed significantly
        tests = results.get('tests', {})
        for test_name, test_data in tests.items():
            if test_name in ['sequential', 'concurrent', 'rapid_fire']:
                success_rate = test_data.get('success_count', 0) / max(test_data.get('num_tasks', 1), 1)
                if success_rate < 0.8:  # Less than 80% success rate
                    print(f"⚠️  Warning: {test_name} test had low success rate: {success_rate*100:.1f}%")
                    sys.exit(1)
        
        print("✅ Worker load test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()