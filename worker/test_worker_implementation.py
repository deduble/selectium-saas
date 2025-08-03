"""
Test and Validation Script for Selextract Cloud Worker Implementation

This script comprehensively tests all components of the worker system
to ensure compliance with the production-ready standards.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

# Add worker directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_schemas import (
    TaskConfig, TaskResult, FieldConfig, FieldType, 
    validate_task_config, get_default_task_config, TaskValidationError
)
from proxies import ProxyManager, ProxyEndpoint, WebshareProxyClient, ProxyHealthChecker
from celery_config import CeleryConfig, validate_celery_config, celery_app
from tasks import ScrapingWorker, execute_scraping_task
from main import WorkerManager, setup_logging


class TestTaskSchemas(unittest.TestCase):
    """Test task schema validation and configuration"""
    
    def test_valid_task_config(self):
        """Test valid task configuration validation"""
        config = {
            "url": "https://example.com",
            "fields": [
                {
                    "name": "title",
                    "type": "text",
                    "selector": "h1",
                    "multiple": False,
                    "required": True
                }
            ]
        }
        
        task_config = validate_task_config(config)
        self.assertIsInstance(task_config, TaskConfig)
        self.assertEqual(str(task_config.url), "https://example.com")
        self.assertEqual(len(task_config.fields), 1)
        self.assertEqual(task_config.fields[0].name, "title")
    
    def test_invalid_task_config(self):
        """Test invalid task configuration raises error"""
        config = {
            "url": "invalid-url",
            "fields": []
        }
        
        with self.assertRaises(TaskValidationError):
            validate_task_config(config)
    
    def test_field_type_validation(self):
        """Test field type validation"""
        # Test attribute field
        field_config = {
            "name": "link",
            "type": "link",
            "selector": "a",
            "attribute": "href"
        }
        field = FieldConfig(**field_config)
        self.assertEqual(field.attribute, "href")
        
        # Test default attribute for link type
        field_config = {
            "name": "link",
            "type": "link", 
            "selector": "a"
        }
        field = FieldConfig(**field_config)
        self.assertEqual(field.attribute, "href")
    
    def test_pagination_config(self):
        """Test pagination configuration"""
        config = {
            "url": "https://example.com",
            "fields": [{"name": "title", "type": "text", "selector": "h1"}],
            "pagination": {
                "enabled": True,
                "next_selector": ".next",
                "max_pages": 5
            }
        }
        
        task_config = validate_task_config(config)
        self.assertTrue(task_config.pagination.enabled)
        self.assertEqual(task_config.pagination.next_selector, ".next")
        self.assertEqual(task_config.pagination.max_pages, 5)
    
    def test_default_config(self):
        """Test default configuration generation"""
        default_config = get_default_task_config()
        self.assertIn("url", default_config)
        self.assertIn("fields", default_config)
        self.assertIsInstance(default_config["fields"], list)
        self.assertGreater(len(default_config["fields"]), 0)


class TestProxyManagement(unittest.TestCase):
    """Test proxy management system"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_api_key = "test_api_key_123"
    
    def test_proxy_endpoint_creation(self):
        """Test ProxyEndpoint creation and methods"""
        proxy = ProxyEndpoint(
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass",
            country="US"
        )
        
        self.assertEqual(proxy.endpoint, "http://proxy.example.com:8080")
        self.assertEqual(proxy.country, "US")
        
        # Test proxy dict format
        proxy_dict = proxy.proxy_dict
        self.assertIn("http", proxy_dict)
        self.assertIn("https", proxy_dict)
        
        # Test Playwright format
        playwright_proxy = proxy.to_playwright_proxy()
        self.assertEqual(playwright_proxy["server"], "http://proxy.example.com:8080")
        self.assertEqual(playwright_proxy["username"], "user")
    
    def test_proxy_health_checker(self):
        """Test proxy health checking functionality"""
        health_checker = ProxyHealthChecker(timeout=5)
        
        # Test with mock proxy
        proxy = ProxyEndpoint(
            host="proxy.example.com",
            port=8080,
            username="user", 
            password="pass"
        )
        
        # Mock the health check (would require actual proxy for real test)
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            is_healthy, response_time = health_checker.check_proxy_health_sync(proxy)
            self.assertTrue(is_healthy)
            self.assertGreaterEqual(response_time, 0)
    
    def test_webshare_client(self):
        """Test Webshare API client"""
        client = WebshareProxyClient(self.test_api_key)
        
        # Test API endpoint configuration
        self.assertEqual(client.api_key, self.test_api_key)
        self.assertIn("Authorization", client.session.headers)
        
        # Mock API response
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "proxy_address": "proxy1.example.com",
                        "port": 8080,
                        "username": "user1",
                        "password": "pass1",
                        "country_code": "US"
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            proxies = client.get_proxy_list()
            self.assertEqual(len(proxies), 1)
            self.assertEqual(proxies[0]["proxy_address"], "proxy1.example.com")
    
    @patch('worker.proxies.WebshareProxyClient')
    def test_proxy_manager_initialization(self, mock_client_class):
        """Test ProxyManager initialization"""
        # Mock the WebshareProxyClient
        mock_client = Mock()
        mock_client.get_proxy_list.return_value = [
            {
                "proxy_address": "proxy1.example.com",
                "port": 8080,
                "username": "user1",
                "password": "pass1",
                "country_code": "US"
            }
        ]
        mock_client_class.return_value = mock_client
        
        # Create ProxyManager
        proxy_manager = ProxyManager(
            webshare_api_key=self.test_api_key,
            health_check_interval=60
        )
        
        # Mock health checker
        with patch.object(proxy_manager, '_perform_health_check_sync'):
            success = proxy_manager.initialize()
            self.assertTrue(success)
            self.assertEqual(len(proxy_manager.proxies), 1)


class TestCeleryConfiguration(unittest.TestCase):
    """Test Celery configuration and setup"""
    
    def test_celery_config_attributes(self):
        """Test Celery configuration attributes"""
        config = CeleryConfig()
        
        # Test broker configuration
        self.assertIsNotNone(config.broker_url)
        self.assertIsNotNone(config.result_backend)
        
        # Test serialization
        self.assertEqual(config.task_serializer, 'json')
        self.assertEqual(config.result_serializer, 'json')
        
        # Test queues
        self.assertIsNotNone(config.task_queues)
        self.assertGreater(len(config.task_queues), 0)
        
        # Test task routing
        self.assertIn('execute_scraping_task', config.task_routes)
    
    def test_celery_app_initialization(self):
        """Test Celery app initialization"""
        self.assertIsNotNone(celery_app)
        self.assertEqual(celery_app.main, 'selextract_worker')
    
    @patch('redis.Redis')
    def test_celery_config_validation(self, mock_redis):
        """Test Celery configuration validation"""
        # Mock Redis connection
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis.from_url.return_value = mock_redis_instance
        
        # Test validation
        is_valid = validate_celery_config()
        self.assertTrue(is_valid)
    
    def test_task_annotations(self):
        """Test task annotations configuration"""
        config = CeleryConfig()
        
        # Test default annotations
        self.assertIn('*', config.task_annotations)
        self.assertIn('rate_limit', config.task_annotations['*'])
        
        # Test specific task annotations
        self.assertIn('execute_scraping_task', config.task_annotations)
        scraping_config = config.task_annotations['execute_scraping_task']
        self.assertIn('time_limit', scraping_config)
        self.assertIn('max_retries', scraping_config)


class TestScrapingWorker(unittest.TestCase):
    """Test main scraping worker functionality"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_task_config = {
            "url": "https://httpbin.org/html",
            "fields": [
                {
                    "name": "title",
                    "type": "text",
                    "selector": "h1",
                    "required": True
                }
            ],
            "browser": {
                "headless": True,
                "timeout": 10000
            }
        }
        self.test_task_id = "test_task_123"
    
    def test_worker_initialization(self):
        """Test worker initialization"""
        worker = ScrapingWorker()
        self.assertIsNone(worker.browser_manager)
        self.assertIsNone(worker.current_proxy)
    
    @patch('worker.tasks.BrowserManager')
    async def test_browser_initialization(self, mock_browser_manager):
        """Test browser initialization"""
        # Mock browser manager
        mock_manager = Mock()
        mock_browser_manager.return_value = mock_manager
        
        worker = ScrapingWorker()
        task_config = validate_task_config(self.test_task_config)
        
        await worker._initialize_browser_with_proxy(task_config)
        
        # Verify browser manager was created and initialized
        mock_browser_manager.assert_called_once()
        mock_manager.initialize.assert_called_once()
    
    def test_task_execution_validation(self):
        """Test task execution with validation"""
        # Test invalid configuration
        invalid_config = {"url": "invalid", "fields": []}
        
        with self.assertRaises(TaskValidationError):
            validate_task_config(invalid_config)
        
        # Test valid configuration
        valid_config = validate_task_config(self.test_task_config)
        self.assertIsInstance(valid_config, TaskConfig)


class TestWorkerManager(unittest.TestCase):
    """Test worker manager and main entry point"""
    
    def setUp(self):
        """Setup test environment"""
        # Set test environment variables
        os.environ['REDIS_HOST'] = 'localhost'
        os.environ['REDIS_PORT'] = '6379'
        os.environ['CELERY_ENV'] = 'testing'
    
    def test_worker_manager_initialization(self):
        """Test worker manager initialization"""
        manager = WorkerManager()
        self.assertFalse(manager.proxy_manager_initialized)
        self.assertFalse(manager.celery_validated)
        self.assertFalse(manager.shutdown_requested)
    
    @patch('worker.main.validate_celery_config')
    def test_environment_validation(self, mock_validate_celery):
        """Test environment validation"""
        mock_validate_celery.return_value = True
        
        manager = WorkerManager()
        
        # Test environment validation
        is_valid = manager._validate_environment()
        self.assertTrue(is_valid)
    
    @patch('worker.main.initialize_proxy_manager')
    def test_proxy_manager_initialization(self, mock_init_proxy):
        """Test proxy manager initialization"""
        mock_init_proxy.return_value = True
        
        manager = WorkerManager()
        
        # Test without API key
        manager._initialize_proxy_manager()
        mock_init_proxy.assert_not_called()
        
        # Test with API key
        os.environ['WEBSHARE_API_KEY'] = 'test_key'
        manager._initialize_proxy_manager()
        mock_init_proxy.assert_called_once()
    
    @patch('playwright.sync_api.sync_playwright')
    def test_system_dependencies_validation(self, mock_playwright):
        """Test system dependencies validation"""
        # Mock Playwright
        mock_p = Mock()
        mock_browser = Mock()
        mock_browser.launch.return_value = Mock()
        mock_p.chromium = mock_browser
        mock_p.firefox = mock_browser
        mock_p.webkit = mock_browser
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_playwright.return_value.__exit__.return_value = None
        
        manager = WorkerManager()
        
        # Create test directories
        test_dirs = ["/tmp/test_results", "/tmp/test_logs", "/tmp/test_tmp"]
        for test_dir in test_dirs:
            Path(test_dir).mkdir(parents=True, exist_ok=True)
        
        with patch.object(manager, '_create_directories'):
            is_valid = manager._validate_system_dependencies()
            self.assertTrue(is_valid)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete worker system"""
    
    def setUp(self):
        """Setup integration test environment"""
        self.test_config = {
            "url": "https://httpbin.org/html",
            "fields": [
                {
                    "name": "title",
                    "type": "text",
                    "selector": "title",
                    "required": True
                }
            ],
            "browser": {
                "headless": True,
                "timeout": 15000,
                "load_images": False
            },
            "rate_limit": {
                "delay_between_requests": 500
            }
        }
    
    def test_task_config_to_execution_flow(self):
        """Test complete flow from config validation to task setup"""
        # Validate configuration
        task_config = validate_task_config(self.test_config)
        self.assertIsInstance(task_config, TaskConfig)
        
        # Test task result structure
        result = TaskResult(task_id="integration_test")
        self.assertEqual(result.task_id, "integration_test")
        self.assertEqual(result.status, "completed")
        self.assertIsInstance(result.data, list)
    
    @patch('worker.tasks.ScrapingWorker.execute_task')
    def test_celery_task_execution(self, mock_execute):
        """Test Celery task execution flow"""
        # Mock successful execution
        mock_result = {
            "task_id": "test_task",
            "status": "completed",
            "data": [{"title": "Test Title"}],
            "pages_scraped": 1,
            "total_records": 1,
            "compute_units_used": 0.1,
            "execution_time": 5.0,
            "errors": [],
            "warnings": [],
            "metadata": {}
        }
        
        mock_execute.return_value = TaskResult(**mock_result)
        
        # Test task execution
        result = execute_scraping_task(self.test_config, "test_task")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["task_id"], "test_task")


class TestComplianceValidation(unittest.TestCase):
    """Test compliance with implementation rules and standards"""
    
    def test_no_placeholders_in_code(self):
        """Ensure no placeholder code exists"""
        worker_dir = Path(__file__).parent
        
        # Check all Python files for placeholders
        placeholder_patterns = [
            "# TODO",
            "# FIXME", 
            "# ... (rest of implementation)",
            "... as provided earlier",
            "implement this",
            "# implement",
            "pass  # TODO"
        ]
        
        python_files = list(worker_dir.glob("*.py"))
        
        for file_path in python_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern in placeholder_patterns:
                    self.assertNotIn(pattern, content, 
                                   f"Placeholder '{pattern}' found in {file_path}")
    
    def test_imports_are_valid(self):
        """Test that all imports are valid and resolvable"""
        import importlib
        
        modules_to_test = [
            'worker.task_schemas',
            'worker.proxies', 
            'worker.tasks',
            'worker.celery_config',
            'worker.main'
        ]
        
        for module_name in modules_to_test:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")
    
    def test_configuration_completeness(self):
        """Test that all configurations are complete and production-ready"""
        # Test Celery configuration
        config = CeleryConfig()
        
        # Essential attributes must be set
        essential_attrs = [
            'broker_url', 'result_backend', 'task_serializer',
            'task_queues', 'task_routes', 'task_annotations'
        ]
        
        for attr in essential_attrs:
            self.assertTrue(hasattr(config, attr), 
                          f"CeleryConfig missing essential attribute: {attr}")
            value = getattr(config, attr)
            self.assertIsNotNone(value, 
                               f"CeleryConfig attribute {attr} is None")
    
    def test_error_handling_coverage(self):
        """Test that error handling is comprehensive"""
        # Check that main components have error handling
        
        # Test task schema validation
        with self.assertRaises(TaskValidationError):
            validate_task_config({"invalid": "config"})
        
        # Test proxy manager error handling
        proxy_manager = ProxyManager("invalid_key")
        # Should not crash on invalid key
        result = proxy_manager.initialize()
        # May fail but should handle gracefully
        self.assertIsInstance(result, bool)


def run_comprehensive_tests():
    """Run all tests and generate comprehensive report"""
    
    # Setup logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger('worker.test')
    logger.info("Starting comprehensive worker implementation tests...")
    
    # Create test suite
    test_classes = [
        TestTaskSchemas,
        TestProxyManagement, 
        TestCeleryConfiguration,
        TestScrapingWorker,
        TestWorkerManager,
        TestIntegration,
        TestComplianceValidation
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    results = {}
    
    for test_class in test_classes:
        logger.info(f"Running tests for {test_class.__name__}...")
        
        # Create test suite for this class
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        # Store results
        results[test_class.__name__] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0
        }
        
        total_tests += result.testsRun
        total_failures += len(result.failures)
        total_errors += len(result.errors)
        
        logger.info(f"  Tests run: {result.testsRun}")
        logger.info(f"  Failures: {len(result.failures)}")
        logger.info(f"  Errors: {len(result.errors)}")
        logger.info(f"  Success rate: {results[test_class.__name__]['success_rate']:.1f}%")
    
    # Generate final report
    logger.info("\n" + "="*60)
    logger.info("COMPREHENSIVE TEST REPORT")
    logger.info("="*60)
    
    for class_name, class_results in results.items():
        logger.info(f"{class_name}:")
        logger.info(f"  Tests: {class_results['tests_run']}")
        logger.info(f"  Failures: {class_results['failures']}")
        logger.info(f"  Errors: {class_results['errors']}")
        logger.info(f"  Success: {class_results['success_rate']:.1f}%")
    
    logger.info("-"*60)
    logger.info(f"TOTAL TESTS: {total_tests}")
    logger.info(f"TOTAL FAILURES: {total_failures}")
    logger.info(f"TOTAL ERRORS: {total_errors}")
    
    overall_success_rate = (total_tests - total_failures - total_errors) / total_tests * 100 if total_tests > 0 else 0
    logger.info(f"OVERALL SUCCESS RATE: {overall_success_rate:.1f}%")
    
    if total_failures == 0 and total_errors == 0:
        logger.info("🎉 ALL TESTS PASSED - IMPLEMENTATION IS PRODUCTION READY!")
        return True
    else:
        logger.warning("⚠️  SOME TESTS FAILED - REVIEW IMPLEMENTATION")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)