"""
Proxy Management System for Selextract Cloud Worker

This module implements proxy rotation and health checking for Webshare.io
integration with automatic failover and country-specific proxy selection.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import aiohttp
import requests
from requests.auth import HTTPProxyAuth

from task_schemas import ProxyInfo


logger = logging.getLogger(__name__)


@dataclass
class ProxyEndpoint:
    """Proxy endpoint configuration"""
    host: str
    port: int
    username: str
    password: str
    country: Optional[str] = None
    city: Optional[str] = None
    is_healthy: bool = True
    failure_count: int = 0
    last_checked: Optional[datetime] = None
    response_time: Optional[float] = None
    last_used: Optional[datetime] = None
    
    @property
    def endpoint(self) -> str:
        """Get proxy endpoint URL"""
        return f"http://{self.host}:{self.port}"
    
    @property
    def auth(self) -> HTTPProxyAuth:
        """Get proxy authentication"""
        return HTTPProxyAuth(self.username, self.password)
    
    @property
    def proxy_dict(self) -> Dict[str, str]:
        """Get proxy configuration for requests"""
        proxy_url = f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def to_playwright_proxy(self) -> Dict[str, Any]:
        """Convert to Playwright proxy format"""
        return {
            'server': f"http://{self.host}:{self.port}",
            'username': self.username,
            'password': self.password
        }


class ProxyHealthChecker:
    """Health checking for proxy endpoints"""
    
    def __init__(self, timeout: int = 10, test_urls: Optional[List[str]] = None):
        self.timeout = timeout
        self.test_urls = test_urls or [
            'http://httpbin.org/ip',
            'https://ifconfig.me/ip',
            'http://icanhazip.com'
        ]
    
    async def check_proxy_health(self, proxy: ProxyEndpoint) -> Tuple[bool, float]:
        """
        Check if a proxy is healthy and measure response time
        
        Args:
            proxy: Proxy endpoint to check
            
        Returns:
            Tuple of (is_healthy, response_time_ms)
        """
        start_time = time.time()
        
        try:
            # Test with a simple HTTP request
            test_url = random.choice(self.test_urls)
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                
                async with session.get(
                    test_url,
                    proxy=proxy_url,
                    headers={'User-Agent': 'Selextract-HealthCheck/1.0'}
                ) as response:
                    if response.status == 200:
                        response_time = (time.time() - start_time) * 1000
                        logger.debug(f"Proxy {proxy.endpoint} health check passed: {response_time:.2f}ms")
                        return True, response_time
                    else:
                        logger.warning(f"Proxy {proxy.endpoint} returned status {response.status}")
                        return False, 0.0
                        
        except Exception as e:
            logger.warning(f"Proxy {proxy.endpoint} health check failed: {str(e)}")
            return False, 0.0
    
    def check_proxy_health_sync(self, proxy: ProxyEndpoint) -> Tuple[bool, float]:
        """
        Synchronous proxy health check
        
        Args:
            proxy: Proxy endpoint to check
            
        Returns:
            Tuple of (is_healthy, response_time_ms)
        """
        start_time = time.time()
        
        try:
            test_url = random.choice(self.test_urls)
            
            response = requests.get(
                test_url,
                proxies=proxy.proxy_dict,
                timeout=self.timeout,
                headers={'User-Agent': 'Selextract-HealthCheck/1.0'}
            )
            
            if response.status_code == 200:
                response_time = (time.time() - start_time) * 1000
                logger.debug(f"Proxy {proxy.endpoint} health check passed: {response_time:.2f}ms")
                return True, response_time
            else:
                logger.warning(f"Proxy {proxy.endpoint} returned status {response.status_code}")
                return False, 0.0
                
        except Exception as e:
            logger.warning(f"Proxy {proxy.endpoint} health check failed: {str(e)}")
            return False, 0.0


class WebshareProxyClient:
    """Client for Webshare.io API integration"""
    
    def __init__(self, api_key: str, base_url: str = "https://proxy.webshare.io/api/v2"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_key}',
            'Content-Type': 'application/json'
        })
    
    def get_proxy_list(self, country: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch proxy list from Webshare.io
        
        Args:
            country: Filter by country code (e.g., 'US', 'GB')
            limit: Maximum number of proxies to fetch
            
        Returns:
            List of proxy configurations
        """
        try:
            params = {'page_size': limit}
            if country:
                params['country_code'] = country.upper()
            
            response = self.session.get(f'{self.base_url}/proxy/list/', params=params)
            response.raise_for_status()
            
            data = response.json()
            proxies = data.get('results', [])
            
            logger.info(f"Fetched {len(proxies)} proxies from Webshare.io")
            return proxies
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch proxies from Webshare.io: {str(e)}")
            return []
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information and usage stats"""
        try:
            response = self.session.get(f'{self.base_url}/profile/')
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return {}


class ProxyManager:
    """
    Main proxy management system with rotation, health checking,
    and automatic failover capabilities
    """
    
    def __init__(
        self,
        webshare_api_key: str,
        health_check_interval: int = 300,  # 5 minutes
        max_failures: int = 3,
        country_preference: Optional[str] = None
    ):
        self.webshare_client = WebshareProxyClient(webshare_api_key)
        self.health_checker = ProxyHealthChecker()
        self.health_check_interval = health_check_interval
        self.max_failures = max_failures
        self.country_preference = country_preference
        
        # Proxy storage
        self.proxies: Dict[str, ProxyEndpoint] = {}
        self.healthy_proxies: List[str] = []
        self.current_proxy_index = 0
        
        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None
        self._stop_health_check = False
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'failed_requests': 0,
            'proxy_switches': 0,
            'last_refresh': None
        }
    
    def initialize(self) -> bool:
        """
        Initialize proxy manager by fetching proxies from Webshare.io
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing proxy manager...")
            
            # Fetch proxies from Webshare.io
            proxy_data = self.webshare_client.get_proxy_list(
                country=self.country_preference,
                limit=100
            )
            
            if not proxy_data:
                logger.error("No proxies available from Webshare.io")
                return False
            
            # Convert to ProxyEndpoint objects
            for proxy_info in proxy_data:
                endpoint = ProxyEndpoint(
                    host=proxy_info['proxy_address'],
                    port=proxy_info['port'],
                    username=proxy_info['username'],
                    password=proxy_info['password'],
                    country=proxy_info.get('country_code'),
                    city=proxy_info.get('city_name')
                )
                
                proxy_id = f"{endpoint.host}:{endpoint.port}"
                self.proxies[proxy_id] = endpoint
            
            logger.info(f"Loaded {len(self.proxies)} proxies")
            
            # Initial health check
            self._perform_health_check_sync()
            
            # Start async health checking
            self._start_health_monitoring()
            
            self.stats['last_refresh'] = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize proxy manager: {str(e)}")
            return False
    
    def get_proxy(self, country: Optional[str] = None, sticky_session: bool = False) -> Optional[ProxyEndpoint]:
        """
        Get next available healthy proxy
        
        Args:
            country: Preferred country code
            sticky_session: Use same proxy for session consistency
            
        Returns:
            ProxyEndpoint or None if no healthy proxies available
        """
        if not self.healthy_proxies:
            logger.warning("No healthy proxies available")
            return None
        
        # Filter by country if specified
        available_proxies = self.healthy_proxies
        if country:
            country_proxies = [
                proxy_id for proxy_id in self.healthy_proxies
                if self.proxies[proxy_id].country == country.upper()
            ]
            if country_proxies:
                available_proxies = country_proxies
        
        if not available_proxies:
            logger.warning(f"No healthy proxies available for country {country}")
            return None
        
        # Select proxy (round-robin or sticky)
        if sticky_session and hasattr(self, '_last_proxy') and self._last_proxy in available_proxies:
            proxy_id = self._last_proxy
        else:
            proxy_id = available_proxies[self.current_proxy_index % len(available_proxies)]
            self.current_proxy_index += 1
            self._last_proxy = proxy_id
        
        proxy = self.proxies[proxy_id]
        proxy.last_used = datetime.now()
        
        logger.debug(f"Selected proxy: {proxy.endpoint} ({proxy.country})")
        return proxy
    
    def mark_proxy_failed(self, proxy: ProxyEndpoint) -> None:
        """
        Mark a proxy as failed and potentially remove from healthy list
        
        Args:
            proxy: Failed proxy endpoint
        """
        proxy_id = f"{proxy.host}:{proxy.port}"
        if proxy_id in self.proxies:
            self.proxies[proxy_id].failure_count += 1
            self.proxies[proxy_id].is_healthy = False
            
            if proxy_id in self.healthy_proxies:
                self.healthy_proxies.remove(proxy_id)
                self.stats['proxy_switches'] += 1
                logger.warning(f"Removed unhealthy proxy: {proxy.endpoint} (failures: {proxy.failure_count})")
        
        self.stats['failed_requests'] += 1
    
    def mark_proxy_success(self, proxy: ProxyEndpoint) -> None:
        """
        Mark a proxy as successful and reset failure count
        
        Args:
            proxy: Successful proxy endpoint
        """
        proxy_id = f"{proxy.host}:{proxy.port}"
        if proxy_id in self.proxies:
            self.proxies[proxy_id].failure_count = 0
            self.proxies[proxy_id].is_healthy = True
            
            if proxy_id not in self.healthy_proxies:
                self.healthy_proxies.append(proxy_id)
                logger.info(f"Restored healthy proxy: {proxy.endpoint}")
        
        self.stats['total_requests'] += 1
    
    def _perform_health_check_sync(self) -> None:
        """Perform synchronous health check on all proxies"""
        logger.info("Performing health check on all proxies...")
        
        healthy_count = 0
        for proxy_id, proxy in self.proxies.items():
            is_healthy, response_time = self.health_checker.check_proxy_health_sync(proxy)
            
            proxy.is_healthy = is_healthy
            proxy.response_time = response_time
            proxy.last_checked = datetime.now()
            
            if is_healthy:
                proxy.failure_count = 0
                if proxy_id not in self.healthy_proxies:
                    self.healthy_proxies.append(proxy_id)
                healthy_count += 1
            else:
                proxy.failure_count += 1
                if proxy_id in self.healthy_proxies:
                    self.healthy_proxies.remove(proxy_id)
        
        logger.info(f"Health check complete: {healthy_count}/{len(self.proxies)} proxies healthy")
    
    async def _perform_health_check_async(self) -> None:
        """Perform asynchronous health check on all proxies"""
        logger.debug("Performing async health check...")
        
        tasks = []
        for proxy_id, proxy in self.proxies.items():
            task = asyncio.create_task(self._check_single_proxy(proxy_id, proxy))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_single_proxy(self, proxy_id: str, proxy: ProxyEndpoint) -> None:
        """Check health of a single proxy"""
        is_healthy, response_time = await self.health_checker.check_proxy_health(proxy)
        
        proxy.is_healthy = is_healthy
        proxy.response_time = response_time
        proxy.last_checked = datetime.now()
        
        if is_healthy:
            proxy.failure_count = 0
            if proxy_id not in self.healthy_proxies:
                self.healthy_proxies.append(proxy_id)
        else:
            proxy.failure_count += 1
            if proxy_id in self.healthy_proxies:
                self.healthy_proxies.remove(proxy_id)
    
    def _start_health_monitoring(self) -> None:
        """Start background health monitoring task"""
        if self._health_check_task is None or self._health_check_task.done():
            self._stop_health_check = False
            self._health_check_task = asyncio.create_task(self._health_monitor_loop())
    
    async def _health_monitor_loop(self) -> None:
        """Background health monitoring loop"""
        while not self._stop_health_check:
            try:
                await asyncio.sleep(self.health_check_interval)
                if not self._stop_health_check:
                    await self._perform_health_check_async()
            except Exception as e:
                logger.error(f"Health monitoring error: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def stop_health_monitoring(self) -> None:
        """Stop background health monitoring"""
        self._stop_health_check = True
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
    
    def refresh_proxy_list(self) -> bool:
        """
        Refresh proxy list from Webshare.io
        
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            logger.info("Refreshing proxy list from Webshare.io...")
            
            new_proxy_data = self.webshare_client.get_proxy_list(
                country=self.country_preference,
                limit=100
            )
            
            if not new_proxy_data:
                logger.warning("No new proxies received from Webshare.io")
                return False
            
            # Update existing proxies and add new ones
            new_proxy_ids = set()
            for proxy_info in new_proxy_data:
                endpoint = ProxyEndpoint(
                    host=proxy_info['proxy_address'],
                    port=proxy_info['port'],
                    username=proxy_info['username'],
                    password=proxy_info['password'],
                    country=proxy_info.get('country_code'),
                    city=proxy_info.get('city_name')
                )
                
                proxy_id = f"{endpoint.host}:{endpoint.port}"
                new_proxy_ids.add(proxy_id)
                
                if proxy_id not in self.proxies:
                    self.proxies[proxy_id] = endpoint
                    logger.info(f"Added new proxy: {endpoint.endpoint}")
            
            # Remove proxies that are no longer available
            removed_proxies = set(self.proxies.keys()) - new_proxy_ids
            for proxy_id in removed_proxies:
                del self.proxies[proxy_id]
                if proxy_id in self.healthy_proxies:
                    self.healthy_proxies.remove(proxy_id)
                logger.info(f"Removed proxy: {proxy_id}")
            
            # Perform health check on new/updated proxies
            self._perform_health_check_sync()
            
            self.stats['last_refresh'] = datetime.now()
            logger.info(f"Proxy list refreshed: {len(self.proxies)} total proxies")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh proxy list: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy manager statistics"""
        return {
            **self.stats,
            'total_proxies': len(self.proxies),
            'healthy_proxies': len(self.healthy_proxies),
            'current_proxy_index': self.current_proxy_index,
            'health_check_interval': self.health_check_interval
        }
    
    def get_proxy_info(self) -> List[ProxyInfo]:
        """Get information about all proxies"""
        proxy_list = []
        for proxy_id, proxy in self.proxies.items():
            proxy_info = ProxyInfo(
                proxy_id=proxy_id,
                endpoint=proxy.endpoint,
                country=proxy.country,
                city=proxy.city,
                is_healthy=proxy.is_healthy,
                failure_count=proxy.failure_count,
                last_used=proxy.last_used.isoformat() if proxy.last_used else None,
                response_time=proxy.response_time
            )
            proxy_list.append(proxy_info)
        
        return proxy_list
    
    def __del__(self):
        """Cleanup on destruction"""
        self.stop_health_monitoring()


# Global proxy manager instance
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> Optional[ProxyManager]:
    """Get global proxy manager instance"""
    return _proxy_manager


def initialize_proxy_manager(
    webshare_api_key: str,
    health_check_interval: int = 300,
    max_failures: int = 3,
    country_preference: Optional[str] = None
) -> bool:
    """
    Initialize global proxy manager
    
    Args:
        webshare_api_key: Webshare.io API key
        health_check_interval: Health check interval in seconds
        max_failures: Maximum failures before marking proxy unhealthy
        country_preference: Preferred country code
        
    Returns:
        True if initialization successful, False otherwise
    """
    global _proxy_manager
    
    try:
        _proxy_manager = ProxyManager(
            webshare_api_key=webshare_api_key,
            health_check_interval=health_check_interval,
            max_failures=max_failures,
            country_preference=country_preference
        )
        
        return _proxy_manager.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize proxy manager: {str(e)}")
        return False


def cleanup_proxy_manager() -> None:
    """Cleanup global proxy manager"""
    global _proxy_manager
    if _proxy_manager:
        _proxy_manager.stop_health_monitoring()
        _proxy_manager = None