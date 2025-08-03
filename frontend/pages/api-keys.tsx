import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from 'react-query';
import { useAuth } from '../lib/auth';
import api from '../lib/api';
import Navbar from '../components/Navbar';
import { ApiKey, ApiError } from '../types/api';
import { 
  Plus, 
  RefreshCw, 
  Copy, 
  Trash2, 
  Key, 
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
  XCircle,
  Calendar,
  Activity
} from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

const ApiKeysPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());

  // Authentication guard
  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch API keys
  const {
    data: apiKeys,
    isLoading: keysLoading,
    error: keysError,
  } = useQuery<ApiKey[], ApiError>(
    ['api-keys', refreshKey],
    () => api.getApiKeys(),
    {
      enabled: isAuthenticated,
      refetchOnWindowFocus: true,
    }
  );

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
    toast.success('API keys refreshed');
  };

  const handleCopyKey = async (keyValue: string) => {
    try {
      await navigator.clipboard.writeText(keyValue);
      toast.success('API key copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy API key');
    }
  };

  const handleToggleVisibility = (keyId: string) => {
    setVisibleKeys(prev => {
      const newSet = new Set(prev);
      if (newSet.has(keyId)) {
        newSet.delete(keyId);
      } else {
        newSet.add(keyId);
      }
      return newSet;
    });
  };

  const handleToggleApiKey = async (keyId: string) => {
    try {
      await api.toggleApiKey(keyId);
      setRefreshKey(prev => prev + 1);
      toast.success('API key status updated');
    } catch (error: any) {
      toast.error(error.message || 'Failed to update API key status');
    }
  };

  const handleDeleteApiKey = async (keyId: string, keyName: string) => {
    if (!confirm(`Are you sure you want to delete the API key "${keyName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await api.deleteApiKey(keyId);
      setRefreshKey(prev => prev + 1);
      toast.success('API key deleted successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete API key');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const maskApiKey = (key: string | undefined) => {
    if (!key || key.length <= 8) return key || '';
    return `${key.substring(0, 4)}${'*'.repeat(key.length - 8)}${key.substring(key.length - 4)}`;
  };

  const getStatusColor = (isActive: boolean) => {
    return isActive 
      ? 'bg-green-100 text-green-800' 
      : 'bg-red-100 text-red-800';
  };

  const getStatusIcon = (isActive: boolean) => {
    return isActive ? CheckCircle : XCircle;
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
              <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
              <p className="text-gray-600 mt-1">
                Manage your API keys for programmatic access to Selextract
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleRefresh}
                disabled={keysLoading}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${keysLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              
              <Link
                href="/api-keys/create"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create API Key
              </Link>
            </div>
          </div>
        </div>

        {/* Error State */}
        {keysError && (
          <div className="mb-8 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <AlertCircle className="w-5 h-5 text-red-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-red-800">
                  Error loading API keys
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{keysError.message}</p>
                </div>
                <div className="mt-4">
                  <button
                    onClick={handleRefresh}
                    className="text-sm bg-red-100 text-red-800 rounded-md px-3 py-1.5 font-medium hover:bg-red-200"
                  >
                    Try again
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {keysLoading ? (
          <div className="bg-white shadow rounded-lg p-6">
            <div className="animate-pulse space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/6"></div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* API Keys List */
          <div className="bg-white shadow rounded-lg overflow-hidden">
            {apiKeys && apiKeys.length > 0 ? (
              <div className="divide-y divide-gray-200">
                {apiKeys.map((apiKey) => {
                  const StatusIcon = getStatusIcon(apiKey.is_active);
                  const isVisible = visibleKeys.has(apiKey.id);
                  
                  return (
                    <div key={apiKey.id} className="p-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="flex-shrink-0">
                            <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                              <Key className="w-5 h-5 text-primary-600" />
                            </div>
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              <h3 className="text-lg font-medium text-gray-900 truncate">
                                {apiKey.name}
                              </h3>
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(apiKey.is_active)}`}>
                                <StatusIcon className="w-3 h-3 mr-1" />
                                {apiKey.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </div>
                            
                            <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                              <div className="flex items-center">
                                <Calendar className="w-4 h-4 mr-1" />
                                Created: {formatDate(apiKey.created_at)}
                              </div>
                              
                              {apiKey.last_used_at && (
                                <div className="flex items-center">
                                  <Activity className="w-4 h-4 mr-1" />
                                  Last used: {formatDate(apiKey.last_used_at)}
                                </div>
                              )}
                              
                              {apiKey.expires_at && (
                                <div className="flex items-center">
                                  <Calendar className="w-4 h-4 mr-1" />
                                  Expires: {formatDate(apiKey.expires_at)}
                                </div>
                              )}
                            </div>
                            
                            <div className="mt-3 flex items-center space-x-2">
                              <code className="bg-gray-100 px-3 py-1 rounded text-sm font-mono">
                                {isVisible ? (apiKey.key_preview || apiKey.key || '') : maskApiKey(apiKey.key_preview || apiKey.key)}
                              </code>
                              
                              <button
                                onClick={() => handleToggleVisibility(apiKey.id)}
                                className="p-1 text-gray-400 hover:text-gray-600"
                                title={isVisible ? 'Hide key' : 'Show key'}
                              >
                                {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                              </button>
                              
                              <button
                                onClick={() => handleCopyKey(apiKey.key_preview || apiKey.key || '')}
                                className="p-1 text-gray-400 hover:text-gray-600"
                                title="Copy to clipboard"
                              >
                                <Copy className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleToggleApiKey(apiKey.id)}
                            className={`inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md ${
                              apiKey.is_active
                                ? 'text-red-700 bg-red-100 hover:bg-red-200'
                                : 'text-green-700 bg-green-100 hover:bg-green-200'
                            }`}
                          >
                            {apiKey.is_active ? 'Disable' : 'Enable'}
                          </button>
                          
                          <button
                            onClick={() => handleDeleteApiKey(apiKey.id, apiKey.name)}
                            className="inline-flex items-center p-1.5 border border-transparent text-red-600 hover:text-red-800 focus:outline-none"
                            title="Delete API key"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* Empty State */
              <div className="text-center py-12">
                <Key className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No API keys</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Get started by creating your first API key for programmatic access.
                </p>
                <div className="mt-6">
                  <Link
                    href="/api-keys/create"
                    className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create API Key
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Information Section */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-md p-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <AlertCircle className="h-5 w-5 text-blue-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                API Key Security Best Practices
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <ul className="list-disc list-inside space-y-1">
                  <li>Keep your API keys secure and never share them publicly</li>
                  <li>Use different API keys for different applications or environments</li>
                  <li>Regularly rotate your API keys for enhanced security</li>
                  <li>Monitor API key usage and disable unused keys</li>
                  <li>Set expiration dates for API keys when possible</li>
                </ul>
              </div>
              <div className="mt-4">
                <Link
                  href="/docs/api"
                  className="text-sm font-medium text-blue-800 hover:text-blue-600 underline"
                >
                  View API Documentation →
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        {apiKeys && apiKeys.length > 0 && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Link
              href="/api-keys/create"
              className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-primary-500 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
            >
              <div>
                <span className="rounded-lg inline-flex p-3 bg-primary-50 text-primary-600 ring-4 ring-white">
                  <Plus className="w-6 h-6" />
                </span>
              </div>
              <div className="mt-8">
                <h3 className="text-lg font-medium text-gray-900">
                  Create New API Key
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Generate a new API key for accessing the Selextract API programmatically.
                </p>
              </div>
            </Link>

            <Link
              href="/docs/api"
              className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-primary-500 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
            >
              <div>
                <span className="rounded-lg inline-flex p-3 bg-blue-50 text-blue-600 ring-4 ring-white">
                  <Key className="w-6 h-6" />
                </span>
              </div>
              <div className="mt-8">
                <h3 className="text-lg font-medium text-gray-900">
                  API Documentation
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Learn how to use the Selextract API with examples and code samples.
                </p>
              </div>
            </Link>

            <div className="relative group bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div>
                <span className="rounded-lg inline-flex p-3 bg-green-50 text-green-600 ring-4 ring-white">
                  <Activity className="w-6 h-6" />
                </span>
              </div>
              <div className="mt-8">
                <h3 className="text-lg font-medium text-gray-900">
                  API Usage Stats
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Monitor your API usage and performance metrics across all keys.
                </p>
                <p className="mt-2 text-xs text-gray-400">
                  Coming soon
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ApiKeysPage;