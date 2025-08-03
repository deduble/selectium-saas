// Artillery.io Custom Processor for Selextract Cloud Load Testing
// Provides custom functions and hooks for advanced testing scenarios

'use strict';

const fs = require('fs');
const path = require('path');

// Custom functions for test scenarios
module.exports = {
  // Setup function called before tests start
  beforeRequest: beforeRequest,
  afterResponse: afterResponse,
  
  // Custom functions for conditional flows
  maybeCancel: maybeCancel,
  maybePlanChange: maybePlanChange,
  
  // Utility functions
  generateRandomTask: generateRandomTask,
  validateResponse: validateResponse,
  
  // Hooks for metrics collection
  logMetrics: logMetrics
};

/**
 * Pre-request hook to modify requests
 */
function beforeRequest(requestParams, context, ee, next) {
  // Add correlation ID for request tracing
  if (!requestParams.headers) {
    requestParams.headers = {};
  }
  
  requestParams.headers['X-Correlation-ID'] = `artillery-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  // Add user agent for API requests
  if (requestParams.url && requestParams.url.includes('/api/')) {
    requestParams.headers['User-Agent'] = 'Artillery-LoadTest/1.0 (Selextract-Cloud-Testing)';
  }
  
  // Log request for debugging in development
  if (process.env.ARTILLERY_DEBUG) {
    console.log(`[DEBUG] Request: ${requestParams.method || 'GET'} ${requestParams.url}`);
  }
  
  return next();
}

/**
 * Post-response hook to collect metrics and validate responses
 */
function afterResponse(requestParams, response, context, ee, next) {
  // Record response time metrics
  const responseTime = response.timings ? response.timings.response : 0;
  
  // Emit custom metrics
  ee.emit('histogram', 'custom.response_time', responseTime);
  
  // Check for authentication errors
  if (response.statusCode === 401) {
    ee.emit('counter', 'custom.auth_errors', 1);
  }
  
  // Check for server errors
  if (response.statusCode >= 500) {
    ee.emit('counter', 'custom.server_errors', 1);
    console.error(`[ERROR] Server error ${response.statusCode} for ${requestParams.url}`);
  }
  
  // Check for rate limiting
  if (response.statusCode === 429) {
    ee.emit('counter', 'custom.rate_limited', 1);
    console.warn(`[WARN] Rate limited for ${requestParams.url}`);
  }
  
  // Validate API response structure for critical endpoints
  if (requestParams.url && requestParams.url.includes('/api/v1/')) {
    validateApiResponse(response, requestParams.url, ee);
  }
  
  // Store successful task IDs for later use
  if (response.statusCode === 201 && requestParams.url && requestParams.url.includes('/tasks')) {
    try {
      const body = JSON.parse(response.body);
      if (body.id) {
        if (!context.vars.created_tasks) {
          context.vars.created_tasks = [];
        }
        context.vars.created_tasks.push(body.id);
      }
    } catch (e) {
      // Ignore parsing errors
    }
  }
  
  return next();
}

/**
 * Conditional function to maybe cancel a task (30% probability)
 */
function maybeCancel(context, events, done) {
  const shouldCancel = Math.random() < 0.3; // 30% chance
  context.vars.shouldCancel = shouldCancel;
  
  if (shouldCancel) {
    events.emit('counter', 'custom.tasks_cancelled', 1);
  }
  
  return done();
}

/**
 * Conditional function to maybe change plan (5% probability)
 */
function maybePlanChange(context, events, done) {
  const shouldChange = Math.random() < 0.05; // 5% chance
  context.vars.shouldChangePlan = shouldChange;
  
  if (shouldChange) {
    // Select random plan
    const plans = ['starter', 'professional', 'enterprise'];
    context.vars.newPlan = plans[Math.floor(Math.random() * plans.length)];
    events.emit('counter', 'custom.plan_changes_attempted', 1);
  }
  
  return done();
}

/**
 * Generate random task data for testing
 */
function generateRandomTask(context, events, done) {
  const taskTemplates = [
    {
      name: 'E-commerce Product Scraping',
      url: 'https://example-shop.com/products',
      selectors: {
        title: '.product-title, h1.title, .product-name',
        price: '.price, .cost, .amount, .product-price',
        availability: '.stock-status, .availability, .in-stock'
      }
    },
    {
      name: 'News Article Extraction',
      url: 'https://example-news.com/latest',
      selectors: {
        headline: 'h1.article-title, .headline, .news-title',
        content: '.article-body, .content, .news-content',
        author: '.author-name, .byline, .author',
        publish_date: '.publish-date, .date, .timestamp'
      }
    },
    {
      name: 'Real Estate Listings',
      url: 'https://example-realty.com/search',
      selectors: {
        price: '.listing-price, .price',
        address: '.listing-address, .address',
        bedrooms: '.bed-count, .bedrooms',
        bathrooms: '.bath-count, .bathrooms',
        sqft: '.square-footage, .sqft'
      }
    },
    {
      name: 'Job Postings Scraper',
      url: 'https://example-jobs.com/listings',
      selectors: {
        job_title: '.job-title, h2.title',
        company: '.company-name, .employer',
        location: '.job-location, .location',
        salary: '.salary-range, .pay',
        description: '.job-description, .details'
      }
    },
    {
      name: 'Social Media Posts',
      url: 'https://example-social.com/feed',
      selectors: {
        post_content: '.post-content, .tweet-text, .post-body',
        author: '.author, .username, .poster',
        likes: '.like-count, .likes, .reactions',
        shares: '.share-count, .retweets, .shares',
        timestamp: '.post-time, .timestamp, .date'
      }
    }
  ];
  
  const template = taskTemplates[Math.floor(Math.random() * taskTemplates.length)];
  
  // Add some randomization to the task
  const randomId = Math.random().toString(36).substr(2, 8);
  context.vars.randomTask = {
    ...template,
    name: `${template.name} (Load Test ${randomId})`,
    config: {
      wait_for_selector: Math.random() > 0.5,
      take_screenshot: Math.random() > 0.7, // 30% chance for screenshots
      user_agent: getRandomUserAgent(),
      timeout: Math.floor(Math.random() * 20000) + 10000 // 10-30 seconds
    }
  };
  
  events.emit('counter', 'custom.random_tasks_generated', 1);
  return done();
}

/**
 * Validate API response structure
 */
function validateApiResponse(response, url, events) {
  if (response.statusCode >= 200 && response.statusCode < 300) {
    try {
      const body = JSON.parse(response.body);
      
      // Validate authentication responses
      if (url.includes('/auth/login')) {
        if (!body.access_token || !body.token_type) {
          events.emit('counter', 'custom.invalid_auth_response', 1);
        }
      }
      
      // Validate task responses
      if (url.includes('/tasks') && !url.includes('/tasks/')) {
        if (response.statusCode === 201) {
          if (!body.id || !body.status) {
            events.emit('counter', 'custom.invalid_task_response', 1);
          }
        }
      }
      
      // Validate dashboard responses
      if (url.includes('/dashboard/stats')) {
        if (typeof body.total_tasks === 'undefined' || typeof body.compute_units_used === 'undefined') {
          events.emit('counter', 'custom.invalid_dashboard_response', 1);
        }
      }
      
      // Validate billing responses
      if (url.includes('/billing/usage')) {
        if (typeof body.compute_units_used === 'undefined' || typeof body.compute_units_limit === 'undefined') {
          events.emit('counter', 'custom.invalid_billing_response', 1);
        }
      }
      
    } catch (parseError) {
      events.emit('counter', 'custom.json_parse_errors', 1);
    }
  }
}

/**
 * Validate response helper function
 */
function validateResponse(context, events, done) {
  const response = context.vars.$response;
  
  if (response && response.body) {
    try {
      const body = JSON.parse(response.body);
      context.vars.responseValid = true;
      context.vars.parsedResponse = body;
    } catch (e) {
      context.vars.responseValid = false;
      events.emit('counter', 'custom.response_validation_failed', 1);
    }
  } else {
    context.vars.responseValid = false;
  }
  
  return done();
}

/**
 * Log custom metrics for performance analysis
 */
function logMetrics(context, events, done) {
  const metrics = {
    timestamp: new Date().toISOString(),
    user_id: context.vars.user_id || 'anonymous',
    session_id: context.vars.session_id || 'unknown',
    created_tasks: context.vars.created_tasks ? context.vars.created_tasks.length : 0,
    cancelled_tasks: context.vars.cancelled_tasks || 0
  };
  
  // Log to file for analysis (in development/testing)
  if (process.env.ARTILLERY_LOG_METRICS) {
    const logFile = path.join(__dirname, 'artillery-metrics.jsonl');
    fs.appendFileSync(logFile, JSON.stringify(metrics) + '\n');
  }
  
  events.emit('counter', 'custom.metrics_logged', 1);
  return done();
}

/**
 * Get random user agent for diversity
 */
function getRandomUserAgent() {
  const userAgents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
  ];
  
  return userAgents[Math.floor(Math.random() * userAgents.length)];
}

/**
 * Cleanup function called after tests complete
 */
function cleanup(context, events, done) {
  // Perform any necessary cleanup
  if (context.vars.created_tasks && context.vars.created_tasks.length > 0) {
    console.log(`[INFO] Test session created ${context.vars.created_tasks.length} tasks`);
  }
  
  return done();
}

// Export cleanup function
module.exports.cleanup = cleanup;