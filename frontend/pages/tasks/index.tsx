import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../../lib/auth';
import { useProgressiveTasks } from '../../lib/useProgressiveTasks';
import { useNavigationAwareCache } from '../../lib/useNavigationAwareCache';
import { useOptimisticTaskOperations } from '../../lib/useOptimisticTaskOperations';
import api from '../../lib/api';
import Navbar from '../../components/Navbar';
import RecentTasksTable from '../../components/RecentTasksTable';
import { Plus, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

const TasksPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Initialize navigation-aware cache management
  useNavigationAwareCache();

  // Initialize optimistic task operations
  const {
    retryTaskOptimistically,
    cancelTaskOptimistically,
    deleteTaskOptimistically,
  } = useOptimisticTaskOperations();

  // Use progressive tasks hook with enhanced options for dedicated tasks page
  const {
    tasks,
    loadMore,
    hasMore,
    isLoading: tasksLoading,
    error: tasksError,
    showingAll,
    refresh,
    isRefreshing
  } = useProgressiveTasks({
    initialPerPage: 20, // Start with 20 tasks for the dedicated page
    autoRefresh: true,
    autoRefreshInterval: 15000, // 15 seconds
    enableCacheOptimization: true
  });

  const handleRefresh = () => {
    refresh();
  };

  const handleRetryTask = async (taskId: string) => {
    try {
      await retryTaskOptimistically(taskId);
      toast.success('Task retried successfully');
    } catch (error: any) {
      console.error('Retry task failed:', error);
      toast.error(error.message || 'Failed to retry task');
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await cancelTaskOptimistically(taskId);
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
      toast.success('Task deleted successfully');
    } catch (error: any) {
      console.error('Delete task failed:', error);
      toast.error(error.message || 'Failed to delete task');
    }
  };

  const handleDownloadResults = async (taskId: string, format: 'json' | 'csv' | 'xlsx') => {
    try {
      const data = await api.downloadTaskResult(taskId, format);
      
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

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                All Tasks
              </h1>
              <p className="text-gray-600 mt-1">
                View, monitor, and manage all your extraction tasks.
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
        {tasksError && (
          <div className="mb-8 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Error loading tasks
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>
                    {tasksError?.message || 'An unexpected error occurred'}
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

        {/* Tasks Table */}
        <div className="mb-8">
          <RecentTasksTable
            tasks={tasks}
            isLoading={tasksLoading}
            onRetry={handleRetryTask}
            onCancel={handleCancelTask}
            onDelete={handleDeleteTask}
            onDownload={handleDownloadResults}
            showViewAll={true}
            onLoadMore={loadMore}
            hasMore={hasMore}
            isLoadingMore={isRefreshing}
            showingAll={showingAll}
          />
        </div>
      </div>
    </div>
  );
};

export default TasksPage;