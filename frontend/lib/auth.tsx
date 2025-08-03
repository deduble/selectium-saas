import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { useRouter } from 'next/router';
import Cookies from 'js-cookie';
import { User, AuthContextType, AuthState, LoginResponse } from '../types/auth';
import { api } from './api';
import toast from 'react-hot-toast';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    token: null,
  });

  const router = useRouter();

  useEffect(() => {
    const initializeAuth = async () => {
      // Dev auto-login
      if (process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN === 'true' && process.env.NODE_ENV === 'development') {
        try {
          console.log('🚀 Attempting development auto-login...');
          const response = await api.devLogin();
          await login(response.access_token);
          console.log('✅ Development auto-login successful.');
          return;
        } catch (error) {
          console.error('🧑‍💻 Development auto-login failed:', error);
          toast.error('Development auto-login failed. Proceeding with normal auth.');
        }
      }

      const token = Cookies.get('access_token');
      
      if (token) {
        try {
          setAuthState(prev => ({ ...prev, token, isLoading: true }));
          const user = await api.getCurrentUser();
          setAuthState({
            user,
            isLoading: false,
            isAuthenticated: true,
            token,
          });
        } catch (error) {
          console.error('Failed to initialize auth:', error);
          Cookies.remove('access_token');
          setAuthState({
            user: null,
            isLoading: false,
            isAuthenticated: false,
            token: null,
          });
        }
      } else {
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }
    };

    initializeAuth();
  }, []);

  const login = useCallback(async (token: string): Promise<void> => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));
      
      // Set token in cookie and API headers
      Cookies.set('access_token', token, {
        expires: 7, // 7 days
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax'
      });
      
      // Fetch user data
      const user = await api.getCurrentUser();
      
      setAuthState({
        user,
        isLoading: false,
        isAuthenticated: true,
        token,
      });

      toast.success(`Welcome back, ${user.full_name || user.email}!`);
      
      // Redirect to dashboard or intended page
      const redirectTo = router.query.redirect as string || '/dashboard';
      router.push(redirectTo);
    } catch (error) {
      console.error('Login failed:', error);
      Cookies.remove('access_token');
      setAuthState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
        token: null,
      });
      toast.error('Login failed. Please try again.');
      throw error;
    }
  }, [router]);

  const logout = useCallback((): void => {
    Cookies.remove('access_token');
    setAuthState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      token: null,
    });
    
    toast.success('Logged out successfully');
    router.push('/login');
  }, [router]);

  const refreshUser = useCallback(async (): Promise<void> => {
    if (!authState.token) return;

    try {
      const user = await api.getCurrentUser();
      setAuthState(prev => ({ ...prev, user }));
    } catch (error) {
      console.error('Failed to refresh user:', error);
      // If refresh fails, logout the user
      logout();
    }
  }, [authState.token, logout]);

  const updateUser = useCallback((userData: Partial<User>): void => {
    if (authState.user) {
      setAuthState(prev => ({
        ...prev,
        user: { ...prev.user!, ...userData }
      }));
    }
  }, [authState.user]);

  const value: AuthContextType = {
    user: authState.user,
    isLoading: authState.isLoading,
    isAuthenticated: authState.isAuthenticated,
    login,
    logout,
    refreshUser,
    updateUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Higher-order component for protected routes
export interface WithAuthOptions {
  redirectTo?: string;
  allowedTiers?: User['subscription_tier'][];
}

export const withAuth = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options: WithAuthOptions = {}
) => {
  const WithAuthComponent: React.FC<P> = (props) => {
    const { user, isLoading, isAuthenticated } = useAuth();
    const router = useRouter();
    const { redirectTo = '/login', allowedTiers } = options;

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        const redirectUrl = `${redirectTo}?redirect=${encodeURIComponent(router.asPath)}`;
        router.replace(redirectUrl);
        return;
      }

      if (user && allowedTiers && !allowedTiers.includes(user.subscription_tier)) {
        toast.error('Access denied. Please upgrade your subscription.');
        router.replace('/billing');
        return;
      }
    }, [isLoading, isAuthenticated, user, router]);

    if (isLoading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      );
    }

    if (!isAuthenticated || !user) {
      return null;
    }

    if (allowedTiers && !allowedTiers.includes(user.subscription_tier)) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };

  WithAuthComponent.displayName = `withAuth(${WrappedComponent.displayName || WrappedComponent.name})`;

  return WithAuthComponent;
};

// Hook for checking subscription access
export const useSubscriptionAccess = () => {
  const { user } = useAuth();

  const hasFeatureAccess = (feature: string): boolean => {
    if (!user) return false;

    const featureMap: Record<User['subscription_tier'], string[]> = {
      free: ['basic_scraping'],
      basic: ['basic_scraping', 'advanced_selectors', 'api_access'],
      pro: ['basic_scraping', 'advanced_selectors', 'api_access', 'bulk_operations', 'premium_support'],
      enterprise: ['basic_scraping', 'advanced_selectors', 'api_access', 'bulk_operations', 'premium_support', 'custom_integrations']
    };

    return featureMap[user.subscription_tier]?.includes(feature) || false;
  };

  const canCreateTask = (): boolean => {
    if (!user) return false;
    return user.compute_units_remaining > 0;
  };

  const getRemainingCalls = (): number => {
    if (!user) return 0;
    return Math.max(0, user.compute_units_remaining);
  };

  const getUsagePercentage = (): number => {
    if (!user || !user.compute_units_limit) return 0;
    const used = user.compute_units_limit - user.compute_units_remaining;
    return Math.min(100, (used / user.compute_units_limit) * 100);
  };

  return {
    hasFeatureAccess,
    canCreateTask,
    getRemainingCalls,
    getUsagePercentage,
    tier: user?.subscription_tier,
    status: user?.subscription_status,
  };
};

// Google OAuth utilities
export const initiateGoogleAuth = async (): Promise<void> => {
  try {
    // Get OAuth URL from backend
    const response = await api.getGoogleAuthUrl();
    
    // Redirect to Google OAuth
    window.location.href = response.auth_url;
  } catch (error) {
    console.error('Failed to initiate Google auth:', error);
    toast.error('Failed to initiate Google authentication');
  }
};

export default AuthContext;