import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useQueryClient } from 'react-query';
import { useAuth } from '../lib/auth';
import { useNavigationAwareCache } from '../lib/useNavigationAwareCache';
import { useOptimisticTaskOperations } from '../lib/useOptimisticTaskOperations';
import api from '../lib/api';
import Navbar from '../components/Navbar';
import DashboardStats from '../components/DashboardStats';
import RecentTasksTable from '../components/RecentTasksTable';
import { DashboardStats as DashboardStatsType, Task, PaginatedResponse, ApiError } from '../types/api';
import { Plus, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

const DashboardPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const queryClient = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Initialize navigation-aware cache management
  const { invalidateDashboardCache } = useNavigationAwareCache();

  // Initialize optimistic task operations
  const {
    retryTaskOptimistically,
    cancelTaskOptimistically,
    deleteTaskOptimistically,
  } = useOptimisticTaskOperations();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch dashboard stats
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useQuery<DashboardStatsType, ApiError>(
    ['dashboard', 'stats'],
    () => api.getDashboardStats(),
    {
      enabled: isAuthenticated,
      refetchInterval: 30000, // Refresh every 30 seconds
      refetchOnWindowFocus: true,
      staleTime: 5000, // Consider data stale after 5 seconds
      cacheTime: 300000, // Keep in cache for 5 minutes
    }
  );

  // Fetch recent tasks
  const {
    data: tasksResponse,
    isLoading: tasksLoading,
    error: tasksError,
    refetch: refetchTasks,
  } = useQuery<PaginatedResponse<Task>, ApiError>(
    ['dashboard', 'recent-tasks'],
    () => api.getTasks({ per_page: 10, page: 1, status: undefined }),
    {
      enabled: isAuthenticated,
      refetchInterval: 30000, // Refresh every 30 seconds
      refetchOnWindowFocus: true,
      staleTime: 5000, // Consider data stale after 5 seconds
      cacheTime: 300000, // Keep in cache for 5 minutes
      onSuccess: (data) => {
        // Update individual task caches for optimistic updates
        if (data?.items) {
          data.items.forEach(task => {
            queryClient.setQueryData(['task', task.id], task);
          });
        }
      }
    }
  );

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Invalidate all dashboard-related caches
      invalidateDashboardCache();
      
      // Refetch both stats and tasks
      await Promise.all([refetchStats(), refetchTasks()]);
      
      toast.success('Dashboard refreshed');
    } catch (error) {
      console.error('Dashboard refresh failed:', error);
      toast.error('Failed to refresh dashboard');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRetryTask = async (taskId: string) => {
    try {
      await retryTaskOptimistically(taskId);
      // Refresh dashboard stats after task operation
      refetchStats();
      toast.success('Task retried successfully');
    } catch (error: any) {
      console.error('Retry task failed:', error);
      toast.error(error.message || 'Failed to retry task');
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await cancelTaskOptimistically(taskId);
      // Refresh dashboard stats after task operation
      refetchStats();
      toast.success('Task cancelled successfully');
    } catch (error: any) {
      console.error('Cancel task failed:', error);
      toast.error(error.message || 'Failed to cancel task');
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteTaskOptimistically(taskId, () => api.deleteTask(taskId));
      // Refresh dashboard stats after task operation
      refetchStats();
      toast.success('Task deleted successfully');
    } catch (error: any) {
      console.error('Delete task failed:', error);
      toast.error(error.message || 'Failed to delete task');
    }
  };

  const handleDownloadResults = async (taskId: string, format: 'json' | 'csv' | 'xlsx') => {
    try {
      const data = await api.downloadTaskResult(taskId, format);
      
      // Create blob and download
      const blob = new Blob([data], {
        type: format === 'json' ? 'application/json' : 
             format === 'csv' ? 'text/csv' : 
             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `task-${taskId}-results.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Results downloaded as ${format.toUpperCase()}`);
    } catch (error: any) {
      toast.error(error.message || 'Failed to download results');
    }
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  const hasErrors = statsError || tasksError;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Welcome back, {user?.full_name || 'User'}!
              </h1>
              <p className="text-gray-600 mt-1">
                Here's what's happening with your data extraction tasks
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                {isRefreshing ? 'Refreshing...' : 'Refresh'}
              </button>
              
              <Link
                href="/tasks/create"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Task
              </Link>
            </div>
          </div>
        </div>

        {/* Error State */}
        {hasErrors && (
          <div className="mb-8 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Error loading dashboard data
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>
                    {statsError?.message || tasksError?.message || 'An unexpected error occurred'}
                  </p>
                </div>
                <div className="mt-4">
                  <button
                    onClick={handleRefresh}
                    className="text-sm bg-red-100 text-red-800 rounded-md px-3 py-1.5 font-medium hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                  >
                    Try again
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Dashboard Stats */}
        <div className="mb-8">
          <DashboardStats 
            stats={stats || {
              total_tasks: 0,
              completed_tasks: 0,
              failed_tasks: 0,
              pending_tasks: 0,
              api_calls_used: 0,
              api_calls_limit: 0,
              success_rate: 0,
              avg_execution_time: 0,
            }}
            isLoading={statsLoading}
          />
        </div>

        {/* Recent Tasks */}
        <div className="mb-8">
          <RecentTasksTable
            tasks={tasksResponse?.items || []}
            isLoading={tasksLoading}
            onRetry={handleRetryTask}
            onCancel={handleCancelTask}
            onDelete={handleDeleteTask}
            onDownload={handleDownloadResults}
            showViewAll={true}
          />
        </div>

        {/* Quick Actions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Link
            href="/tasks/create"
            className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-primary-500 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
          >
            <div>
              <span className="rounded-lg inline-flex p-3 bg-primary-50 text-primary-600 ring-4 ring-white">
                <Plus className="w-6 h-6" />
              </span>
            </div>
            <div className="mt-8">
              <h3 className="text-lg font-medium text-gray-900">
                Create New Task
              </h3>
              <p className="mt-2 text-sm text-gray-500">
                Set up a new data extraction task with custom selectors and configuration.
              </p>
            </div>
            <span className="absolute top-6 right-6 text-gray-300 group-hover:text-gray-400">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
            </span>
          </Link>

          <Link
            href="/tasks"
            className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-primary-500 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
          >
            <div>
              <span className="rounded-lg inline-flex p-3 bg-blue-50 text-blue-600 ring-4 ring-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </span>
            </div>
            <div className="mt-8">
              <h3 className="text-lg font-medium text-gray-900">
                Manage Tasks
              </h3>
              <p className="mt-2 text-sm text-gray-500">
                View, monitor, and manage all your extraction tasks in one place.
              </p>
            </div>
            <span className="absolute top-6 right-6 text-gray-300 group-hover:text-gray-400">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
            </span>
          </Link>

          <Link
            href="/api-keys"
            className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-primary-500 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
          >
            <div>
              <span className="rounded-lg inline-flex p-3 bg-green-50 text-green-600 ring-4 ring-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
              </span>
            </div>
            <div className="mt-8">
              <h3 className="text-lg font-medium text-gray-900">
                API Keys
              </h3>
              <p className="mt-2 text-sm text-gray-500">
                Generate and manage API keys for programmatic access to Selextract.
              </p>
            </div>
            <span className="absolute top-6 right-6 text-gray-300 group-hover:text-gray-400">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;