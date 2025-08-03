"""
Main Worker Implementation for Selextract Cloud

This module implements the complete scraping worker system using Playwright
with proxy rotation, stealth measures, and robust error handling.
"""

import asyncio
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import traceback

from celery import Celery
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import aiofiles

from task_schemas import (
    TaskConfig, TaskResult, FieldConfig, FieldType, WaitCondition,
    PaginationConfig, validate_task_config, TaskValidationError
)
from proxies import get_proxy_manager, ProxyEndpoint
from celery_config import celery_app


logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    def __init__(self, message: str, error_type: str = "general", retryable: bool = True):
        self.message = message
        self.error_type = error_type
        self.retryable = retryable
        super().__init__(self.message)


class BrowserManager:
    """Manages Playwright browser instances with stealth configuration"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    async def initialize(self, task_config: TaskConfig, proxy: Optional[ProxyEndpoint] = None) -> None:
        """
        Initialize browser with stealth measures and proxy configuration
        
        Args:
            task_config: Task configuration
            proxy: Optional proxy endpoint
        """
        try:
            self.playwright = await async_playwright().start()
            
            # Browser launch options with stealth measures
            launch_options = {
                'headless': task_config.browser.headless,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            }
            
            # Add proxy configuration if available
            if proxy:
                launch_options['proxy'] = proxy.to_playwright_proxy()
                logger.info(f"Using proxy: {proxy.endpoint} ({proxy.country})")
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # Context options with stealth measures
            context_options = {
                'viewport': {
                    'width': task_config.browser.viewport_width,
                    'height': task_config.browser.viewport_height
                },
                'user_agent': task_config.browser.user_agent or self._get_random_user_agent(),
                'java_script_enabled': task_config.browser.javascript_enabled,
                'accept_downloads': False,
                'ignore_https_errors': True,
                'extra_http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0',
                    **task_config.custom_headers
                }
            }
            
            # Add cookies if provided
            self.context = await self.browser.new_context(**context_options)
            
            if task_config.cookies:
                cookie_list = [
                    {'name': name, 'value': value, 'domain': self._extract_domain(str(task_config.url))}
                    for name, value in task_config.cookies.items()
                ]
                await self.context.add_cookies(cookie_list)
            
            # Block unnecessary resources for faster loading
            if not task_config.browser.load_images:
                await self.context.route("**/*.{png,jpg,jpeg,gif,svg,ico,webp}", lambda route: route.abort())
                await self.context.route("**/*.{css,woff,woff2,ttf,eot}", lambda route: route.abort())
            
            # Create page with stealth modifications
            self.page = await self.context.new_page()
            
            # Inject stealth scripts
            await self._inject_stealth_scripts()
            
            # Set timeout
            self.page.set_default_timeout(task_config.browser.timeout)
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            await self.cleanup()
            raise ScrapingError(f"Failed to initialize browser: {str(e)}", "browser_init")
    
    async def _inject_stealth_scripts(self) -> None:
        """Inject stealth scripts to avoid detection"""
        stealth_scripts = [
            # Override webdriver property
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            """,
            # Override plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            """,
            # Override languages
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            """,
            # Override permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """,
            # Override chrome runtime
            """
            if (!window.chrome) {
                window.chrome = {};
            }
            if (!window.chrome.runtime) {
                window.chrome.runtime = {};
            }
            """
        ]
        
        for script in stealth_scripts:
            await self.page.add_init_script(script)
    
    def _get_random_user_agent(self) -> str:
        """Get a random realistic user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        return random.choice(user_agents)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for cookies"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    
    async def navigate_to_page(self, url: str, wait_conditions: List[WaitCondition]) -> None:
        """
        Navigate to page with wait conditions
        
        Args:
            url: Target URL
            wait_conditions: List of wait conditions
        """
        try:
            # Navigate to page
            await self.page.goto(url, wait_until='domcontentloaded')
            logger.info(f"Navigated to: {url}")
            
            # Apply wait conditions
            for condition in wait_conditions:
                await self._apply_wait_condition(condition)
            
            # Random delay to appear more human
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            raise ScrapingError(f"Failed to navigate to page: {str(e)}", "navigation")
    
    async def _apply_wait_condition(self, condition: WaitCondition) -> None:
        """Apply a specific wait condition"""
        try:
            if condition.type == "element" and condition.selector:
                await self.page.wait_for_selector(condition.selector, timeout=condition.timeout)
            elif condition.type == "timeout":
                await asyncio.sleep(condition.timeout / 1000)
            elif condition.type == "network" and condition.network_idle:
                await self.page.wait_for_load_state('networkidle', timeout=condition.timeout)
        except PlaywrightTimeoutError:
            logger.warning(f"Wait condition timeout: {condition.type}")
    
    async def cleanup(self) -> None:
        """Cleanup browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during browser cleanup: {str(e)}")


class DataExtractor:
    """Handles data extraction from web pages"""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def extract_fields(self, fields: List[FieldConfig]) -> Dict[str, Any]:
        """
        Extract all configured fields from the current page
        
        Args:
            fields: List of field configurations
            
        Returns:
            Dictionary of extracted data
        """
        extracted_data = {}
        
        for field in fields:
            try:
                value = await self._extract_single_field(field)
                extracted_data[field.name] = value
                
                if field.required and not value:
                    logger.warning(f"Required field '{field.name}' is empty")
                
            except Exception as e:
                logger.error(f"Failed to extract field '{field.name}': {str(e)}")
                
                if field.required:
                    extracted_data[field.name] = field.default_value
                else:
                    extracted_data[field.name] = None
        
        return extracted_data
    
    async def _extract_single_field(self, field: FieldConfig) -> Any:
        """Extract a single field based on its configuration"""
        try:
            if field.multiple:
                elements = await self.page.query_selector_all(field.selector)
                values = []
                
                for element in elements:
                    value = await self._extract_element_value(element, field)
                    if value:
                        values.append(value)
                
                return values
            else:
                element = await self.page.query_selector(field.selector)
                if element:
                    return await self._extract_element_value(element, field)
                else:
                    return field.default_value
                    
        except Exception as e:
            logger.error(f"Error extracting field {field.name}: {str(e)}")
            return field.default_value
    
    async def _extract_element_value(self, element, field: FieldConfig) -> Optional[str]:
        """Extract value from a single element based on field type"""
        try:
            if field.type == FieldType.TEXT:
                return await element.inner_text()
            elif field.type == FieldType.ATTRIBUTE:
                return await element.get_attribute(field.attribute)
            elif field.type == FieldType.LINK:
                href = await element.get_attribute(field.attribute or 'href')
                if href:
                    # Convert relative URLs to absolute
                    return await self.page.evaluate(f'new URL("{href}", location.href).href')
                return href
            elif field.type == FieldType.IMAGE:
                src = await element.get_attribute(field.attribute or 'src')
                if src:
                    # Convert relative URLs to absolute
                    return await self.page.evaluate(f'new URL("{src}", location.href).href')
                return src
            else:
                return await element.inner_text()
                
        except Exception as e:
            logger.error(f"Error extracting element value: {str(e)}")
            return None


class PaginationHandler:
    """Handles pagination navigation"""
    
    def __init__(self, page: Page, config: PaginationConfig):
        self.page = page
        self.config = config
        self.current_page = 1
    
    async def has_next_page(self) -> bool:
        """Check if there's a next page available"""
        if not self.config.enabled:
            return False
        
        if self.current_page >= self.config.max_pages:
            return False
        
        # Check for stop condition
        if self.config.stop_condition:
            stop_element = await self.page.query_selector(self.config.stop_condition)
            if stop_element:
                return False
        
        # Check for next page element
        if self.config.next_selector:
            next_element = await self.page.query_selector(self.config.next_selector)
            if next_element:
                # Check if element is disabled or not clickable
                is_disabled = await next_element.is_disabled()
                is_visible = await next_element.is_visible()
                return not is_disabled and is_visible
        
        return False
    
    async def go_to_next_page(self) -> bool:
        """
        Navigate to the next page
        
        Returns:
            True if navigation was successful, False otherwise
        """
        try:
            if not await self.has_next_page():
                return False
            
            next_element = await self.page.query_selector(self.config.next_selector)
            if not next_element:
                return False
            
            # Click the next page button/link
            await next_element.click()
            
            # Wait for page to load
            await asyncio.sleep(self.config.wait_after_click / 1000)
            
            # Wait for network to be idle
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            
            self.current_page += 1
            logger.info(f"Navigated to page {self.current_page}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to next page: {str(e)}")
            return False


class ScrapingWorker:
    """Main scraping worker class"""
    
    def __init__(self):
        self.browser_manager = None
        self.proxy_manager = get_proxy_manager()
        self.current_proxy = None
        self.task_start_time = None
        self.compute_units_used = 0.0
    
    async def execute_task(self, task_config_dict: Dict[str, Any], task_id: str) -> TaskResult:
        """
        Execute a complete scraping task
        
        Args:
            task_config_dict: Task configuration dictionary
            task_id: Unique task identifier
            
        Returns:
            TaskResult with execution results
        """
        self.task_start_time = time.time()
        result = TaskResult(task_id=task_id)
        
        try:
            # Validate task configuration
            task_config = validate_task_config(task_config_dict)
            logger.info(f"Starting task {task_id} for URL: {task_config.url}")
            
            # Initialize browser with proxy
            await self._initialize_browser_with_proxy(task_config)
            
            # Execute scraping with retries
            await self._execute_scraping_with_retries(task_config, result)
            
            # Calculate compute units (1 CU = 1 minute)
            execution_time = time.time() - self.task_start_time
            self.compute_units_used = max(execution_time / 60, 0.1)  # Minimum 0.1 CU
            
            result.compute_units_used = self.compute_units_used
            result.execution_time = execution_time
            
            if result.data:
                result.status = "completed"
                result.total_records = sum(len(page_data) if isinstance(page_data, list) else 1 for page_data in result.data)
            else:
                result.status = "failed"
                result.errors.append("No data extracted")
            
            logger.info(f"Task {task_id} completed: {result.total_records} records, {result.pages_scraped} pages")
            
        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.error(f"Task {task_id} failed: {str(e)}")
            
        finally:
            # Cleanup
            await self._cleanup()
            
            # Save results to file
            await self._save_results_to_file(result)
        
        return result
    
    async def _initialize_browser_with_proxy(self, task_config: TaskConfig, retry_count: int = 0) -> None:
        """Initialize browser with proxy support and retry logic"""
        max_retries = 3
        
        try:
            # Get proxy if enabled
            if task_config.proxy.enabled and self.proxy_manager:
                self.current_proxy = self.proxy_manager.get_proxy(
                    country=task_config.proxy.country,
                    sticky_session=task_config.proxy.sticky_session
                )
                
                if not self.current_proxy:
                    raise ScrapingError("No healthy proxies available", "proxy_unavailable")
            
            # Initialize browser
            self.browser_manager = BrowserManager()
            await self.browser_manager.initialize(task_config, self.current_proxy)
            
        except Exception as e:
            if retry_count < max_retries:
                logger.warning(f"Browser initialization failed (attempt {retry_count + 1}): {str(e)}")
                
                # Mark proxy as failed if it was used
                if self.current_proxy and self.proxy_manager:
                    self.proxy_manager.mark_proxy_failed(self.current_proxy)
                
                # Cleanup and retry
                await self._cleanup()
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                await self._initialize_browser_with_proxy(task_config, retry_count + 1)
            else:
                raise ScrapingError(f"Failed to initialize browser after {max_retries} attempts: {str(e)}", "browser_init")
    
    async def _execute_scraping_with_retries(self, task_config: TaskConfig, result: TaskResult) -> None:
        """Execute scraping with retry logic"""
        max_retries = task_config.max_retries
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                await self._execute_scraping(task_config, result)
                
                # Mark proxy as successful if used
                if self.current_proxy and self.proxy_manager:
                    self.proxy_manager.mark_proxy_success(self.current_proxy)
                
                return  # Success, exit retry loop
                
            except ScrapingError as e:
                retry_count += 1
                
                if not e.retryable or retry_count > max_retries:
                    raise e
                
                logger.warning(f"Scraping failed (attempt {retry_count}): {e.message}")
                result.warnings.append(f"Retry {retry_count}: {e.message}")
                
                # Handle proxy failure
                if e.error_type == "proxy_failure" and self.current_proxy and self.proxy_manager:
                    self.proxy_manager.mark_proxy_failed(self.current_proxy)
                    
                    # Reinitialize with new proxy
                    await self._cleanup()
                    await self._initialize_browser_with_proxy(task_config)
                
                # Wait before retry
                await asyncio.sleep(task_config.retry_delay / 1000)
        
        raise ScrapingError(f"Scraping failed after {max_retries} retries", "max_retries_exceeded")
    
    async def _execute_scraping(self, task_config: TaskConfig, result: TaskResult) -> None:
        """Execute the main scraping logic"""
        try:
            # Navigate to initial page
            await self.browser_manager.navigate_to_page(str(task_config.url), task_config.wait_conditions)
            
            # Initialize data extractor and pagination handler
            data_extractor = DataExtractor(self.browser_manager.page)
            pagination_handler = PaginationHandler(self.browser_manager.page, task_config.pagination)
            
            # Extract data from all pages
            while True:
                # Apply rate limiting
                if result.pages_scraped > 0:
                    delay = task_config.rate_limit.delay_between_requests / 1000
                    if task_config.rate_limit.random_delay:
                        delay += random.uniform(0, task_config.rate_limit.max_random_delay / 1000)
                    await asyncio.sleep(delay)
                
                # Extract data from current page
                page_data = await data_extractor.extract_fields(task_config.fields)
                result.data.append(page_data)
                result.pages_scraped += 1
                
                logger.info(f"Extracted data from page {result.pages_scraped}")
                
                # Check if we should continue to next page
                if not await pagination_handler.has_next_page():
                    break
                
                # Navigate to next page
                if not await pagination_handler.go_to_next_page():
                    break
            
        except PlaywrightTimeoutError as e:
            raise ScrapingError(f"Page timeout: {str(e)}", "timeout", retryable=True)
        except Exception as e:
            error_message = str(e)
            
            # Check for proxy-related errors
            if any(keyword in error_message.lower() for keyword in ['proxy', 'connection', 'network']):
                raise ScrapingError(f"Proxy error: {error_message}", "proxy_failure", retryable=True)
            else:
                raise ScrapingError(f"Scraping error: {error_message}", "scraping", retryable=True)
    
    async def _save_results_to_file(self, result: TaskResult) -> None:
        """Save results to JSON file"""
        try:
            # Create results directory if it doesn't exist
            results_dir = Path("/app/results")
            results_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"task_{result.task_id}_{timestamp}.json"
            filepath = results_dir / filename
            
            # Prepare result data
            result_dict = {
                "task_id": result.task_id,
                "status": result.status,
                "data": result.data,
                "pages_scraped": result.pages_scraped,
                "total_records": result.total_records,
                "compute_units_used": result.compute_units_used,
                "execution_time": result.execution_time,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": {
                    **result.metadata,
                    "timestamp": datetime.now().isoformat(),
                    "proxy_used": self.current_proxy.endpoint if self.current_proxy else None,
                    "proxy_country": self.current_proxy.country if self.current_proxy else None
                }
            }
            
            # Save to file
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(result_dict, indent=2, ensure_ascii=False))
            
            logger.info(f"Results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save results to file: {str(e)}")
            result.warnings.append(f"Failed to save results: {str(e)}")
    
    async def _cleanup(self) -> None:
        """Cleanup browser resources"""
        if self.browser_manager:
            await self.browser_manager.cleanup()
            self.browser_manager = None


# Celery task definitions
@celery_app.task(bind=True, name='execute_scraping_task')
def execute_scraping_task(self, task_config: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """
    Main Celery task for executing scraping jobs
    
    Args:
        task_config: Task configuration dictionary
        task_id: Unique task identifier
        
    Returns:
        Task result dictionary
    """
    try:
        # Run the async scraping worker
        worker = ScrapingWorker()
        result = asyncio.run(worker.execute_task(task_config, task_id))
        
        return {
            "task_id": result.task_id,
            "status": result.status,
            "data": result.data,
            "pages_scraped": result.pages_scraped,
            "total_records": result.total_records,
            "compute_units_used": result.compute_units_used,
            "execution_time": result.execution_time,
            "errors": result.errors,
            "warnings": result.warnings,
            "metadata": result.metadata
        }
        
    except Exception as e:
        logger.error(f"Task {task_id} failed with exception: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "task_id": task_id,
            "status": "failed",
            "data": [],
            "pages_scraped": 0,
            "total_records": 0,
            "compute_units_used": 0.0,
            "execution_time": 0.0,
            "errors": [str(e)],
            "warnings": [],
            "metadata": {"exception": traceback.format_exc()}
        }


@celery_app.task(name='cleanup_old_results')
def cleanup_old_results(days_old: int = 7) -> Dict[str, Any]:
    """
    Cleanup old result files
    
    Args:
        days_old: Files older than this many days will be deleted
        
    Returns:
        Cleanup statistics
    """
    try:
        results_dir = Path("/app/results")
        if not results_dir.exists():
            return {"deleted_files": 0, "freed_space": 0}
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_files = 0
        freed_space = 0
        
        for file_path in results_dir.glob("task_*.json"):
            if file_path.stat().st_mtime < cutoff_date.timestamp():
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_files += 1
                freed_space += file_size
        
        logger.info(f"Cleanup completed: {deleted_files} files deleted, {freed_space} bytes freed")
        
        return {
            "deleted_files": deleted_files,
            "freed_space": freed_space,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        return {"error": str(e)}


@celery_app.task(name='refresh_user_compute_units')
def refresh_user_compute_units() -> Dict[str, Any]:
    """
    Background task to refresh user compute units
    
    Returns:
        Refresh statistics
    """
    try:
        # This would typically connect to the database and refresh compute units
        # Implementation depends on the database schema and business logic
        logger.info("Compute units refresh task executed")
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Compute units refresh failed: {str(e)}")
        return {"error": str(e)}


@celery_app.task(name='proxy_health_check')
def proxy_health_check() -> Dict[str, Any]:
    """
    Background task for proxy health checking
    
    Returns:
        Health check statistics
    """
    try:
        proxy_manager = get_proxy_manager()
        if not proxy_manager:
            return {"error": "Proxy manager not initialized"}
        
        stats = proxy_manager.get_stats()
        logger.info(f"Proxy health check completed: {stats}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Proxy health check failed: {str(e)}")
        return {"error": str(e)}


# Export main task
__all__ = [
    'ScrapingWorker',
    'execute_scraping_task',
    'cleanup_old_results', 
    'refresh_user_compute_units',
    'proxy_health_check'
]