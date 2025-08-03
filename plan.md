Here is the final blueprint, which synthesizes the robust application logic from our previous plan with your new, pragmatic infrastructure strategy.

***

## Selextract Cloud: A Comprehensive SaaS Development Plan (Revision 4.0 - The Single-Server Implementation Blueprint)

### **Executive Summary**

This document presents the final, implementation-ready development plan for **Selextract Cloud**, revised to reflect a strategic shift to a **single dedicated server architecture**. This approach prioritizes cost-efficiency (€100/month target), operational control, and avoidance of vendor lock-in, while acknowledging the trade-offs in terms of operational overhead and initial scalability limits.

This blueprint details the complete project, from server setup and resource isolation using Docker Compose, to the integration of a proxy management system, to non-negotiable backup and monitoring procedures. It is the definitive guide for building a powerful, reliable, and cost-effective scraping service, designed with a clear path for future growth.

### **1. Finalized Single-Server Architecture**

All services will be co-located on a single dedicated server (e.g., 32 cores, 128GB RAM) and managed via Docker Compose to ensure strict resource isolation.

**Architecture Diagram:**

```
┌─────────────────────────────────────────────────────────┐
│                Dedicated Server (e.g., Hetzner)         │
│                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │    Nginx    │◀─▶│ FastAPI API  │◀─▶│ Web Dashboard │  │
│  │  (Reverse   │   │ (Backend)    │   │   (Next.js)   │  │
│  │   Proxy)    │   └──────┬───────┘   └──────────────┘  │
│  └─────────────┘          │                             │
│                           ▼                             │
│                  ┌────────────────┐                     │
│                  │ Redis (Celery) │                     │
│                  └────────┬───────┘                     │
│                           │                             │
│                           ▼                             │
│  ┌────────────────┐    ┌─────────────┐    ┌───────────┐ │
│  │ PostgreSQL DB  │    │ Playwright  │    │Monitoring │ │
│  └────────────────┘    │   Workers   │    │(Prometheus/│ │
│                        │ (Dockerized)│    │ Grafana)  │ │
│                        └─────────────┘    └───────────┘ │
└─────────────────────────────────────────────────────────┘
```

### **2. Core System Concepts (Unchanged)**

The fundamental application logic and business model remain consistent with previous revisions.

*   **The "Task" Schema (Version 1.0):** The JSONB object defining a scrape job remains the contract between all services.
*   **Consumption-Based Billing (Compute Units):** The model of `1 CU = 1 minute of run-time` is perfectly suited to this architecture.
*   **Schema Evolution:** The strategy for versioning task schemas to ensure backward compatibility will be maintained.

### **3. Phased Development Plan**

---

#### **Phase 1: Core Backend and Infrastructure Hardening (Weeks 1-4)**

**Objective:** Provision the server and deploy a secure, resilient, and production-ready backend.

1.  **Server Setup and Configuration:**
    *   Provision the dedicated server.
    *   Install Docker and Docker Compose.
    *   Configure the firewall (UFW), create non-root users, and set up SSH key-based authentication.
    *   Deploy Nginx as a reverse proxy to handle SSL/TLS termination and route traffic to the appropriate services.

2.  **Resource Isolation with Docker Compose:**
    *   Create a `docker-compose.yml` file to define all services with strict resource limits, preventing any single service from overwhelming the server.

    **File: `docker-compose.yml`**
    ```yaml
    version: '3.8'
    
    networks:
      selextract-network:
        driver: bridge
    
    volumes:
      postgres_data:
        driver: local
      redis_data:
        driver: local
      prometheus_data:
        driver: local
      grafana_data:
        driver: local
    
    services:
      postgres:
        image: postgres:15
        container_name: selextract-postgres
        environment:
          POSTGRES_DB: selextract
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
          POSTGRES_HOST_AUTH_METHOD: trust
        volumes:
          - postgres_data:/var/lib/postgresql/data
          - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
        ports:
          - "5432:5432"
        networks:
          - selextract-network
        deploy:
          resources:
            limits:
              cpus: '4'
              memory: '16G'
        restart: unless-stopped
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U postgres"]
          interval: 30s
          timeout: 10s
          retries: 3
    
      redis:
        image: redis:7-alpine
        container_name: selextract-redis
        command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
        volumes:
          - redis_data:/data
        ports:
          - "6379:6379"
        networks:
          - selextract-network
        deploy:
          resources:
            limits:
              cpus: '2'
              memory: '4G'
        restart: unless-stopped
        healthcheck:
          test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
          interval: 30s
          timeout: 10s
          retries: 3
    
      api:
        build:
          context: ./api
          dockerfile: Dockerfile
        container_name: selextract-api
        environment:
          DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/selextract
          REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
          JWT_SECRET_KEY: ${JWT_SECRET_KEY}
          GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
          GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
          WEBSHARE_API_KEY: ${WEBSHARE_API_KEY}
          LEMON_SQUEEZY_API_KEY: ${LEMON_SQUEEZY_API_KEY}
          ENVIRONMENT: production
        ports:
          - "8000:8000"
        depends_on:
          postgres:
            condition: service_healthy
          redis:
            condition: service_healthy
        networks:
          - selextract-network
        deploy:
          resources:
            limits:
              cpus: '4'
              memory: '8G'
        restart: unless-stopped
        volumes:
          - ./logs:/app/logs
          - ./results:/app/results
    
      worker:
        build:
          context: ./worker
          dockerfile: Dockerfile
        environment:
          DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/selextract
          REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
          WEBSHARE_API_KEY: ${WEBSHARE_API_KEY}
        depends_on:
          postgres:
            condition: service_healthy
          redis:
            condition: service_healthy
        networks:
          - selextract-network
        deploy:
          replicas: 4
          resources:
            limits:
              cpus: '2'
              memory: '4G'
        restart: unless-stopped
        volumes:
          - ./results:/app/results
          - ./logs:/app/logs
        shm_size: '2gb'  # Important for Playwright browsers
    
      nginx:
        image: nginx:alpine
        container_name: selextract-nginx
        ports:
          - "80:80"
          - "443:443"
        volumes:
          - ./nginx/nginx.conf:/etc/nginx/nginx.conf
          - ./nginx/sites-available:/etc/nginx/sites-available
          - ./ssl:/etc/nginx/ssl
        depends_on:
          - api
          - frontend
        networks:
          - selextract-network
        restart: unless-stopped
    
      frontend:
        build:
          context: ./frontend
          dockerfile: Dockerfile
        container_name: selextract-frontend
        environment:
          NEXT_PUBLIC_API_URL: https://api.selextract.com
          NEXTAUTH_URL: https://app.selextract.com
          NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
        ports:
          - "3000:3000"
        networks:
          - selextract-network
        deploy:
          resources:
            limits:
              cpus: '2'
              memory: '4G'
        restart: unless-stopped
    
      prometheus:
        image: prom/prometheus:latest
        container_name: selextract-prometheus
        command:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus'
          - '--web.console.libraries=/etc/prometheus/console_libraries'
          - '--web.console.templates=/etc/prometheus/consoles'
          - '--storage.tsdb.retention.time=200h'
          - '--web.enable-lifecycle'
        volumes:
          - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
          - prometheus_data:/prometheus
        ports:
          - "9090:9090"
        networks:
          - selextract-network
        deploy:
          resources:
            limits:
              cpus: '1'
              memory: '2G'
        restart: unless-stopped
    
      grafana:
        image: grafana/grafana:latest
        container_name: selextract-grafana
        environment:
          GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
          GF_USERS_ALLOW_SIGN_UP: 'false'
        volumes:
          - grafana_data:/var/lib/grafana
          - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
          - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
        ports:
          - "3001:3000"
        networks:
          - selextract-network
        deploy:
          resources:
            limits:
              cpus: '1'
              memory: '2G'
        restart: unless-stopped
    ```

3.  **Backup and Disaster Recovery Strategy:**
    *   Implement a non-negotiable daily backup routine. This script will be executed via a cron job.

    **File: `/etc/cron.daily/backup.sh`**
    ```bash
    #!/bin/bash
    # Stop services for a consistent DB snapshot
    cd /path/to/selextract && docker-compose stop
    
    # Backup PostgreSQL database
    docker exec -t selextract-postgres-1 pg_dumpall -c -U postgres | gzip > /backups/db_$(date +%Y%m%d).sql.gz
    
    # Copy backup to secure, off-site storage (e.g., Backblaze B2)
    /usr/local/bin/b2 upload-file your-b2-bucket-name /backups/db_$(date +%Y%m%d).sql.gz db_$(date +%Y%m%d).sql.gz
    
    # Restart services
    cd /path/to/selextract && docker-compose start
    
    # Prune local backups older than 7 days
    find /backups -name "*.sql.gz" -mtime +7 -delete
    ```

4.  **Proxy Integration (Webshare.io):**
    *   Develop the `ProxyManager` class as a core utility for workers to rotate IPs and bypass anti-bot measures.

    **File: `worker/proxies.py`**
    ```python
    import requests
    import random
    import os
    import logging
    from datetime import datetime, timedelta
    from typing import Dict, List, Optional, Any
    import asyncio
    from dataclasses import dataclass

    @dataclass
    class ProxyInfo:
        """Data class to represent a proxy configuration"""
        host: str
        port: int
        username: str
        password: str
        country_code: str
        valid: bool = True
        last_used: Optional[datetime] = None
        failure_count: int = 0

        def to_playwright_format(self) -> Dict[str, Any]:
            """Convert to Playwright proxy format"""
            return {
                "server": f"http://{self.host}:{self.port}",
                "username": self.username,
                "password": self.password
            }

        def to_requests_format(self) -> Dict[str, str]:
            """Convert to requests library format"""
            proxy_url = f"http://{self.username}:{self.password}@{self.host}:{self.port}"
            return {
                "http": proxy_url,
                "https": proxy_url
            }

    class ProxyManager:
        """
        Manages proxy rotation and health checking for Webshare.io proxies
        """
        
        def __init__(self):
            self.api_key = os.environ.get("WEBSHARE_API_KEY")
            if not self.api_key:
                raise ValueError("WEBSHARE_API_KEY environment variable is required")
            
            self.proxies: List[ProxyInfo] = []
            self.last_refresh = None
            self.refresh_interval = timedelta(minutes=30)
            self.base_url = "https://proxy.webshare.io/api/v2"
            self.logger = logging.getLogger(__name__)
            
            # Configuration
            self.max_failure_count = 3
            self.health_check_url = "http://httpbin.org/ip"
            self.health_check_timeout = 10

        async def refresh_proxies(self) -> bool:
            """
            Fetch fresh proxy list from Webshare.io API
            Returns True if successful, False otherwise
            """
            if (self.last_refresh and
                datetime.now() - self.last_refresh < self.refresh_interval and
                self.proxies):
                return True

            try:
                headers = {"Authorization": f"Token {self.api_key}"}
                
                # Get proxy list from Webshare API
                response = requests.get(
                    f"{self.base_url}/proxy/list/",
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                
                proxy_data = response.json()
                new_proxies = []
                
                for proxy in proxy_data.get("results", []):
                    proxy_info = ProxyInfo(
                        host=proxy["proxy_address"],
                        port=proxy["port"],
                        username=proxy["username"],
                        password=proxy["password"],
                        country_code=proxy.get("country_code", "Unknown")
                    )
                    new_proxies.append(proxy_info)
                
                if new_proxies:
                    self.proxies = new_proxies
                    self.last_refresh = datetime.now()
                    self.logger.info(f"Successfully refreshed {len(new_proxies)} proxies")
                    return True
                else:
                    self.logger.warning("No proxies received from API")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Failed to refresh proxies: {str(e)}")
                return False

        async def get_proxy(self, preferred_country: Optional[str] = None) -> Optional[ProxyInfo]:
            """
            Get a random working proxy, optionally filtered by country
            """
            # Refresh proxies if needed
            if not await self.refresh_proxies():
                self.logger.error("Could not refresh proxy list")
                return None

            # Filter valid proxies
            valid_proxies = [p for p in self.proxies if p.valid and p.failure_count < self.max_failure_count]
            
            if not valid_proxies:
                self.logger.warning("No valid proxies available")
                return None

            # Filter by country if specified
            if preferred_country:
                country_proxies = [p for p in valid_proxies if p.country_code.lower() == preferred_country.lower()]
                if country_proxies:
                    valid_proxies = country_proxies

            # Select random proxy, preferring least recently used
            valid_proxies.sort(key=lambda x: x.last_used or datetime.min)
            selected_proxy = random.choice(valid_proxies[:len(valid_proxies)//2 + 1])
            
            selected_proxy.last_used = datetime.now()
            return selected_proxy

        async def test_proxy(self, proxy: ProxyInfo) -> bool:
            """
            Test if a proxy is working by making a simple HTTP request
            """
            try:
                proxy_dict = proxy.to_requests_format()
                response = requests.get(
                    self.health_check_url,
                    proxies=proxy_dict,
                    timeout=self.health_check_timeout
                )
                
                if response.status_code == 200:
                    proxy.failure_count = 0
                    proxy.valid = True
                    return True
                else:
                    raise Exception(f"HTTP {response.status_code}")
                    
            except Exception as e:
                proxy.failure_count += 1
                if proxy.failure_count >= self.max_failure_count:
                    proxy.valid = False
                    self.logger.warning(f"Proxy {proxy.host}:{proxy.port} marked as invalid after {proxy.failure_count} failures")
                return False

        async def mark_proxy_failed(self, proxy: ProxyInfo, error: str = "") -> None:
            """
            Mark a proxy as failed and potentially remove it from rotation
            """
            proxy.failure_count += 1
            self.logger.warning(f"Proxy {proxy.host}:{proxy.port} failed: {error} (failure count: {proxy.failure_count})")
            
            if proxy.failure_count >= self.max_failure_count:
                proxy.valid = False
                self.logger.error(f"Proxy {proxy.host}:{proxy.port} disabled due to excessive failures")

        async def get_proxy_stats(self) -> Dict[str, Any]:
            """
            Get statistics about current proxy pool
            """
            if not self.proxies:
                return {"total": 0, "valid": 0, "invalid": 0, "countries": []}

            valid_count = sum(1 for p in self.proxies if p.valid and p.failure_count < self.max_failure_count)
            invalid_count = len(self.proxies) - valid_count
            countries = list(set(p.country_code for p in self.proxies if p.valid))

            return {
                "total": len(self.proxies),
                "valid": valid_count,
                "invalid": invalid_count,
                "countries": sorted(countries),
                "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None
            }

        async def health_check_all_proxies(self) -> None:
            """
            Test all proxies in the pool to update their health status
            """
            if not self.proxies:
                await self.refresh_proxies()

            self.logger.info(f"Starting health check for {len(self.proxies)} proxies")
            
            # Test proxies concurrently (but limit concurrency)
            semaphore = asyncio.Semaphore(10)  # Max 10 concurrent tests
            
            async def test_with_semaphore(proxy):
                async with semaphore:
                    return await self.test_proxy(proxy)
            
            tasks = [test_with_semaphore(proxy) for proxy in self.proxies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            healthy_count = sum(1 for result in results if result is True)
            self.logger.info(f"Health check completed: {healthy_count}/{len(self.proxies)} proxies healthy")

    # Usage example for workers
    proxy_manager = ProxyManager()
    ```

    **File: `worker/requirements.txt`**
    ```txt
    requests>=2.31.0
    aiohttp>=3.8.0
    playwright>=1.40.0
    celery[redis]>=5.3.0
    sqlalchemy>=2.0.0
    asyncpg>=0.29.0
    pydantic>=2.0.0
    python-dotenv>=1.0.0
    structlog>=23.0.0
    ```

---

#### **Phase 2: Worker Implementation & Monitoring (Weeks 5-7)**

**Objective:** Deploy the scraping workers and establish comprehensive system monitoring.

1.  **Worker Task Execution Logic:**
    *   Implement the core Playwright scraping logic within the Dockerized worker.
    *   Integrate the `ProxyManager`: Before launching Playwright, the worker will call `proxy_manager.get_proxy()` and configure the browser to use it.
    *   Implement the robust error handling and retry policies defined in Revision 3.0.

2.  **Monitoring and Alerting Setup:**
    *   Deploy the monitoring stack using a separate Docker Compose file.
    *   Configure Prometheus to scrape metrics from the API and workers (using an appropriate exporter).
    *   Build a Grafana dashboard to visualize critical system health metrics:
        *   **System-level:** CPU Usage, Memory Usage (per container), Disk I/O.
        *   **Application-level:** API Latency, Task Success/Failure Rate, Celery Queue Depth.
    *   Set up Alertmanager to send notifications for critical events (e.g., high memory usage, low task success rate).

---

### **Phase 3: Web Dashboard, System Optimization, and Public Launch**

**Objective:** To build the complete user-facing web application, conduct final system-wide testing and optimization, and officially launch the Selextract Cloud service to the public. The Chrome Extension remains untouched during this phase.

#### **3.1. Web Dashboard Development (Next.js)**

This is the primary user interface for the cloud service. It will be a feature-rich, standalone web application.

1.  **Project Initialization:**
    *   Initialize a new Next.js project using TypeScript: `npx create-next-app@latest --ts`.
    *   Establish the project structure: `/pages`, `/components`, `/lib` (for API clients and helpers), `/styles`.
    *   Integrate a UI component library (e.g., Mantine, Chakra UI, or Tailwind CSS with Headless UI) to accelerate development and ensure a consistent design.

2.  **Authentication Flow Implementation:**
    *   Create a `[...nextauth]` route or a custom authentication context to manage user sessions.
    *   The "Login" button will redirect the user to the backend API's OAuth endpoint: `https://api.selextract.com/auth/google`.
    *   The backend will handle the Google OAuth flow and, upon success, redirect back to a dedicated callback URL on the web dashboard: `https://app.selextract.com/auth/callback`.
    *   The backend will set a secure, HTTP-only cookie containing the user's JWT, which the browser will automatically include in all subsequent requests to the API domain.
    *   The frontend will manage the user's state (logged in/out) based on the presence and validity of this session.

3.  **Dashboard Main Page (`/dashboard`):**
    *   This is the user's command center after logging in.
    *   **Key Metrics Display:** Prominently display essential information fetched from the API (`GET /auth/me`):
        *   Remaining Compute Units (CUs).
        *   Current Subscription Tier.
        *   Number of active and queued tasks.
    *   **Recent Tasks Table:** Display a table of the user's 10 most recent tasks.
        *   **Columns:** Task Name, Status (color-coded: `Pending`, `Running`, `Completed`, `Failed`), Creation Date, CUs Consumed.
        *   Each task row will be a link to its dedicated Task Details page.

4.  **Task Details Page (`/tasks/[taskId]`):**
    *   **Task Configuration View:** Display all settings from the `task.config` JSON object in a clean, readable format. This provides a clear record of what was executed.
    *   **Execution Metadata:** Show timestamps for `created_at`, `started_at`, and `completed_at`. Display the final `compute_units_consumed`.
    *   **Result Preview & Download:**
        *   If the task was successful, fetch and display a preview of the first 10-20 rows of the result data.
        *   Provide a prominent "Download Results (JSON)" button that links to the authenticated backend endpoint (`GET /results/[resultId]/download`).
    *   **Error Display:** If the task failed, display the specific error message from the `tasks.error` field to help the user debug their configuration.

5.  **Subscription & Billing Page (`/billing`):**
    *   **Current Plan:** Clearly display the user's active subscription tier and its associated limits (e.g., concurrent task limit).
    *   **Usage Information:** Show the current CU balance and the date it will be refilled.
    *   **Manage Billing Button:** This is a critical implementation detail. We will **not** build our own UI for handling credit cards. This button will link the user *directly* to their secure **Lemon Squeezy Customer Portal**, where they can update payment methods, cancel subscriptions, or view invoices. This greatly reduces our security and compliance burden.


#### **Phase 4: Load Testing, Optimization, and Launch (Weeks 11-12)**

**Objective:** Stress-test the system on its target hardware and prepare for a production launch.

1.  **Load Testing:**
    *   Perform rigorous load testing to understand the server's limits. Determine the maximum number of concurrent Playwright workers the server can handle before performance degrades (`oom-kills`, high CPU steal).
    *   Use this data to set a safe default for the number of worker replicas (`services.worker.scale`).

2.  **Security Hardening & Final Audit:**
    *   Ensure Nginx is correctly configured with strong SSL/TLS ciphers.
    *   Verify all firewall rules are in place.
    *   Conduct a final review of all application code for potential security vulnerabilities.
    *   **Test the backup restore procedure** at least once to ensure it works.


### **Phase 4: Chrome Extension Cloud Integration** 

**Objective:** To update the existing, local-only Chrome Extension to function as a powerful client for the now-live Selextract Cloud platform, providing a seamless bridge from visual selection to cloud execution.
#### WARNING! THIS WILL REQUIRE WORKSPACE CHANGE, STOP IMPLEMENTATION IMMEDIATELY IF YOU ARE NOT IN CHROME EXTENSION WORKSPACE

1.  **Authentication and State Management:**
    *   Add a "Login" or "Connect to Cloud" button within the extension's UI.
    *   Clicking this button will programmatically open a new browser tab to the API's authentication URL: `https://api.selextract.com/auth/google`.
    *   Upon successful login, the backend will redirect to a special, static success page (e.g., `https://app.selextract.com/extension-auth-success`).
    *   This page will contain a small script that retrieves the JWT from its secure cookie and sends it to the extension's background script using `chrome.runtime.sendMessage`.
    *   The extension's background script will securely store the received JWT in `chrome.storage.local`.

2.  **UI/UX Redesign for Cloud Functionality:**
    *   Introduce a new "Run Destination" toggle or tab in the extension UI, with options for "Local" and "Cloud".
    *   When "Cloud" is selected, the UI will dynamically show additional input fields required for the cloud service, which are not present in the local version:
        *   **Task Name:** A simple text input.
        *   **Scheduling Options:** A toggle to enable scheduling and a validated input for a `cron` string.
        *   **Advanced Pagination:** More detailed controls for `maxPages`, etc.

3.  **Task Serialization and Submission Logic:**
    *   Enhance the existing `taskSerializer.js` module. It will now read the "Run Destination" state.
    *   If the destination is "Cloud", it will read all the additional UI fields and build a JSON object that strictly conforms to the `task.config` schema (Version 1.0).
    *   Create a new `apiClient.js` module within the extension's codebase. This client will be responsible for:
        *   Reading the JWT from `chrome.storage.local`.
        *   Attaching the JWT as an `Authorization: Bearer <token>` header to all outgoing requests.
        *   Making the `POST /tasks` request to the backend API with the serialized task data.

4.  **Cloud Task Monitoring within the Extension:**
    *   Add a new "Cloud History" panel to the extension UI.
    *   This panel will periodically (e.g., every 30 seconds while open) call the `GET /tasks` endpoint using the `apiClient`.
    *   It will display a concise list of the user's most recent cloud tasks and their real-time statuses, providing immediate feedback without requiring the user to leave their current page to check the web dashboard.

### **Phase X. Future Scaling Strategy (Post-Launch)**

This single-server architecture is designed to be the first step in a larger journey. When the server's resources are consistently maxed out, follow this pragmatic scaling path:

1.  **Decouple the Database:** Migrate the PostgreSQL database to its own dedicated database server to eliminate I/O and CPU contention between the application and the database.
2.  **Add Dedicated Worker Nodes:** Provision new, smaller servers whose only job is to run the Playwright worker containers. The main server's Celery instance will distribute tasks to this new fleet of workers.
3.  **Implement a Load Balancer:** As API traffic grows, place a dedicated load balancer (e.g., HAProxy) in front of one or more application servers running the FastAPI code.
4.  **Adopt Shared Storage:** Implement a network storage solution like NFS or a self-hosted S3-compatible service like MinIO, so that all workers and the API server can access result files from a central location.