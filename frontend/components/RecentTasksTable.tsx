import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { formatDistanceToNow } from 'date-fns';
import {
  MoreVertical,
  Play,
  Pause,
  RotateCcw,
  Download,
  Trash2,
  ExternalLink,
  Eye,
  Copy
} from 'lucide-react';
import { Task } from '../types/api';
import TaskStatus from './TaskStatus';
import SmartDropdown from './SmartDropdown';

interface RecentTasksTableProps {
  tasks: Task[];
  isLoading?: boolean;
  onRetry?: (taskId: string) => void;
  onCancel?: (taskId: string) => void;
  onDelete?: (taskId: string) => void;
  onDownload?: (taskId: string, format: 'json' | 'csv' | 'xlsx') => void;
  showViewAll?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  showingAll?: boolean;
}

interface TaskActionsMenuProps {
  task: Task;
  onRetry?: (taskId: string) => void;
  onCancel?: (taskId: string) => void;
  onDelete?: (taskId: string) => void;
  onDownload?: (taskId: string, format: 'json' | 'csv' | 'xlsx') => void;
}

interface ClickableTableRowProps {
  task: Task;
  onRowClick: (taskId: string) => void;
  children: React.ReactNode;
}

const ClickableTableRow: React.FC<ClickableTableRowProps> = ({ task, onRowClick, children }) => {
  const handleRowClick = (e: React.MouseEvent) => {
    // Prevent navigation if clicking on interactive elements
    if ((e.target as HTMLElement).closest('button, a, [role="button"]')) {
      return;
    }
    onRowClick(task.id);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onRowClick(task.id);
    }
  };

  return (
    <tr
      onClick={handleRowClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      className="hover:bg-gray-50 cursor-pointer focus:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset transition-colors duration-150"
      role="button"
      aria-label={`View details for task ${task.name}`}
    >
      {children}
    </tr>
  );
};

const TaskActionsMenu: React.FC<TaskActionsMenuProps> = ({
  task,
  onRetry,
  onCancel,
  onDelete,
  onDownload,
}) => {
  const canRetry = task.status === 'failed' || task.status === 'cancelled';
  const canCancel = task.status === 'pending' || task.status === 'running';
  const canDownload = task.status === 'completed' && task.result_file_path;

  const trigger = (
    <div className="p-1 rounded-full hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
      <MoreVertical className="w-4 h-4 text-gray-500" />
    </div>
  );

  return (
    <SmartDropdown
      trigger={trigger}
      placement="auto"
      className="w-48"
    >
      <div className="py-1">
        <Link
          href={`/tasks/${task.id}`}
          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
        >
          <Eye className="w-4 h-4 mr-3" />
          View Details
        </Link>
        
        <button
          onClick={() => navigator.clipboard.writeText(task.id)}
          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
        >
          <Copy className="w-4 h-4 mr-3" />
          Copy ID
        </button>

        {canRetry && onRetry && (
          <button
            onClick={() => onRetry(task.id)}
            className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <RotateCcw className="w-4 h-4 mr-3" />
            Retry Task
          </button>
        )}

        {canCancel && onCancel && (
          <button
            onClick={() => onCancel(task.id)}
            className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <Pause className="w-4 h-4 mr-3" />
            Cancel Task
          </button>
        )}

        {canDownload && onDownload && (
          <>
            <div className="border-t border-gray-200 my-1"></div>
            <button
              onClick={() => onDownload(task.id, 'json')}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <Download className="w-4 h-4 mr-3" />
              Download JSON
            </button>
            <button
              onClick={() => onDownload(task.id, 'csv')}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <Download className="w-4 h-4 mr-3" />
              Download CSV
            </button>
            <button
              onClick={() => onDownload(task.id, 'xlsx')}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <Download className="w-4 h-4 mr-3" />
              Download Excel
            </button>
          </>
        )}

        {onDelete && (
          <>
            <div className="border-t border-gray-200 my-1"></div>
            <button
              onClick={() => onDelete(task.id)}
              className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4 mr-3" />
              Delete Task
            </button>
          </>
        )}
      </div>
    </SmartDropdown>
  );
};

const LoadingRow: React.FC = () => (
  <tr className="animate-pulse">
    <td className="px-6 py-4 whitespace-nowrap">
      <div className="flex items-center">
        <div className="h-4 bg-gray-300 rounded w-24"></div>
      </div>
    </td>
    <td className="px-6 py-4 whitespace-nowrap">
      <div className="h-6 bg-gray-300 rounded w-20"></div>
    </td>
    <td className="px-6 py-4 whitespace-nowrap">
      <div className="h-4 bg-gray-300 rounded w-32"></div>
    </td>
    <td className="px-6 py-4 whitespace-nowrap">
      <div className="h-4 bg-gray-300 rounded w-16"></div>
    </td>
    <td className="px-6 py-4 whitespace-nowrap">
      <div className="h-4 bg-gray-300 rounded w-20"></div>
    </td>
    <td className="px-6 py-4 whitespace-nowrap text-right">
      <div className="h-6 bg-gray-300 rounded w-6 ml-auto"></div>
    </td>
  </tr>
);

const RecentTasksTable: React.FC<RecentTasksTableProps> = ({
  tasks,
  isLoading = false,
  onRetry,
  onCancel,
  onDelete,
  onDownload,
  showViewAll = true,
  onLoadMore,
  hasMore = false,
  isLoadingMore = false,
  showingAll = false,
}) => {
  const router = useRouter();

  const handleRowClick = (taskId: string) => {
    router.push(`/tasks/${taskId}`);
  };
  const truncateText = (text: string | undefined | null, maxLength: number = 50): string => {
    if (!text) return '';
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  const formatUrl = (url: string | undefined | null): string => {
    if (!url) return '';
    try {
      const urlObj = new URL(url);
      return urlObj.hostname + urlObj.pathname;
    } catch {
      return url;
    }
  };

  const getTaskUrl = (task: Task): string => {
    if (task.config?.urls && task.config.urls.length > 0) {
      return task.config.urls[0];
    }
    return '';
  };

  const getPriorityColor = (priority: Task['priority']): string => {
    const priorityStr = typeof priority === 'number' ?
      (priority >= 8 ? 'high' : priority >= 5 ? 'medium' : 'low') :
      priority;
      
    switch (priorityStr) {
      case 'high':
        return 'text-red-600 bg-red-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'low':
        return 'text-gray-600 bg-gray-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getPriorityLabel = (priority: Task['priority']): string => {
    if (typeof priority === 'number') {
      return priority >= 8 ? 'High' : priority >= 5 ? 'Medium' : 'Low';
    }
    return priority?.charAt(0).toUpperCase() + priority?.slice(1) || 'Medium';
  };

  if (isLoading) {
    return (
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Tasks</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Task
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  URL
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Priority
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {Array.from({ length: 5 }).map((_, index) => (
                <LoadingRow key={index} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Tasks</h3>
        </div>
        <div className="text-center py-12">
          <div className="w-12 h-12 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <Play className="w-6 h-6 text-gray-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-900 mb-2">No tasks yet</h3>
          <p className="text-sm text-gray-500 mb-4">
            Get started by creating your first extraction task.
          </p>
          <Link
            href="/tasks/create"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Create Task
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow-sm rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Recent Tasks</h3>
        {showViewAll && (
          <>
            {onLoadMore && hasMore && !showingAll ? (
              <button
                onClick={onLoadMore}
                disabled={isLoadingMore}
                className="text-sm text-primary-600 hover:text-primary-500 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoadingMore ? 'Loading...' : 'View all'}
              </button>
            ) : showingAll ? (
              <span className="text-sm text-gray-500 font-medium">
                Showing all tasks
              </span>
            ) : (
              <Link
                href="/tasks"
                className="text-sm text-primary-600 hover:text-primary-500 font-medium"
              >
                View all
              </Link>
            )}
          </>
        )}
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Task
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                URL
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {tasks.map((task) => (
              <ClickableTableRow
                key={task.id}
                task={task}
                onRowClick={handleRowClick}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {truncateText(task.name)}
                      </div>
                      {task.description && (
                        <div className="text-sm text-gray-500">
                          {truncateText(task.description, 60)}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <TaskStatus status={task.status} size="sm" />
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span className="text-sm text-gray-900">
                      {truncateText(formatUrl(getTaskUrl(task)), 40)}
                    </span>
                    {getTaskUrl(task) && (
                      <a
                        href={getTaskUrl(task)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-2 text-gray-400 hover:text-gray-600"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                    {getPriorityLabel(task.priority)}
                  </span>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <TaskActionsMenu
                    task={task}
                    onRetry={onRetry}
                    onCancel={onCancel}
                    onDelete={onDelete}
                    onDownload={onDownload}
                  />
                </td>
              </ClickableTableRow>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RecentTasksTable;