import { useCallback } from 'react';
import { useQueryClient } from 'react-query';
import { Task, PaginatedResponse, ApiError } from '../types/api';
import { api } from './api';

/**
 * Optimistic task operations hook
 * Provides immediate UI updates before API calls complete
 * Includes rollback mechanisms for failed operations
 */
export const useOptimisticTaskOperations = () => {
  const queryClient = useQueryClient();

  /**
   * Update task cache optimistically
   */
  const updateTaskOptimistically = useCallback(
    (taskId: string, updates: Partial<Task>) => {
      console.log('[OptimisticUpdate] Updating task:', taskId, updates);

      // Update individual task cache
      const currentTask = queryClient.getQueryData(['task', taskId]) as Task | undefined;
      if (currentTask) {
        queryClient.setQueryData(['task', taskId], { ...currentTask, ...updates });
      }

      // Update tasks list cache (progressive)
      const currentProgressiveTasks = queryClient.getQueryData(['tasks', 'progressive']) as PaginatedResponse<Task> | undefined;
      if (currentProgressiveTasks) {
        queryClient.setQueryData(['tasks', 'progressive'], {
          ...currentProgressiveTasks,
          items: currentProgressiveTasks.items.map(task =>
            task.id === taskId ? { ...task, ...updates } : task
          )
        });
      }

      // Update regular tasks list cache
      const currentTasks = queryClient.getQueryData(['tasks']) as PaginatedResponse<Task> | undefined;
      if (currentTasks) {
        queryClient.setQueryData(['tasks'], {
          ...currentTasks,
          items: currentTasks.items.map(task =>
            task.id === taskId ? { ...task, ...updates } : task
          )
        });
      }
    },
    [queryClient]
  );

  /**
   * Remove task from cache optimistically
   */
  const removeTaskOptimistically = useCallback(
    (taskId: string) => {
      console.log('[OptimisticUpdate] Removing task:', taskId);

      // Update tasks list cache (progressive)
      const currentProgressiveTasks = queryClient.getQueryData(['tasks', 'progressive']) as PaginatedResponse<Task> | undefined;
      if (currentProgressiveTasks) {
        queryClient.setQueryData(['tasks', 'progressive'], {
          ...currentProgressiveTasks,
          items: currentProgressiveTasks.items.filter(task => task.id !== taskId),
          total: currentProgressiveTasks.total - 1
        });
      }

      // Update regular tasks list cache
      const currentTasks = queryClient.getQueryData(['tasks']) as PaginatedResponse<Task> | undefined;
      if (currentTasks) {
        queryClient.setQueryData(['tasks'], {
          ...currentTasks,
          items: currentTasks.items.filter(task => task.id !== taskId),
          total: currentTasks.total - 1
        });
      }

      // Remove individual task cache
      queryClient.removeQueries(['task', taskId]);
    },
    [queryClient]
  );

  /**
   * Rollback task updates by invalidating cache
   */
  const rollbackTaskUpdate = useCallback(
    (taskId: string) => {
      console.log('[OptimisticUpdate] Rolling back task update:', taskId);
      queryClient.invalidateQueries(['task', taskId]);
      queryClient.invalidateQueries(['tasks']);
      queryClient.invalidateQueries(['tasks', 'progressive']);
    },
    [queryClient]
  );

  /**
   * Optimistic task status update
   */
  const updateTaskStatus = useCallback(
    async (taskId: string, status: Task['status'], apiCall: () => Promise<Task>) => {
      const originalData = queryClient.getQueryData(['task', taskId]) as Task | undefined;
      
      try {
        // Apply optimistic update
        updateTaskOptimistically(taskId, { 
          status,
          updated_at: new Date().toISOString()
        });

        // Execute actual API call
        const updatedTask = await apiCall();
        
        // Update with real data from API
        updateTaskOptimistically(taskId, updatedTask);
        
        return updatedTask;
      } catch (error) {
        console.error('[OptimisticUpdate] Status update failed, rolling back:', error);
        // Rollback on failure
        if (originalData) {
          updateTaskOptimistically(taskId, originalData);
        } else {
          rollbackTaskUpdate(taskId);
        }
        throw error;
      }
    },
    [updateTaskOptimistically, rollbackTaskUpdate, queryClient]
  );

  /**
   * Optimistic task deletion
   */
  const deleteTaskOptimistically = useCallback(
    async (taskId: string, apiCall: () => Promise<void>) => {
      const originalTasksData = queryClient.getQueryData(['tasks', 'progressive']) as PaginatedResponse<Task> | undefined;
      const originalRegularTasksData = queryClient.getQueryData(['tasks']) as PaginatedResponse<Task> | undefined;
      const originalTaskData = queryClient.getQueryData(['task', taskId]) as Task | undefined;

      try {
        // Apply optimistic removal
        removeTaskOptimistically(taskId);

        // Execute actual API call
        await apiCall();

        console.log('[OptimisticUpdate] Task deletion confirmed:', taskId);
      } catch (error) {
        console.error('[OptimisticUpdate] Deletion failed, rolling back:', error);
        
        // Rollback on failure - restore original data
        if (originalTasksData) {
          queryClient.setQueryData(['tasks', 'progressive'], originalTasksData);
        }
        if (originalRegularTasksData) {
          queryClient.setQueryData(['tasks'], originalRegularTasksData);
        }
        if (originalTaskData) {
          queryClient.setQueryData(['task', taskId], originalTaskData);
        }
        
        throw error;
      }
    },
    [removeTaskOptimistically, queryClient]
  );

  /**
   * Optimistic task retry
   */
  const retryTaskOptimistically = useCallback(
    async (taskId: string) => {
      return updateTaskStatus(taskId, 'pending', () => api.retryTask(taskId));
    },
    [updateTaskStatus]
  );

  /**
   * Optimistic task cancellation
   */
  const cancelTaskOptimistically = useCallback(
    async (taskId: string) => {
      return updateTaskStatus(taskId, 'cancelled', () => api.cancelTask(taskId));
    },
    [updateTaskStatus]
  );

  /**
   * Perform optimistic task update with API call
   */
  const performOptimisticTaskUpdate = useCallback(
    async (taskId: string, updates: Partial<Task>, apiCall: () => Promise<Task>) => {
      const originalData = queryClient.getQueryData(['task', taskId]) as Task | undefined;
      
      try {
        // Apply optimistic update
        updateTaskOptimistically(taskId, {
          ...updates,
          updated_at: new Date().toISOString()
        });

        // Execute actual API call
        const updatedTask = await apiCall();
        
        // Update with real data from API
        updateTaskOptimistically(taskId, updatedTask);
        
        return updatedTask;
      } catch (error) {
        console.error('[OptimisticUpdate] Task update failed, rolling back:', error);
        // Rollback on failure
        if (originalData) {
          updateTaskOptimistically(taskId, originalData);
        } else {
          rollbackTaskUpdate(taskId);
        }
        throw error;
      }
    },
    [updateTaskOptimistically, rollbackTaskUpdate, queryClient]
  );

  return {
    updateTaskOptimistically,
    removeTaskOptimistically,
    rollbackTaskUpdate,
    updateTaskStatus,
    deleteTaskOptimistically,
    retryTaskOptimistically,
    cancelTaskOptimistically,
    performOptimisticTaskUpdate,
  };
};