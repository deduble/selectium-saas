import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQueryClient } from 'react-query';

/**
 * Navigation-aware cache management hook
 * Implements selective cache invalidation based on route changes
 * Provides scroll position restoration for better UX
 */
export const useNavigationAwareCache = () => {
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    const handleRouteChange = (url: string) => {
      // Invalidate tasks cache when returning to tasks page
      if (url === '/tasks' || url.startsWith('/tasks?')) {
        console.log('[NavigationCache] Invalidating tasks cache on route:', url);
        queryClient.invalidateQueries(['tasks']);
        queryClient.invalidateQueries(['tasks', 'progressive']);
      }

      // Invalidate dashboard stats when returning to dashboard
      if (url === '/dashboard') {
        console.log('[NavigationCache] Invalidating dashboard cache on route:', url);
        queryClient.invalidateQueries(['dashboard']);
        queryClient.invalidateQueries(['stats']);
      }
    };

    const handleBeforeRouteChange = (url: string) => {
      // Store current scroll position before navigation
      if (router.asPath.startsWith('/tasks/') && !router.asPath.startsWith('/tasks/create')) {
        const scrollPosition = window.scrollY;
        console.log('[NavigationCache] Storing scroll position:', scrollPosition);
        sessionStorage.setItem('tasksScrollPosition', scrollPosition.toString());
      }

      // Store scroll position for dashboard navigation
      if (router.asPath === '/dashboard') {
        const scrollPosition = window.scrollY;
        sessionStorage.setItem('dashboardScrollPosition', scrollPosition.toString());
      }
    };

    // Register event listeners
    router.events.on('routeChangeComplete', handleRouteChange);
    router.events.on('beforeHistoryChange', handleBeforeRouteChange);

    return () => {
      // Cleanup event listeners
      router.events.off('routeChangeComplete', handleRouteChange);
      router.events.off('beforeHistoryChange', handleBeforeRouteChange);
    };
  }, [router, queryClient]);

  // Restore scroll position when returning to tasks page
  useEffect(() => {
    if (router.asPath === '/tasks') {
      const savedPosition = sessionStorage.getItem('tasksScrollPosition');
      if (savedPosition) {
        console.log('[NavigationCache] Restoring tasks scroll position:', savedPosition);
        // Use setTimeout to ensure DOM is rendered
        setTimeout(() => {
          window.scrollTo(0, parseInt(savedPosition));
          sessionStorage.removeItem('tasksScrollPosition');
        }, 100);
      }
    }

    // Restore dashboard scroll position
    if (router.asPath === '/dashboard') {
      const savedPosition = sessionStorage.getItem('dashboardScrollPosition');
      if (savedPosition) {
        console.log('[NavigationCache] Restoring dashboard scroll position:', savedPosition);
        setTimeout(() => {
          window.scrollTo(0, parseInt(savedPosition));
          sessionStorage.removeItem('dashboardScrollPosition');
        }, 100);
      }
    }
  }, [router.asPath]);

  // Utility function for manual cache invalidation
  const invalidateTasksCache = () => {
    console.log('[NavigationCache] Manual tasks cache invalidation');
    queryClient.invalidateQueries(['tasks']);
    queryClient.invalidateQueries(['tasks', 'progressive']);
  };

  const invalidateDashboardCache = () => {
    console.log('[NavigationCache] Manual dashboard cache invalidation');
    queryClient.invalidateQueries(['dashboard']);
    queryClient.invalidateQueries(['stats']);
  };

  const invalidateTaskCache = (taskId: string) => {
    console.log('[NavigationCache] Invalidating individual task cache:', taskId);
    queryClient.invalidateQueries(['task', taskId]);
  };

  return {
    invalidateTasksCache,
    invalidateDashboardCache,
    invalidateTaskCache,
  };
};