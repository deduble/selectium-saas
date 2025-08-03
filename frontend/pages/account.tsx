import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from 'react-query';
import { useAuth } from '../lib/auth';
import { useForm } from 'react-hook-form';
import api from '../lib/api';
import Navbar from '../components/Navbar';
import SubscriptionCard from '../components/SubscriptionCard';
import { User, Subscription, DashboardStats, ApiError } from '../types/api';
import { 
  User as UserIcon, 
  Mail, 
  Calendar,
  CreditCard,
  Shield,
  Activity,
  Trash2,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Eye,
  BarChart3,
  Settings,
  Globe
} from 'lucide-react';
import toast from 'react-hot-toast';

interface ProfileFormData {
  full_name: string;
  email: string;
}

const AccountPage: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, refreshUser } = useAuth();
  const [isUpdating, setIsUpdating] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<ProfileFormData>({
    defaultValues: {
      full_name: user?.full_name || '',
      email: user?.email || '',
    },
  });

  // Update form when user data changes
  React.useEffect(() => {
    if (user) {
      reset({
        full_name: user.full_name,
        email: user.email,
      });
    }
  }, [user, reset]);

  // Authentication guard
  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch subscription data
  const {
    data: subscription,
    isLoading: subscriptionLoading,
    error: subscriptionError,
  } = useQuery<Subscription, ApiError>(
    ['subscription', refreshKey],
    () => api.getSubscription(),
    {
      enabled: isAuthenticated,
      refetchOnWindowFocus: true,
    }
  );

  // Fetch dashboard stats for usage overview
  const {
    data: stats,
    isLoading: statsLoading,
  } = useQuery<DashboardStats, ApiError>(
    ['dashboard-stats-account', refreshKey],
    () => api.getDashboardStats(),
    {
      enabled: isAuthenticated,
      refetchOnWindowFocus: true,
    }
  );

  const onSubmit = async (data: ProfileFormData) => {
    setIsUpdating(true);

    try {
      await api.updateProfile({
        full_name: data.full_name.trim(),
        email: data.email.trim(),
      });
      
      await refreshUser();
      toast.success('Profile updated successfully');
    } catch (error: any) {
      console.error('Failed to update profile:', error);
      toast.error(error.message || 'Failed to update profile');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') {
      toast.error('Please type "DELETE" to confirm account deletion');
      return;
    }

    try {
      await api.deleteAccount();
      toast.success('Account deleted successfully');
      router.push('/');
    } catch (error: any) {
      console.error('Failed to delete account:', error);
      toast.error(error.message || 'Failed to delete account');
    }
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
    refreshUser();
    toast.success('Account data refreshed');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case 'enterprise':
        return 'bg-gray-100 text-gray-800';
      case 'pro':
        return 'bg-purple-100 text-purple-800';
      case 'basic':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-600';
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
  if (!isAuthenticated || !user) {
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
              <h1 className="text-2xl font-bold text-gray-900">Account Settings</h1>
              <p className="text-gray-600 mt-1">
                Manage your profile, subscription, and account preferences
              </p>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={subscriptionLoading || statsLoading}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${(subscriptionLoading || statsLoading) ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Profile Information */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-6 flex items-center">
                <UserIcon className="w-5 h-5 mr-2" />
                Profile Information
              </h2>
              
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div>
                  <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                    Full Name
                  </label>
                  <input
                    {...register('full_name', { 
                      required: 'Full name is required',
                      minLength: { value: 2, message: 'Name must be at least 2 characters' }
                    })}
                    type="text"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  />
                  {errors.full_name && (
                    <p className="mt-2 text-sm text-red-600">{errors.full_name.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    Email Address
                  </label>
                  <div className="mt-1 flex rounded-md shadow-sm">
                    <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                      <Mail className="w-4 h-4" />
                    </span>
                    <input
                      {...register('email', { 
                        required: 'Email is required',
                        pattern: {
                          value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                          message: 'Invalid email address'
                        }
                      })}
                      type="email"
                      className="flex-1 block w-full border-gray-300 rounded-none rounded-r-md focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    />
                  </div>
                  {errors.email && (
                    <p className="mt-2 text-sm text-red-600">{errors.email.message}</p>
                  )}
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={!isDirty || isUpdating}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isUpdating ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Updating...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        Save Changes
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Account Details */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-6 flex items-center">
                <Shield className="w-5 h-5 mr-2" />
                Account Details
              </h2>
              
              <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-gray-500">User ID</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">{user.id}</dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Account Created</dt>
                  <dd className="mt-1 text-sm text-gray-900 flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    {formatDate(user.created_at)}
                  </dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                  <dd className="mt-1 text-sm text-gray-900 flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    {formatDate(user.updated_at)}
                  </dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Account Status</dt>
                  <dd className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {user.is_active ? (
                        <CheckCircle className="w-3 h-3 mr-1" />
                      ) : (
                        <AlertCircle className="w-3 h-3 mr-1" />
                      )}
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Subscription Tier</dt>
                  <dd className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTierBadgeColor(user.subscription_tier)}`}>
                      <CreditCard className="w-3 h-3 mr-1" />
                      {user.subscription_tier.toUpperCase()}
                    </span>
                  </dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Compute Units Remaining</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-medium">
                    {(Number(user.compute_units_remaining) || 0).toLocaleString()}
                    {user.compute_units_limit && (
                      <span className="text-gray-500 font-normal">
                        {' '}of {(Number(user.compute_units_limit) || 0).toLocaleString()}
                      </span>
                    )}
                  </dd>
                </div>
              </dl>
            </div>

            {/* Usage Overview */}
            {stats && (
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-6 flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2" />
                  Usage Overview
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Activity className="h-5 w-5 text-blue-400" />
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-500">Total Tasks</p>
                        <p className="text-lg font-semibold text-gray-900">{stats.total_tasks}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <CheckCircle className="h-5 w-5 text-green-400" />
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-500">Completed</p>
                        <p className="text-lg font-semibold text-gray-900">{stats.completed_tasks}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Globe className="h-5 w-5 text-primary-400" />
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-500">API Calls Used</p>
                        <p className="text-lg font-semibold text-gray-900">{stats.api_calls_used}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <BarChart3 className="h-5 w-5 text-purple-400" />
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-500">Success Rate</p>
                        <p className="text-lg font-semibold text-gray-900">{(stats.success_rate || 0).toFixed(1)}%</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Danger Zone */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-red-900 mb-6 flex items-center">
                <AlertCircle className="w-5 h-5 mr-2" />
                Danger Zone
              </h2>
              
              <div className="border border-red-200 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-sm font-medium text-red-900">Delete Account</h3>
                    <p className="mt-1 text-sm text-red-700">
                      Permanently delete your account and all associated data. This action cannot be undone.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowDeleteDialog(true)}
                    className="ml-4 inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Delete Account
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Subscription Info */}
            {subscription ? (
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  <CreditCard className="w-5 h-5 mr-2" />
                  Subscription
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Status</span>
                    <span className={`text-sm font-medium ${
                      subscription.status === 'active' ? 'text-green-600' : 'text-yellow-600'
                    }`}>
                      {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Tier</span>
                    <span className="text-sm font-medium text-gray-900">
                      {subscription.tier?.charAt(0).toUpperCase() + subscription.tier?.slice(1) || 'N/A'}
                    </span>
                  </div>
                  {subscription.current_period_end && (
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Next Billing</span>
                      <span className="text-sm font-medium text-gray-900">
                        {formatDate(subscription.current_period_end)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : subscriptionError ? (
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center">
                  <AlertCircle className="w-5 h-5 text-red-400 mr-3" />
                  <div>
                    <h3 className="text-sm font-medium text-red-800">
                      Error loading subscription
                    </h3>
                    <p className="mt-1 text-sm text-red-700">
                      {subscriptionError.message}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white shadow rounded-lg p-6">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
                  <div className="h-6 bg-gray-200 rounded w-1/2 mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded w-full"></div>
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
              
              <div className="space-y-3">
                <button
                  onClick={() => router.push('/billing')}
                  className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                >
                  <CreditCard className="w-4 h-4 mr-2" />
                  Manage Billing
                </button>
                
                <button
                  onClick={() => router.push('/api-keys')}
                  className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Shield className="w-4 h-4 mr-2" />
                  API Keys
                </button>
                
                <button
                  onClick={() => router.push('/settings')}
                  className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Delete Account Dialog */}
        {showDeleteDialog && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div className="mt-3 text-center">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                  <Trash2 className="h-6 w-6 text-red-600" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mt-4">Delete Account</h3>
                <div className="mt-2 px-7 py-3">
                  <p className="text-sm text-gray-500">
                    This action cannot be undone. This will permanently delete your account and remove all associated data.
                  </p>
                  <p className="text-sm text-red-600 mt-2 font-medium">
                    Type "DELETE" to confirm:
                  </p>
                  <input
                    type="text"
                    value={deleteConfirmText}
                    onChange={(e) => setDeleteConfirmText(e.target.value)}
                    className="mt-2 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500 sm:text-sm"
                    placeholder="DELETE"
                  />
                </div>
                <div className="items-center px-4 py-3">
                  <button
                    onClick={handleDeleteAccount}
                    disabled={deleteConfirmText !== 'DELETE'}
                    className="px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md w-full shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Delete Account
                  </button>
                  <button
                    onClick={() => {
                      setShowDeleteDialog(false);
                      setDeleteConfirmText('');
                    }}
                    className="mt-3 px-4 py-2 bg-gray-300 text-gray-800 text-base font-medium rounded-md w-full shadow-sm hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountPage;