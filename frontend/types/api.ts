export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string;
  google_id?: string;
  subscription_tier: 'free' | 'basic' | 'pro' | 'enterprise';
  subscription_status?: 'active' | 'cancelled' | 'past_due' | 'trialing';
  compute_units_remaining: number;
  compute_units_limit?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskConfig {
  urls: string[];
  selectors: Record<string, string>;
  output_format: 'json' | 'csv' | 'xlsx';
  include_metadata: boolean;
  follow_redirects: boolean;
  timeout: number; // in seconds, 5-300
}

export interface Task {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  task_type: 'simple_scraping' | 'advanced_scraping' | 'bulk_scraping' | 'monitoring';
  config: TaskConfig;
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  priority: number | 'high' | 'medium' | 'low';
  compute_units_consumed: number;
  estimated_compute_units: number;
  result_file_path?: string;
  error_message?: string;
  progress: number;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  result?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface TaskLog {
  id: string;
  task_id: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ApiKey {
  id: string;
  user_id: string;
  name: string;
  key?: string;  // Full API key (only available in creation response)
  api_key?: string;  // Backend field name for the full key
  key_preview?: string;  // Preview of the key (for list views)
  description?: string;
  permissions?: string[];
  is_active: boolean;
  last_used_at?: string;
  created_at: string;
  expires_at?: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  tier: 'free' | 'basic' | 'pro' | 'enterprise';
  status: 'active' | 'cancelled' | 'past_due' | 'trialing';
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  days_until_renewal?: number;
  created_at: string;
  updated_at: string;
}

export interface Usage {
  period: string;
  api_calls: number;
  successful_tasks: number;
  failed_tasks: number;
  total_execution_time: number;
}

export interface DashboardStats {
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  pending_tasks: number;
  api_calls_used: number;
  api_calls_limit: number;
  success_rate: number;
  avg_execution_time: number;
}

export interface CreateTaskRequest {
  name: string;
  description?: string;
  task_type: Task['task_type'];
  config: TaskConfig;
  priority?: number;
  scheduled_at?: string;
}

export interface UpdateTaskRequest {
  name?: string;
  description?: string;
  priority?: number;
  scheduled_at?: string;
  config?: TaskConfig;
}

export interface CreateApiKeyRequest {
  name: string;
  description?: string;
  expires_at?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  error?: string;
  success: boolean;
}

export interface ApiError {
  message: string;
  code?: string;
  status: number;
  details?: Record<string, any>;
}

// Query parameters for API requests
export interface TasksQueryParams {
  page?: number;
  per_page?: number;
  status?: Task['status'];
  priority?: Task['priority'];
  search?: string;
  sort_by?: 'created_at' | 'updated_at' | 'name' | 'status';
  sort_order?: 'asc' | 'desc';
}

export interface LogsQueryParams {
  page?: number;
  per_page?: number;
  level?: TaskLog['level'];
  since?: string;
  until?: string;
}

export interface UsageQueryParams {
  start_date?: string;
  end_date?: string;
  granularity?: 'day' | 'week' | 'month';
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  tier: string;
  price: number;
  currency: string;
  compute_units_limit: number;
  features: string[];
  billing_interval: string;
  popular?: boolean;
}

export interface Invoice {
  id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  receipt_url?: string;
  invoice_url?: string;
}