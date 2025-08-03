import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useQueryClient } from 'react-query';
import { useAuth } from '../../lib/auth';
import api from '../../lib/api';
import Navbar from '../../components/Navbar';
import TaskStatus from '../../components/TaskStatus';
import ConfigurationEditor from '../../components/ConfigurationEditor';
import { Task, TaskLog, PaginatedResponse, ApiError, TaskConfig } from '../../types/api';
import {
  ArrowLeft,
  RefreshCw,
  Play,
  Square,
  Trash2,
  Download,
  Clock,
  Globe,
  Settings,
  FileText,
  AlertCircle,
  Eye,
  ChevronDown,
  ChevronUp,
  ExternalLink
} from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

const TaskDetailsPage: React.FC = () => {
  const router = useRouter();
  const { taskId } = router.query;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [refreshKey, setRefreshKey] = useState(0);
  const [showLogs, setShowLogs] = useState(false);
  const [isUpdatingConfig, setIsUpdatingConfig] = useState(false);

  // Authentication guard
  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch task details
  const {
    data: task,
    isLoading: taskLoading,
    error: taskError,
    refetch: refetchTask,
  } = useQuery<Task, ApiError>(
    ['task', taskId, refreshKey],
    () => api.getTask(taskId as string),
    {
      enabled: isAuthenticated && !!taskId,
      refetchOnWindowFocus: true,
    }
  );

  // Set up conditional refetch interval based on task status
  React.useEffect(() => {
    if (!task) return;

    const shouldRefetch = task.status === 'running' || task.status === 'pending';
    if (!shouldRefetch) return;

    const interval = setInterval(() => {
      refetchTask();
    }, 5000);

    return () => clearInterval(interval);
  }, [task?.status, refetchTask]);

  // Fetch task logs
  const {
    data: logsResponse,
    isLoading: logsLoading,
    refetch: refetchLogs,
  } = useQuery<PaginatedResponse<TaskLog>, ApiError>(
    ['task-logs', taskId, refreshKey],
    () => api.getTaskLogs(taskId as string, { per_page: 50, page: 1 }),
    {
      enabled: isAuthenticated && !!taskId && showLogs,
    }
  );

  // Set up conditional refetch interval for logs based on task status
  React.useEffect(() => {
    if (!task || !showLogs) return;

    const shouldRefetch = task.status === 'running' || task.status === 'pending';
    if (!shouldRefetch) return;

    const interval = setInterval(() => {
      refetchLogs();
    }, 3000);

    return () => clearInterval(interval);
  }, [task?.status, showLogs, refetchLogs]);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
    toast.success('Task refreshed');
  };

  const handleRetry = async () => {
    if (!task) return;
    
    try {
      await api.retryTask(task.id);
      setRefreshKey(prev => prev + 1);
      toast.success('Task retried successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to retry task');
    }
  };

  const handleCancel = async () => {
    if (!task) return;
    
    try {
      await api.cancelTask(task.id);
      setRefreshKey(prev => prev + 1);
      toast.success('Task cancelled successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to cancel task');
    }
  };

  const handleDelete = async () => {
    if (!task) return;
    
    if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
      return;
    }

    try {
      await api.deleteTask(task.id);
      toast.success('Task deleted successfully');
      router.push('/tasks');
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete task');
    }
  };

  const handleDownload = async (format: 'json' | 'csv' | 'xlsx') => {
    if (!task) return;
    
    try {
      const data = await api.downloadTaskResult(task.id, format);
      
      const blob = new Blob([data], {
        type: format === 'json' ? 'application/json' :
             format === 'csv' ? 'text/csv' :
             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${task.name}-results.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Results downloaded as ${format.toUpperCase()}`);
    } catch (error: any) {
      toast.error(error.message || 'Failed to download results');
    }
  };

  const handleConfigurationSave = async (config: TaskConfig) => {
    if (!task) return;
    
    setIsUpdatingConfig(true);
    try {
      const updatedTask = await api.updateTask(task.id, {
        config: config
      });
      
      // Update the local cache
      queryClient.setQueryData(['task', taskId], updatedTask);
      
      // Refresh the task data
      setRefreshKey(prev => prev + 1);
      
      toast.success('Configuration updated successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to update configuration');
      throw error; // Re-throw for component error handling
    } finally {
      setIsUpdatingConfig(false);
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return 'Invalid Date';
    }
  };

  const getLogLevelColor = (level: TaskLog['level']) => {
    switch (level) {
      case 'error':
        return 'text-red-600 bg-red-50';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50';
      case 'info':
        return 'text-blue-600 bg-blue-50';
      case 'debug':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-600 bg-gray-50';
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

  if (taskLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-8"></div>
            <div className="bg-white shadow rounded-lg p-6">
              <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
              <div className="space-y-3">
                <div className="h-4 bg-gray-200 rounded"></div>
                <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                <div className="h-4 bg-gray-200 rounded w-4/6"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (taskError) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-red-50 border border-red-200 rounded-md p-6">
            <div className="flex">
              <AlertCircle className="w-5 h-5 text-red-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Error loading task</h3>
                <p className="mt-2 text-sm text-red-700">{taskError.message}</p>
                <div className="mt-4">
                  <Link
                    href="/tasks"
                    className="text-sm bg-red-100 text-red-800 rounded-md px-3 py-1.5 font-medium hover:bg-red-200"
                  >
                    Back to Tasks
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!task) {
    return null;
  }

  const canRetry = task.status === 'failed' || task.status === 'cancelled';
  const canCancel = task.status === 'pending' || task.status === 'running';
  const hasResults = task.status === 'completed' && task.result;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <Link
              href="/tasks"
              className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back to Tasks
            </Link>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{task.name}</h1>
                {task.description && (
                  <p className="text-gray-600 mt-1">{task.description}</p>
                )}
              </div>
              <TaskStatus status={task.status} />
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleRefresh}
                disabled={taskLoading}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${taskLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              
              {canRetry && (
                <button
                  onClick={handleRetry}
                  className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Retry
                </button>
              )}
              
              {canCancel && (
                <button
                  onClick={handleCancel}
                  className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-yellow-600 hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                >
                  <Square className="w-4 h-4 mr-2" />
                  Cancel
                </button>
              )}
              
              <button
                onClick={handleDelete}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Task Details */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Task Details</h2>
              
              <dl className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-gray-500">URL</dt>
                  <dd className="mt-1 text-sm text-gray-900 break-all">
                    {task.config.urls && task.config.urls.length > 0 ? (
                      <div className="space-y-2">
                        <div>
                          <a
                            href={task.config.urls[0]}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:text-primary-700 inline-flex items-center"
                          >
                            <Globe className="w-4 h-4 mr-1" />
                            {task.config.urls[0]}
                            <ExternalLink className="w-3 h-3 ml-1" />
                          </a>
                          {task.config.urls.length > 1 && (
                            <span className="ml-2 text-xs text-gray-500">
                              (+ {task.config.urls.length - 1} more)
                            </span>
                          )}
                        </div>
                        {task.config.urls.slice(1).map((url, index) => (
                          <div key={index + 1}>
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary-600 hover:text-primary-700 inline-flex items-center"
                            >
                              <Globe className="w-4 h-4 mr-1" />
                              {url}
                              <ExternalLink className="w-3 h-3 ml-1" />
                            </a>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-400 italic">No URL specified</span>
                    )}
                  </dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Priority</dt>
                  <dd className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      task.priority === 'high' ? 'bg-red-100 text-red-800' :
                      task.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {task.priority}
                    </span>
                  </dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="mt-1 text-sm text-gray-900 flex items-center">
                    <Clock className="w-4 h-4 mr-1" />
                    {formatDate(task.created_at)}
                  </dd>
                </div>
                
                {task.started_at && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Started</dt>
                    <dd className="mt-1 text-sm text-gray-900 flex items-center">
                      <Clock className="w-4 h-4 mr-1" />
                      {formatDate(task.started_at)}
                    </dd>
                  </div>
                )}
                
                {task.completed_at && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Completed</dt>
                    <dd className="mt-1 text-sm text-gray-900 flex items-center">
                      <Clock className="w-4 h-4 mr-1" />
                      {formatDate(task.completed_at)}
                    </dd>
                  </div>
                )}
                
                {task.scheduled_at && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Scheduled</dt>
                    <dd className="mt-1 text-sm text-gray-900 flex items-center">
                      <Clock className="w-4 h-4 mr-1" />
                      {formatDate(task.scheduled_at)}
                    </dd>
                  </div>
                )}
              </dl>
              
              {task.error_message && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                  <div className="flex">
                    <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
                    <div>
                      <h4 className="text-sm font-medium text-red-800">Error</h4>
                      <p className="mt-1 text-sm text-red-700">{task.error_message}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Configuration */}
            <ConfigurationEditor
              task={task}
              onSave={handleConfigurationSave}
              isLoading={isUpdatingConfig}
              readOnly={task.status === 'completed' || task.status === 'failed'}
            />

            {/* Results */}
            {hasResults && (
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-medium text-gray-900 flex items-center">
                    <FileText className="w-5 h-5 mr-2" />
                    Results
                  </h2>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleDownload('json')}
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                    >
                      <Download className="w-3 h-3 mr-1" />
                      JSON
                    </button>
                    <button
                      onClick={() => handleDownload('csv')}
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                    >
                      <Download className="w-3 h-3 mr-1" />
                      CSV
                    </button>
                    <button
                      onClick={() => handleDownload('xlsx')}
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                    >
                      <Download className="w-3 h-3 mr-1" />
                      Excel
                    </button>
                    <Link
                      href={`/tasks/${task.id}/results`}
                      className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-primary-600 hover:bg-primary-700"
                    >
                      <Eye className="w-3 h-3 mr-1" />
                      View Details
                    </Link>
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded-md p-3 max-h-96 overflow-auto">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                    {JSON.stringify(task.result, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
              
              <div className="space-y-3">
                {hasResults && (
                  <Link
                    href={`/tasks/${task.id}/results`}
                    className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    View Results
                  </Link>
                )}
                
                {canRetry && (
                  <button
                    onClick={handleRetry}
                    className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Retry Task
                  </button>
                )}
                
                <Link
                  href="/tasks/create"
                  className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Duplicate Task
                </Link>
              </div>
            </div>

            {/* Logs */}
            <div className="bg-white shadow rounded-lg p-6">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className="flex items-center justify-between w-full text-left mb-4"
              >
                <h3 className="text-lg font-medium text-gray-900">Logs</h3>
                {showLogs ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
              </button>
              
              {showLogs && (
                <div className="space-y-2 max-h-96 overflow-auto">
                  {logsLoading ? (
                    <div className="animate-pulse space-y-2">
                      {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-4 bg-gray-200 rounded"></div>
                      ))}
                    </div>
                  ) : logsResponse && logsResponse.items.length > 0 ? (
                    logsResponse.items.map((log) => (
                      <div
                        key={log.id}
                        className={`p-2 rounded text-xs ${getLogLevelColor(log.level)}`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium uppercase">{log.level}</span>
                          <span className="text-xs opacity-75">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p>{log.message}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">No logs available</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskDetailsPage;