import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const authFailureRate = new Rate('auth_failures');
const taskCreationTime = new Trend('task_creation_duration');
const taskExecutionTime = new Trend('task_execution_duration');
const billingOperationTime = new Trend('billing_operation_duration');
const concurrentTasksCounter = new Counter('concurrent_tasks_created');

// Load testing configuration
export const options = {
  scenarios: {
    // Authentication load testing
    auth_load: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '2m', target: 20 },  // Ramp up to 20 users
        { duration: '5m', target: 20 },  // Stay at 20 users
        { duration: '2m', target: 50 },  // Ramp up to 50 users
        { duration: '5m', target: 50 },  // Stay at 50 users
        { duration: '2m', target: 0 },   // Ramp down
      ],
      exec: 'authScenario',
    },
    
    // API stress testing
    api_stress: {
      executor: 'ramping-vus',
      startVUs: 5,
      stages: [
        { duration: '3m', target: 30 },  // Ramp up to 30 users
        { duration: '10m', target: 30 }, // Stay at 30 users
        { duration: '3m', target: 100 }, // Stress test with 100 users
        { duration: '5m', target: 100 }, // Maintain stress
        { duration: '3m', target: 0 },   // Ramp down
      ],
      exec: 'apiStressScenario',
    },
    
    // Database intensive operations
    database_load: {
      executor: 'constant-vus',
      vus: 20,
      duration: '10m',
      exec: 'databaseScenario',
    },
    
    // Worker queue stress testing
    worker_stress: {
      executor: 'ramping-arrival-rate',
      startRate: 1,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { duration: '2m', target: 5 },   // Start with 5 tasks/sec
        { duration: '5m', target: 10 },  // Ramp to 10 tasks/sec
        { duration: '5m', target: 20 },  // Stress with 20 tasks/sec
        { duration: '3m', target: 5 },   // Ramp down to 5 tasks/sec
      ],
      exec: 'workerStressScenario',
    },
    
    // Billing system load
    billing_load: {
      executor: 'constant-vus',
      vus: 10,
      duration: '8m',
      exec: 'billingScenario',
    },
    
    // Memory leak testing (long-running)
    memory_leak_test: {
      executor: 'constant-vus',
      vus: 5,
      duration: '30m',
      exec: 'memoryLeakScenario',
    },
  },
  
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'], // 95% under 2s, 99% under 5s
    http_req_failed: ['rate<0.05'], // Error rate under 5%
    auth_failures: ['rate<0.01'], // Auth failure rate under 1%
    task_creation_duration: ['p(95)<3000'], // Task creation under 3s
    task_execution_duration: ['p(95)<30000'], // Task execution under 30s
    billing_operation_duration: ['p(95)<5000'], // Billing ops under 5s
  },
  
  // Load test environment configuration
  ext: {
    loadimpact: {
      distribution: {
        'amazon:us:ashburn': { loadZone: 'amazon:us:ashburn', percent: 50 },
        'amazon:eu:dublin': { loadZone: 'amazon:eu:dublin', percent: 50 },
      },
    },
  },
};

// Test configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_BASE_URL = `${BASE_URL}/api/v1`;
const FRONTEND_BASE_URL = __ENV.FRONTEND_URL || 'http://localhost:3000';

// Test data
const TEST_USERS = [
  { email: 'loadtest1@example.com', password: 'LoadTest123!' },
  { email: 'loadtest2@example.com', password: 'LoadTest123!' },
  { email: 'loadtest3@example.com', password: 'LoadTest123!' },
  { email: 'loadtest4@example.com', password: 'LoadTest123!' },
  { email: 'loadtest5@example.com', password: 'LoadTest123!' },
];

const SAMPLE_TASKS = [
  {
    name: 'E-commerce Product Scraping',
    url: 'https://example-shop.com/products',
    selectors: {
      title: '.product-title',
      price: '.price',
      availability: '.stock-status'
    },
    config: {
      wait_for_selector: true,
      take_screenshot: false,
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
  },
  {
    name: 'News Article Extraction',
    url: 'https://example-news.com/article/123',
    selectors: {
      headline: 'h1.article-title',
      content: '.article-body',
      author: '.author-name',
      publish_date: '.publish-date'
    },
    config: {
      wait_for_selector: true,
      take_screenshot: true,
      user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
  },
  {
    name: 'Real Estate Listings',
    url: 'https://example-realty.com/listings',
    selectors: {
      price: '.listing-price',
      address: '.listing-address',
      bedrooms: '.bed-count',
      bathrooms: '.bath-count',
      sqft: '.square-footage'
    },
    config: {
      wait_for_selector: true,
      take_screenshot: false,
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
  }
];

// Utility functions
function getRandomUser() {
  return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

function getRandomTask() {
  return SAMPLE_TASKS[Math.floor(Math.random() * SAMPLE_TASKS.length)];
}

function authenticateUser(user) {
  const loginResponse = http.post(`${API_BASE_URL}/auth/login`, JSON.stringify({
    email: user.email,
    password: user.password
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
  
  check(loginResponse, {
    'login successful': (r) => r.status === 200,
    'received access token': (r) => {
      const body = JSON.parse(r.body);
      return body.access_token !== undefined;
    },
  });
  
  if (loginResponse.status !== 200) {
    authFailureRate.add(1);
    return null;
  }
  
  authFailureRate.add(0);
  const tokens = JSON.parse(loginResponse.body);
  return tokens.access_token;
}

function getAuthHeaders(token) {
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

// Authentication load testing scenario
export function authScenario() {
  group('Authentication Load Test', () => {
    const user = getRandomUser();
    
    // Test registration (simulate new users)
    if (Math.random() < 0.1) { // 10% of requests are new registrations
      const registerResponse = http.post(`${API_BASE_URL}/auth/register`, JSON.stringify({
        email: `loadtest_${Date.now()}_${Math.random()}@example.com`,
        password: 'LoadTest123!',
        full_name: 'Load Test User'
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
      
      check(registerResponse, {
        'registration status': (r) => r.status === 201 || r.status === 409, // 409 if user exists
      });
    }
    
    // Test login
    const token = authenticateUser(user);
    
    if (token) {
      // Test token validation
      const profileResponse = http.get(`${API_BASE_URL}/auth/me`, {
        headers: getAuthHeaders(token),
      });
      
      check(profileResponse, {
        'profile fetch successful': (r) => r.status === 200,
        'profile contains user data': (r) => {
          const body = JSON.parse(r.body);
          return body.email === user.email;
        },
      });
      
      // Test logout
      const logoutResponse = http.post(`${API_BASE_URL}/auth/logout`, null, {
        headers: getAuthHeaders(token),
      });
      
      check(logoutResponse, {
        'logout successful': (r) => r.status === 200,
      });
    }
  });
  
  sleep(1);
}

// API stress testing scenario
export function apiStressScenario() {
  group('API Stress Test', () => {
    const user = getRandomUser();
    const token = authenticateUser(user);
    
    if (!token) return;
    
    const headers = getAuthHeaders(token);
    
    // Test task management endpoints
    group('Task Management', () => {
      // Create task
      const taskData = getRandomTask();
      const createStart = Date.now();
      
      const createResponse = http.post(`${API_BASE_URL}/tasks`, JSON.stringify(taskData), {
        headers: headers,
      });
      
      const createDuration = Date.now() - createStart;
      taskCreationTime.add(createDuration);
      
      check(createResponse, {
        'task created successfully': (r) => r.status === 201,
        'task has valid ID': (r) => {
          const body = JSON.parse(r.body);
          return body.id !== undefined;
        },
      });
      
      if (createResponse.status === 201) {
        const task = JSON.parse(createResponse.body);
        concurrentTasksCounter.add(1);
        
        // Get task details
        const getResponse = http.get(`${API_BASE_URL}/tasks/${task.id}`, {
          headers: headers,
        });
        
        check(getResponse, {
          'task details retrieved': (r) => r.status === 200,
          'task data matches': (r) => {
            const body = JSON.parse(r.body);
            return body.name === taskData.name;
          },
        });
        
        // List user tasks
        const listResponse = http.get(`${API_BASE_URL}/tasks`, {
          headers: headers,
        });
        
        check(listResponse, {
          'tasks list retrieved': (r) => r.status === 200,
          'tasks list contains data': (r) => {
            const body = JSON.parse(r.body);
            return Array.isArray(body.tasks);
          },
        });
        
        // Cancel task (simulate user behavior)
        if (Math.random() < 0.3) { // 30% chance to cancel
          const cancelResponse = http.post(`${API_BASE_URL}/tasks/${task.id}/cancel`, null, {
            headers: headers,
          });
          
          check(cancelResponse, {
            'task cancelled successfully': (r) => r.status === 200,
          });
        }
      }
    });
    
    // Test dashboard endpoints
    group('Dashboard Data', () => {
      const statsResponse = http.get(`${API_BASE_URL}/dashboard/stats`, {
        headers: headers,
      });
      
      check(statsResponse, {
        'dashboard stats retrieved': (r) => r.status === 200,
        'stats contain required fields': (r) => {
          const body = JSON.parse(r.body);
          return body.total_tasks !== undefined && body.compute_units_used !== undefined;
        },
      });
      
      const recentTasksResponse = http.get(`${API_BASE_URL}/dashboard/recent-tasks`, {
        headers: headers,
      });
      
      check(recentTasksResponse, {
        'recent tasks retrieved': (r) => r.status === 200,
      });
    });
  });
  
  sleep(Math.random() * 2 + 1); // Random sleep 1-3 seconds
}

// Database intensive scenario
export function databaseScenario() {
  group('Database Load Test', () => {
    const user = getRandomUser();
    const token = authenticateUser(user);
    
    if (!token) return;
    
    const headers = getAuthHeaders(token);
    
    // Perform database-intensive operations
    group('Complex Queries', () => {
      // Search tasks with filters
      const searchResponse = http.get(`${API_BASE_URL}/tasks?status=completed&limit=50&offset=0&sort=created_at&order=desc`, {
        headers: headers,
      });
      
      check(searchResponse, {
        'search query executed': (r) => r.status === 200,
      });
      
      // Get usage analytics (complex aggregation)
      const analyticsResponse = http.get(`${API_BASE_URL}/analytics/usage?period=30days`, {
        headers: headers,
      });
      
      check(analyticsResponse, {
        'analytics query executed': (r) => r.status === 200,
      });
      
      // Get billing history (joins multiple tables)
      const billingHistoryResponse = http.get(`${API_BASE_URL}/billing/history?limit=20`, {
        headers: headers,
      });
      
      check(billingHistoryResponse, {
        'billing history retrieved': (r) => r.status === 200,
      });
    });
  });
  
  sleep(0.5);
}

// Worker stress testing scenario
export function workerStressScenario() {
  group('Worker Stress Test', () => {
    const user = getRandomUser();
    const token = authenticateUser(user);
    
    if (!token) return;
    
    const headers = getAuthHeaders(token);
    const taskData = getRandomTask();
    
    // Create task for worker processing
    const createStart = Date.now();
    const createResponse = http.post(`${API_BASE_URL}/tasks`, JSON.stringify(taskData), {
      headers: headers,
    });
    
    const createDuration = Date.now() - createStart;
    taskCreationTime.add(createDuration);
    
    if (createResponse.status === 201) {
      const task = JSON.parse(createResponse.body);
      concurrentTasksCounter.add(1);
      
      // Poll for task completion (simulate real user behavior)
      let pollCount = 0;
      const maxPolls = 20; // Maximum 2 minutes of polling
      const executionStart = Date.now();
      
      while (pollCount < maxPolls) {
        sleep(6); // Poll every 6 seconds
        
        const statusResponse = http.get(`${API_BASE_URL}/tasks/${task.id}`, {
          headers: headers,
        });
        
        if (statusResponse.status === 200) {
          const taskStatus = JSON.parse(statusResponse.body);
          
          if (taskStatus.status === 'completed' || taskStatus.status === 'failed') {
            const executionDuration = Date.now() - executionStart;
            taskExecutionTime.add(executionDuration);
            break;
          }
        }
        
        pollCount++;
      }
      
      // Get task results if completed
      const resultsResponse = http.get(`${API_BASE_URL}/tasks/${task.id}/results`, {
        headers: headers,
      });
      
      check(resultsResponse, {
        'task results accessible': (r) => r.status === 200 || r.status === 404, // 404 if not completed
      });
    }
  });
}

// Billing system load testing
export function billingScenario() {
  group('Billing System Load Test', () => {
    const user = getRandomUser();
    const token = authenticateUser(user);
    
    if (!token) return;
    
    const headers = getAuthHeaders(token);
    
    group('Billing Operations', () => {
      // Get current usage
      const usageStart = Date.now();
      const usageResponse = http.get(`${API_BASE_URL}/billing/usage`, {
        headers: headers,
      });
      const usageeDuration = Date.now() - usageStart;
      billingOperationTime.add(usageeDuration);
      
      check(usageResponse, {
        'usage data retrieved': (r) => r.status === 200,
        'usage contains compute units': (r) => {
          const body = JSON.parse(r.body);
          return body.compute_units_used !== undefined;
        },
      });
      
      // Get available plans
      const plansResponse = http.get(`${API_BASE_URL}/billing/plans`, {
        headers: headers,
      });
      
      check(plansResponse, {
        'billing plans retrieved': (r) => r.status === 200,
      });
      
      // Get billing history
      const historyResponse = http.get(`${API_BASE_URL}/billing/history`, {
        headers: headers,
      });
      
      check(historyResponse, {
        'billing history retrieved': (r) => r.status === 200,
      });
      
      // Simulate plan change (only occasionally)
      if (Math.random() < 0.05) { // 5% chance
        const changeStart = Date.now();
        const changePlanResponse = http.post(`${API_BASE_URL}/billing/change-plan`, JSON.stringify({
          plan_id: 'starter'
        }), {
          headers: headers,
        });
        const changeDuration = Date.now() - changeStart;
        billingOperationTime.add(changeDuration);
        
        check(changePlanResponse, {
          'plan change processed': (r) => r.status === 200 || r.status === 409, // 409 if already on plan
        });
      }
    });
  });
  
  sleep(2);
}

// Memory leak testing scenario (long-running)
export function memoryLeakScenario() {
  group('Memory Leak Test', () => {
    const user = getRandomUser();
    const token = authenticateUser(user);
    
    if (!token) return;
    
    const headers = getAuthHeaders(token);
    
    // Perform repetitive operations that might cause memory leaks
    for (let i = 0; i < 10; i++) {
      // Create and immediately cancel tasks
      const taskData = getRandomTask();
      const createResponse = http.post(`${API_BASE_URL}/tasks`, JSON.stringify(taskData), {
        headers: headers,
      });
      
      if (createResponse.status === 201) {
        const task = JSON.parse(createResponse.body);
        
        // Cancel task immediately
        http.post(`${API_BASE_URL}/tasks/${task.id}/cancel`, null, {
          headers: headers,
        });
      }
      
      // Perform various API calls
      http.get(`${API_BASE_URL}/dashboard/stats`, { headers: headers });
      http.get(`${API_BASE_URL}/tasks`, { headers: headers });
      http.get(`${API_BASE_URL}/billing/usage`, { headers: headers });
      
      sleep(0.1);
    }
  });
  
  sleep(5);
}

// Setup and teardown functions
export function setup() {
  console.log('Starting Selextract Cloud load tests...');
  console.log(`Target: ${BASE_URL}`);
  console.log(`Frontend: ${FRONTEND_BASE_URL}`);
  
  // Health check
  const healthResponse = http.get(`${API_BASE_URL}/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`API health check failed: ${healthResponse.status}`);
  }
  
  console.log('Health check passed. Starting load tests...');
  return { baseUrl: BASE_URL };
}

export function teardown(data) {
  console.log('Load tests completed.');
  console.log('Check the results and metrics for performance analysis.');
}