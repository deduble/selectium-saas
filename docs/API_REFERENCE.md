# Selextract Cloud API Reference

This document provides comprehensive documentation for the Selextract Cloud REST API. The API enables programmatic access to web scraping and data extraction capabilities.

## Table of Contents

1. [Authentication](#authentication)
2. [Base URL and Versioning](#base-url-and-versioning)
3. [Request/Response Format](#requestresponse-format)
4. [Rate Limiting](#rate-limiting)
5. [Error Handling](#error-handling)
6. [Authentication Endpoints](#authentication-endpoints)
7. [Task Management Endpoints](#task-management-endpoints)
8. [API Key Management](#api-key-management)
9. [Billing and Subscription](#billing-and-subscription)
10. [Analytics and Usage](#analytics-and-usage)
11. [System and Health](#system-and-health)
12. [SDKs and Examples](#sdks-and-examples)

## Authentication

Selextract Cloud API supports multiple authentication methods:

### 1. JWT Bearer Token (OAuth Flow)
Used for web applications with user authentication via Google OAuth.

```http
Authorization: Bearer <jwt_token>
```

### 2. API Key Authentication
Used for server-to-server communication and programmatic access.

```http
Authorization: Bearer sk_test_1234567890abcdef...
```

### 3. Session-based Authentication
Used by the web frontend for dashboard access.

## Base URL and Versioning

- **Production:** `https://api.selextract.com`
- **API Version:** v1 (current)
- **Full Base URL:** `https://api.selextract.com/`

All endpoints are relative to the base URL.

## Request/Response Format

### Content Type
All requests should use `application/json` content type:

```http
Content-Type: application/json
```

### Response Format
All responses follow a consistent JSON structure:

```json
{
  "data": {...},
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_1234567890"
}
```

### Error Response Format
```json
{
  "error": "error_code",
  "message": "Human readable error message",
  "details": [
    {
      "field": "field_name",
      "message": "Field-specific error message"
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_1234567890"
}
```

## Rate Limiting

Rate limits are applied per user and API key:

- **Authentication endpoints:** 10 requests/minute
- **Task creation:** 30 requests/minute
- **General API:** 100 requests/minute
- **Billing operations:** 5 requests/minute

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995800
```

## Error Handling

### HTTP Status Codes

- `200` - Success
- `201` - Created successfully
- `400` - Bad request (validation error)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Resource not found
- `402` - Payment required (insufficient compute units)
- `429` - Rate limit exceeded
- `500` - Internal server error

### Common Error Codes

- `authentication_error` - Invalid or expired authentication
- `authorization_error` - Insufficient permissions
- `validation_error` - Request validation failed
- `rate_limit_exceeded` - Too many requests
- `insufficient_credits` - Not enough compute units
- `resource_not_found` - Requested resource doesn't exist
- `internal_server_error` - Server-side error

## Authentication Endpoints

### Get Google OAuth URL

Initiates Google OAuth flow for user authentication.

```http
GET /auth/google
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/oauth/authorize?...",
  "state": "random_state_token"
}
```

### Handle OAuth Callback

Exchanges OAuth code for JWT token. This endpoint is called by the frontend after Google redirects to `/auth/success`.

```http
POST /auth/google
```

**Request Body:**
```json
{
  "code": "oauth_authorization_code"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "subscription_tier": "free",
    "compute_units_remaining": 1000,
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Current User

Returns information about the authenticated user.

```http
GET /auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "user_uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "subscription_tier": "professional",
  "compute_units_used": 250,
  "compute_units_limit": 10000,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

### Update User Profile

Updates user profile information.

```http
PUT /auth/me
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "full_name": "John Smith",
  "avatar_url": "https://example.com/new-avatar.jpg"
}
```

### Logout

Invalidates the current session (client should discard token).

```http
POST /auth/logout
Authorization: Bearer <token>
```

## Task Management Endpoints

### List User Tasks

Retrieves tasks for the authenticated user with filtering and pagination.

```http
GET /tasks?page=1&page_size=20&sort_by=created_at&sort_order=desc
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 20, max: 100) - Items per page
- `sort_by` (string) - Field to sort by (`created_at`, `updated_at`, `name`, `status`)
- `sort_order` (string) - Sort direction (`asc`, `desc`)
- `status` (array) - Filter by status (`pending`, `running`, `completed`, `failed`, `cancelled`)
- `task_type` (array) - Filter by type (`simple_scraping`, `advanced_scraping`, `bulk_scraping`, `monitoring`)
- `created_after` (ISO datetime) - Tasks created after this date
- `created_before` (ISO datetime) - Tasks created before this date
- `name_contains` (string) - Filter by name containing text

**Response:**
```json
[
  {
    "id": "task_uuid",
    "name": "Extract product data",
    "description": "Scrape product information from e-commerce site",
    "task_type": "simple_scraping",
    "status": "completed",
    "config": {
      "urls": ["https://example.com/products"],
      "selectors": {
        "title": "h1.product-title",
        "price": ".price",
        "description": ".product-description"
      },
      "output_format": "json"
    },
    "priority": 5,
    "compute_units_consumed": 5,
    "estimated_compute_units": 5,
    "result_url": "/tasks/task_uuid/download",
    "error_message": null,
    "progress": 100,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "started_at": "2024-01-15T10:31:00Z",
    "completed_at": "2024-01-15T10:35:00Z",
    "user_id": "user_uuid"
  }
]
```

### Create Task

Creates a new scraping task.

```http
POST /tasks
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "Extract product data",
  "description": "Scrape product information from e-commerce site",
  "task_type": "simple_scraping",
  "priority": 5,
  "config": {
    "urls": ["https://example.com/products"],
    "selectors": {
      "title": "h1.product-title",
      "price": ".price",
      "description": ".product-description"
    },
    "output_format": "json",
    "include_metadata": true,
    "timeout": 30
  }
}
```

**Task Configuration by Type:**

#### Simple Scraping
```json
{
  "task_type": "simple_scraping",
  "config": {
    "urls": ["https://example.com/page1", "https://example.com/page2"],
    "selectors": {
      "title": "h1",
      "content": ".main-content",
      "price": ".price"
    },
    "output_format": "json",
    "include_metadata": true,
    "follow_redirects": true,
    "timeout": 30
  }
}
```

#### Advanced Scraping
```json
{
  "task_type": "advanced_scraping",
  "config": {
    "urls": ["https://spa-example.com"],
    "selectors": {
      "dynamic_content": ".ajax-loaded"
    },
    "javascript_enabled": true,
    "wait_for_selector": ".content-loaded",
    "custom_headers": {
      "User-Agent": "Custom Bot 1.0"
    },
    "cookies": {
      "session": "abc123"
    },
    "proxy_rotation": true,
    "rate_limit": 2
  }
}
```

#### Bulk Scraping
```json
{
  "task_type": "bulk_scraping",
  "config": {
    "urls": ["https://example.com/page1", "...100 more URLs"],
    "selectors": {
      "data": ".item"
    },
    "batch_size": 10,
    "parallel_requests": 3,
    "retry_attempts": 3,
    "export_individual_files": false
  }
}
```

#### Monitoring
```json
{
  "task_type": "monitoring",
  "config": {
    "urls": ["https://example.com/price-page"],
    "selectors": {
      "price": ".current-price"
    },
    "schedule": "daily",
    "notification_email": "alerts@company.com",
    "change_threshold": 0.05
  }
}
```

**Response:** Same as task object in list response.

### Get Task Details

Retrieves details for a specific task.

```http
GET /tasks/{task_id}
Authorization: Bearer <token>
```

**Response:** Same as task object structure.

### Update Task

Updates an existing task (only if not completed).

```http
PUT /tasks/{task_id}
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "Updated task name",
  "description": "Updated description",
  "priority": 8
}
```

### Delete/Cancel Task

Deletes or cancels a task.

```http
DELETE /tasks/{task_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Task deleted successfully"
}
```

### Get Task Logs

Retrieves execution logs for a task.

```http
GET /tasks/{task_id}/logs?page=1&page_size=50
Authorization: Bearer <token>
```

**Response:**
```json
{
  "task_id": "task_uuid",
  "logs": [
    {
      "id": "log_uuid",
      "task_id": "task_uuid",
      "level": "INFO",
      "message": "Starting task execution",
      "timestamp": "2024-01-15T10:31:00Z",
      "metadata": {
        "step": "initialization"
      }
    }
  ],
  "total_count": 25,
  "page": 1,
  "page_size": 50
}
```

### Download Task Results

Downloads the results file for a completed task.

```http
GET /tasks/{task_id}/download
Authorization: Bearer <token>
```

**Response:** File download (JSON, CSV, or XLSX based on task configuration)

## API Key Management

### List API Keys

Retrieves all API keys for the authenticated user.

```http
GET /api-keys
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": "key_uuid",
    "name": "Production API Key",
    "description": "Used for production scraping tasks",
    "key_preview": "sk_prod_12345678...",
    "permissions": ["tasks:read", "tasks:create"],
    "last_used_at": "2024-01-20T09:15:00Z",
    "created_at": "2024-01-15T10:30:00Z",
    "is_active": true
  }
]
```

### Create API Key

Creates a new API key.

```http
POST /api-keys
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "Production API Key",
  "description": "Used for production scraping tasks",
  "permissions": ["tasks:read", "tasks:create"]
}
```

**Response:**
```json
{
  "id": "key_uuid",
  "name": "Production API Key",
  "description": "Used for production scraping tasks",
  "key_preview": "sk_prod_12345678...",
  "permissions": ["tasks:read", "tasks:create"],
  "last_used_at": null,
  "created_at": "2024-01-15T10:30:00Z",
  "is_active": true,
  "api_key": "sk_prod_1234567890abcdef..."
}
```

**Note:** The full `api_key` is only returned once during creation.

### Delete API Key

Deactivates an API key.

```http
DELETE /api-keys/{key_id}
Authorization: Bearer <token>
```

## Billing and Subscription

### Get Subscription Details

Retrieves comprehensive subscription information for the user.

```http
GET /billing/subscription
Authorization: Bearer <token>
```

**Response:**
```json
{
  "subscription": {
    "id": "sub_uuid",
    "plan_id": "professional",
    "status": "active",
    "current_period_start": "2024-01-01T00:00:00Z",
    "current_period_end": "2024-02-01T00:00:00Z",
    "cancel_at_period_end": false
  },
  "plan": {
    "id": "professional",
    "name": "Professional",
    "price": 29.99,
    "currency": "USD",
    "compute_units_limit": 10000,
    "features": [
      "10,000 compute units/month",
      "Up to 5 concurrent tasks",
      "Advanced scraping features",
      "API access",
      "Email support"
    ]
  },
  "usage": {
    "compute_units_used": 2500,
    "compute_units_remaining": 7500,
    "compute_units_limit": 10000,
    "usage_percentage": 25.0
  },
  "billing": {
    "next_billing_date": "2024-02-01T00:00:00Z",
    "payment_method": "card_ending_4242"
  }
}
```

### Get Available Plans

Lists all available subscription plans.

```http
GET /billing/plans
```

**Response:**
```json
[
  {
    "id": "free",
    "name": "Free",
    "tier": "free",
    "price": 0.0,
    "currency": "USD",
    "compute_units_limit": 1000,
    "features": [
      "1,000 compute units/month",
      "Up to 2 concurrent tasks",
      "Basic scraping only",
      "Community support"
    ],
    "billing_interval": "monthly"
  },
  {
    "id": "professional",
    "name": "Professional",
    "tier": "pro",
    "price": 29.99,
    "currency": "USD",
    "compute_units_limit": 10000,
    "features": [
      "10,000 compute units/month",
      "Up to 5 concurrent tasks",
      "Advanced scraping features",
      "API access",
      "Email support"
    ],
    "billing_interval": "monthly"
  }
]
```

### Create Checkout Session

Creates a checkout session for subscription upgrade.

```http
POST /billing/create-checkout
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "plan_id": "professional",
  "success_url": "https://app.selextract.com/billing/success",
  "cancel_url": "https://app.selextract.com/billing/cancelled"
}
```

**Response:**
```json
{
  "checkout_url": "https://selextract.lemonsqueezy.com/checkout/...",
  "checkout_id": "checkout_uuid"
}
```

### Update Subscription

Changes the subscription plan.

```http
PUT /billing/subscription
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "plan_id": "enterprise"
}
```

### Cancel Subscription

Cancels the current subscription (remains active until period end).

```http
POST /billing/subscription/cancel
Authorization: Bearer <token>
```

### Resume Subscription

Resumes a cancelled subscription during the grace period.

```http
POST /billing/subscription/resume
Authorization: Bearer <token>
```

### Get Customer Portal

Returns URL for customer billing portal.

```http
POST /billing/portal
Authorization: Bearer <token>
```

**Response:**
```json
{
  "portal_url": "https://billing.lemonsqueezy.com/p/..."
}
```

### Get Invoices

Retrieves user's invoice history.

```http
GET /billing/invoices
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": "inv_uuid",
    "number": "INV-001",
    "amount": 29.99,
    "currency": "USD",
    "status": "paid",
    "created_at": "2024-01-01T00:00:00Z",
    "due_date": "2024-01-01T00:00:00Z",
    "paid_at": "2024-01-01T00:00:00Z",
    "download_url": "https://example.com/invoice.pdf"
  }
]
```

## Analytics and Usage

### Get Usage Analytics

Retrieves usage analytics for specified period.

```http
GET /analytics/usage?period=monthly&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <token>
```

**Query Parameters:**
- `period` (string) - `daily`, `weekly`, or `monthly`
- `start_date` (ISO date) - Start date for analytics
- `end_date` (ISO date) - End date for analytics

**Response:**
```json
{
  "period": "monthly",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "total_tasks": 150,
  "completed_tasks": 142,
  "failed_tasks": 8,
  "compute_units_consumed": 2500,
  "compute_units_limit": 10000,
  "top_task_types": [
    {
      "type": "simple_scraping",
      "count": 89
    },
    {
      "type": "advanced_scraping",
      "count": 45
    },
    {
      "type": "bulk_scraping",
      "count": 16
    }
  ]
}
```

### Get Dashboard Statistics

Retrieves current dashboard statistics.

```http
GET /analytics/dashboard
Authorization: Bearer <token>
```

**Response:**
```json
{
  "active_tasks": 3,
  "completed_tasks_today": 12,
  "compute_units_used_today": 45,
  "compute_units_remaining": 7500,
  "success_rate": 0.947,
  "recent_tasks": [
    {
      "id": "task_uuid",
      "name": "Recent task",
      "status": "completed",
      "created_at": "2024-01-20T15:30:00Z"
    }
  ]
}
```

## System and Health

### Health Check

Checks API health status.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-20T16:00:00Z",
  "database": "healthy",
  "redis": "healthy",
  "celery": "healthy"
}
```

### System Metrics (Admin Only)

Returns system-wide metrics for administrators.

```http
GET /admin/system-metrics
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "active_users": 1250,
  "total_tasks": 45000,
  "active_tasks": 23,
  "queue_length": 5,
  "timestamp": "2024-01-20T16:00:00Z"
}
```

## SDKs and Examples

### Python SDK Example

```python
import requests

class SelextractClient:
    def __init__(self, api_key, base_url="https://api.selextract.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def create_task(self, name, task_type, config, description=None):
        """Create a new scraping task."""
        data = {
            'name': name,
            'task_type': task_type,
            'config': config
        }
        if description:
            data['description'] = description
            
        response = self.session.post(f'{self.base_url}/tasks', json=data)
        response.raise_for_status()
        return response.json()
    
    def get_task(self, task_id):
        """Get task details."""
        response = self.session.get(f'{self.base_url}/tasks/{task_id}')
        response.raise_for_status()
        return response.json()
    
    def download_results(self, task_id, filename=None):
        """Download task results."""
        response = self.session.get(f'{self.base_url}/tasks/{task_id}/download')
        response.raise_for_status()
        
        if filename:
            with open(filename, 'wb') as f:
                f.write(response.content)
        return response.content

# Usage example
client = SelextractClient('sk_prod_your_api_key_here')

# Create a simple scraping task
task = client.create_task(
    name="Extract product prices",
    task_type="simple_scraping",
    config={
        "urls": ["https://example-store.com/products"],
        "selectors": {
            "title": ".product-title",
            "price": ".price",
            "rating": ".rating"
        },
        "output_format": "json"
    }
)

print(f"Task created: {task['id']}")

# Check task status
task_details = client.get_task(task['id'])
print(f"Status: {task_details['status']}")

# Download results when complete
if task_details['status'] == 'completed':
    results = client.download_results(task['id'], 'results.json')
    print("Results downloaded successfully")
```

### JavaScript/Node.js Example

```javascript
class SelextractClient {
    constructor(apiKey, baseUrl = 'https://api.selextract.com') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
    }

    async request(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }

        return response.json();
    }

    async createTask(name, taskType, config, description = null) {
        const data = { name, task_type: taskType, config };
        if (description) data.description = description;
        
        return this.request('POST', '/tasks', data);
    }

    async getTask(taskId) {
        return this.request('GET', `/tasks/${taskId}`);
    }

    async listTasks(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request('GET', `/tasks?${params}`);
    }
}

// Usage example
const client = new SelextractClient('sk_prod_your_api_key_here');

async function scrapeProducts() {
    try {
        // Create task
        const task = await client.createTask(
            'Extract product data',
            'simple_scraping',
            {
                urls: ['https://example-store.com/products'],
                selectors: {
                    title: '.product-title',
                    price: '.price',
                    rating: '.rating'
                },
                output_format: 'json'
            }
        );

        console.log(`Task created: ${task.id}`);

        // Poll for completion
        let taskDetails;
        do {
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
            taskDetails = await client.getTask(task.id);
            console.log(`Status: ${taskDetails.status}`);
        } while (['pending', 'running'].includes(taskDetails.status));

        if (taskDetails.status === 'completed') {
            console.log('Task completed successfully!');
            console.log(`Download URL: ${taskDetails.result_url}`);
        } else {
            console.error(`Task failed: ${taskDetails.error_message}`);
        }

    } catch (error) {
        console.error('Error:', error.message);
    }
}

scrapeProducts();
```

### cURL Examples

#### Create a simple scraping task:
```bash
curl -X POST https://api.selextract.com/tasks \
  -H "Authorization: Bearer sk_prod_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Extract product data",
    "task_type": "simple_scraping",
    "config": {
      "urls": ["https://example.com/products"],
      "selectors": {
        "title": "h1.product-title",
        "price": ".price"
      },
      "output_format": "json"
    }
  }'
```

#### Get task status:
```bash
curl https://api.selextract.com/tasks/task_uuid_here \
  -H "Authorization: Bearer sk_prod_your_api_key_here"
```

#### Download results:
```bash
curl https://api.selextract.com/tasks/task_uuid_here/download \
  -H "Authorization: Bearer sk_prod_your_api_key_here" \
  -o results.json
```

## Best Practices

1. **Always handle rate limits** - Implement exponential backoff for rate-limited requests
2. **Store API keys securely** - Never expose API keys in client-side code
3. **Use webhooks for long tasks** - Poll sparingly for task status updates
4. **Validate configurations** - Test selectors on small datasets first
5. **Monitor compute unit usage** - Track usage to avoid service interruptions
6. **Handle errors gracefully** - Implement proper error handling and retries
7. **Use appropriate task types** - Choose the right task type for your use case

## Support

- **Documentation:** [https://docs.selextract.com](https://docs.selextract.com)
- **API Status:** [https://status.selextract.com](https://status.selextract.com)
- **Support Email:** support@selextract.com
- **Community:** [https://community.selextract.com](https://community.selextract.com)

For technical support, include your request ID from error responses to help with debugging.