import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import Cookies from 'js-cookie';
import { User } from '../types/auth';
import {
  Task,
  TaskLog,
  ApiKey,
  Subscription,
  Usage,
  DashboardStats,
  CreateTaskRequest,
  UpdateTaskRequest,
  CreateApiKeyRequest,
  PaginatedResponse,
  ApiResponse,
  ApiError,
  TasksQueryParams,
  LogsQueryParams,
  UsageQueryParams,
  SubscriptionPlan,
  Invoice,
} from '../types/api';

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    this.client = axios.create({
      baseURL: `${this.baseURL}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = Cookies.get('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          Cookies.remove('access_token');
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        }
        return Promise.reject(this.formatError(error));
      }
    );
  }

  private formatError(error: any): ApiError {
    if (error.response) {
      const data = error.response.data;
      
      // Handle FastAPI validation errors (array of error objects directly in response.data)
      if (Array.isArray(data)) {
        const validationErrors = data.map((err: any) => {
          const location = err.loc ? err.loc.join('.') : 'field';
          return `${location}: ${err.msg || err.message || err.type || 'validation error'}`;
        }).join('; ');
        
        return {
          message: `Validation errors: ${validationErrors}`,
          status: error.response.status,
          code: 'VALIDATION_ERROR',
          details: data,
        };
      }
      
      // Handle other error formats
      return {
        message: data?.message || data?.detail || 'An error occurred',
        status: error.response.status,
        code: data?.code,
        details: data?.details,
      };
    } else if (error.request) {
      return {
        message: 'Network error. Please check your connection.',
        status: 0,
        code: 'NETWORK_ERROR',
      };
    } else {
      return {
        message: error.message || 'Unknown error occurred',
        status: 0,
        code: 'UNKNOWN_ERROR',
      };
    }
  }

  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.client.request<ApiResponse<T>>(config);
      if (response.data.data !== undefined) {
        return response.data.data;
      }
      return response.data as T;
    } catch (error) {
      throw error;
    }
  }

  // Authentication endpoints
  async getCurrentUser(): Promise<User> {
    return this.request<User>({
      method: 'GET',
      url: '/auth/me',
    });
  }

  async getGoogleAuthUrl(): Promise<{ auth_url: string; state: string }> {
    return this.request<{ auth_url: string; state: string }>({
      method: 'GET',
      url: '/auth/google',
    });
  }

  async googleAuth(code: string): Promise<{ access_token: string; user: User }> {
    return this.request<{ access_token: string; user: User }>({
      method: 'POST',
      url: '/auth/google',
      data: { code },
    });
  }

  async refreshToken(): Promise<{ access_token: string }> {
    return this.request<{ access_token: string }>({
      method: 'POST',
      url: '/auth/refresh',
    });
  }

  async logout(): Promise<void> {
    return this.request<void>({
      method: 'POST',
      url: '/auth/logout',
    });
  }

  // Task endpoints
  async getTasks(params?: TasksQueryParams): Promise<PaginatedResponse<Task>> {
    return this.request<PaginatedResponse<Task>>({
      method: 'GET',
      url: '/tasks',
      params,
    });
  }

  async getTask(taskId: string): Promise<Task> {
    return this.request<Task>({
      method: 'GET',
      url: `/tasks/${taskId}`,
    });
  }

  async createTask(data: CreateTaskRequest): Promise<Task> {
    return this.request<Task>({
      method: 'POST',
      url: '/tasks',
      data,
    });
  }

  async updateTask(taskId: string, data: UpdateTaskRequest): Promise<Task> {
    return this.request<Task>({
      method: 'PUT',
      url: `/tasks/${taskId}`,
      data,
    });
  }

  async deleteTask(taskId: string): Promise<void> {
    return this.request<void>({
      method: 'DELETE',
      url: `/tasks/${taskId}`,
    });
  }

  async cancelTask(taskId: string): Promise<Task> {
    return this.request<Task>({
      method: 'POST',
      url: `/tasks/${taskId}/cancel`,
    });
  }

  async retryTask(taskId: string): Promise<Task> {
    return this.request<Task>({
      method: 'POST',
      url: `/tasks/${taskId}/retry`,
    });
  }

  async downloadTaskResult(taskId: string, format: 'json' | 'csv' | 'xlsx'): Promise<Blob> {
    const response = await this.client.get(`/tasks/${taskId}/download`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  }

  // Task logs endpoints
  async getTaskLogs(taskId: string, params?: LogsQueryParams): Promise<PaginatedResponse<TaskLog>> {
    return this.request<PaginatedResponse<TaskLog>>({
      method: 'GET',
      url: `/tasks/${taskId}/logs`,
      params,
    });
  }

  // API Keys endpoints
  async getApiKeys(): Promise<ApiKey[]> {
    return this.request<ApiKey[]>({
      method: 'GET',
      url: '/api-keys',
    });
  }

  async createApiKey(data: CreateApiKeyRequest): Promise<ApiKey> {
    return this.request<ApiKey>({
      method: 'POST',
      url: '/api-keys',
      data,
    });
  }

  async deleteApiKey(keyId: string): Promise<void> {
    return this.request<void>({
      method: 'DELETE',
      url: `/api-keys/${keyId}`,
    });
  }

  async toggleApiKey(keyId: string): Promise<ApiKey> {
    return this.request<ApiKey>({
      method: 'POST',
      url: `/api-keys/${keyId}/toggle`,
    });
  }

  // Dashboard and analytics endpoints
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>({
      method: 'GET',
      url: '/analytics/dashboard',
    });
  }

  async getUsage(params?: UsageQueryParams): Promise<Usage[]> {
    return this.request<Usage[]>({
      method: 'GET',
      url: '/analytics/usage',
      params,
    });
  }

  // Subscription endpoints
  async getSubscription(): Promise<Subscription> {
    return this.request<Subscription>({
      method: 'GET',
      url: '/billing/subscription',
    });
  }

  async createCheckoutSession(tier: string): Promise<{ checkout_url: string }> {
    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
    return this.request<{ checkout_url: string }>({
      method: 'POST',
      url: '/billing/create-checkout',
      data: {
        plan_id: tier,
        success_url: `${baseUrl}/billing/success`,
        cancel_url: `${baseUrl}/billing/cancelled`
      },
    });
  }

  async createPortalSession(): Promise<{ portal_url: string }> {
    return this.request<{ portal_url: string }>({
      method: 'POST',
      url: '/billing/portal',
    });
  }

  async cancelSubscription(): Promise<Subscription> {
    return this.request<Subscription>({
      method: 'POST',
      url: '/billing/subscription/cancel',
    });
  }

  async updateSubscription(tier: string): Promise<Subscription> {
    return this.request<Subscription>({
      method: 'PUT',
      url: '/billing/subscription',
      data: { plan_id: tier },
    });
  }

  async getPlans(): Promise<SubscriptionPlan[]> {
    return this.request<SubscriptionPlan[]>({
      method: 'GET',
      url: '/billing/plans',
    });
  }

  async getInvoices(): Promise<Invoice[]> {
    return this.request<Invoice[]>({
      method: 'GET',
      url: '/billing/invoices',
    });
  }

  // Development
  // =======================================================================
  async devLogin(): Promise<{ access_token: string; user: User }> {
    return this.request<{ access_token: string; user: User }>({
        method: 'POST',
        url: '/auth/dev/login',
    });
  }

  async resumeSubscription(): Promise<{ message: string }> {
    return this.request<{ message: string }>({
      method: 'POST',
      url: '/billing/subscription/resume',
    });
  }

  // User profile endpoints
  async updateProfile(data: Partial<User>): Promise<User> {
    return this.request<User>({
      method: 'PUT',
      url: '/auth/me',
      data,
    });
  }

  async deleteAccount(): Promise<void> {
    return this.request<void>({
      method: 'DELETE',
      url: '/auth/account',
    });
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request<{ status: string; timestamp: string }>({
      method: 'GET',
      url: '/health',
    });
  }

  // Utility methods
  getDownloadUrl(taskId: string, format: 'json' | 'csv' | 'xlsx'): string {
    const token = Cookies.get('access_token');
    return `${this.baseURL}/api/v1/tasks/${taskId}/download?format=${format}&token=${token}`;
  }

  getImageUrl(path: string): string {
    return `${this.baseURL}${path}`;
  }
}

// Create singleton instance
export const api = new ApiClient();

// Export types for convenience
export type {
  User,
  Task,
  TaskLog,
  ApiKey,
  Subscription,
  Usage,
  DashboardStats,
  CreateTaskRequest,
  UpdateTaskRequest,
  CreateApiKeyRequest,
  PaginatedResponse,
  ApiResponse,
  ApiError,
  TasksQueryParams,
  LogsQueryParams,
  UsageQueryParams,
  SubscriptionPlan,
  Invoice,
};

export default api;