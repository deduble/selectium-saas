import { useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient } from 'react-query';
import { Task, PaginatedResponse, ApiError } from '../types/api';
import { api } from './api';

interface UseProgressiveTasksReturn {
  tasks: Task[];
  loadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  error: ApiError | null;
  showingAll: boolean;
  refresh: () => void;
  isRefreshing: boolean;
}

interface UseProgressiveTasksOptions {
  initialPerPage?: number;
  autoRefresh?: boolean;
  autoRefreshInterval?: number;
  enableCacheOptimization?: boolean;
}

export const useProgressiveTasks = (
  options: UseProgressiveTasksOptions = {}
): UseProgressiveTasksReturn => {
  const {
    initialPerPage = 5,
    autoRefresh = true,
    autoRefreshInterval = 15000, // 15 seconds
    enableCacheOptimization = true
  } = options;

  const [perPage, setPerPage] = useState(initialPerPage);
  const [showingAll, setShowingAll] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const queryClient = useQueryClient();

  const {
    data: tasksResponse,
    isLoading,
    error,
    refetch
  } = useQuery<PaginatedResponse<Task>, ApiError>(
    ['tasks', 'progressive', perPage],
    () => api.getTasks({ page: 1, per_page: perPage }),
    {
      enabled: true,
      keepPreviousData: true,
      refetchInterval: autoRefresh ? autoRefreshInterval : false,
      refetchIntervalInBackground: false,
      staleTime: 5000, // Consider data stale after 5 seconds
      cacheTime: 300000, // Keep in cache for 5 minutes
      onSuccess: (data) => {
        // Update individual task caches for optimistic updates
        if (enableCacheOptimization && data?.items) {
          data.items.forEach(task => {
            queryClient.setQueryData(['task', task.id], task);
          });
        }
      }
    }
  );

  const loadMore = useCallback(() => {
    if (tasksResponse && !showingAll) {
      const newPerPage = Math.min(perPage + 10, tasksResponse.total);
      setPerPage(newPerPage);
      
      if (newPerPage >= tasksResponse.total) {
        setShowingAll(true);
      }
    }
  }, [perPage, tasksResponse, showingAll]);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // Invalidate all related caches before refetch
      queryClient.invalidateQueries(['tasks']);
      queryClient.invalidateQueries(['dashboard']);
      
      await refetch();
    } catch (error) {
      console.error('[ProgressiveTasks] Refresh failed:', error);
    } finally {
      setIsRefreshing(false);
    }
  }, [refetch, queryClient]);

  // Reset pagination when switching to a different page size initially
  useEffect(() => {
    if (tasksResponse && perPage !== initialPerPage && tasksResponse.total > 0) {
      const shouldShowAll = perPage >= tasksResponse.total;
      setShowingAll(shouldShowAll);
    }
  }, [tasksResponse, perPage, initialPerPage]);

  // Auto-refresh on window focus if enabled
  useEffect(() => {
    if (!autoRefresh) return;

    const handleFocus = () => {
      // Only refresh if data is stale (older than 30 seconds)
      const queryState = queryClient.getQueryState(['tasks', 'progressive', perPage]);
      const isStale = !queryState?.dataUpdatedAt ||
        Date.now() - queryState.dataUpdatedAt > 30000;
      
      if (isStale) {
        console.log('[ProgressiveTasks] Auto-refreshing on window focus');
        refetch();
      }
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [autoRefresh, refetch, queryClient, perPage]);

  // Optimize cache by prefetching next set of tasks
  useEffect(() => {
    if (enableCacheOptimization && tasksResponse && hasMore && !isLoading) {
      const nextPerPage = Math.min(perPage + 10, tasksResponse.total);
      
      // Prefetch next batch if user is close to the end
      queryClient.prefetchQuery(
        ['tasks', 'progressive', nextPerPage],
        () => api.getTasks({ page: 1, per_page: nextPerPage }),
        {
          staleTime: 30000, // 30 seconds
        }
      );
    }
  }, [tasksResponse, perPage, isLoading, enableCacheOptimization, queryClient]);

  const hasMore = tasksResponse ? perPage < tasksResponse.total : false;

  return {
    tasks: tasksResponse?.items || [],
    loadMore,
    hasMore,
    isLoading,
    error,
    showingAll,
    refresh,
    isRefreshing: isRefreshing || isLoading,
  };
};