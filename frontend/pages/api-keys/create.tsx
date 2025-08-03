import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../../lib/auth';
import { useForm } from 'react-hook-form';
import api from '../../lib/api';
import Navbar from '../../components/Navbar';
import { CreateApiKeyRequest, ApiKey } from '../../types/api';
import { ArrowLeft, Key, Copy, Eye, EyeOff, Calendar, AlertCircle, CheckCircle } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

interface ApiKeyFormData {
  name: string;
  description?: string;
  expires_at?: string;
}

const CreateApiKeyPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdApiKey, setCreatedApiKey] = useState<ApiKey | null>(null);
  const [keyVisible, setKeyVisible] = useState(true);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<ApiKeyFormData>();

  // Authentication guard
  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const onSubmit = async (data: ApiKeyFormData) => {
    setIsSubmitting(true);

    try {
      const request: CreateApiKeyRequest = {
        name: data.name.trim(),
        description: data.description?.trim() || undefined,
        expires_at: data.expires_at || undefined,
      };

      const apiKey = await api.createApiKey(request);
      // Handle backend response where the full key is in 'api_key' field
      const processedApiKey = {
        ...apiKey,
        key: apiKey.api_key || apiKey.key || '',
      };
      setCreatedApiKey(processedApiKey);
      toast.success('API key created successfully!');
    } catch (error: any) {
      console.error('Failed to create API key:', error);
      toast.error(error.message || 'Failed to create API key');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyKey = async () => {
    if (!createdApiKey) return;
    
    try {
      await navigator.clipboard.writeText(createdApiKey.key);
      toast.success('API key copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy API key');
    }
  };

  const handleFinish = () => {
    router.push('/api-keys');
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

  // Show success state if API key was created
  if (createdApiKey) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center space-x-4 mb-4">
              <Link
                href="/api-keys"
                className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                Back to API Keys
              </Link>
            </div>
            
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900">API Key Created Successfully!</h1>
              <p className="text-gray-600 mt-2">
                Your new API key has been generated. Make sure to copy it now as you won't be able to see it again.
              </p>
            </div>
          </div>

          {/* API Key Display */}
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <div className="border-l-4 border-green-400 bg-green-50 p-4 mb-6">
              <div className="flex">
                <div className="ml-3">
                  <p className="text-sm text-green-700">
                    <strong>Important:</strong> This is the only time you'll be able to see the full API key. 
                    Make sure to copy it and store it securely.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key Name
                </label>
                <div className="bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
                  <span className="text-sm text-gray-900">{createdApiKey.name}</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key
                </label>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
                    <code className="text-sm font-mono text-gray-900 break-all">
                      {keyVisible ? (createdApiKey.key || createdApiKey.api_key || '') : '•'.repeat((createdApiKey.key || createdApiKey.api_key || '').length)}
                    </code>
                  </div>
                  <button
                    onClick={() => setKeyVisible(!keyVisible)}
                    className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none"
                    title={keyVisible ? 'Hide key' : 'Show key'}
                  >
                    {keyVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={handleCopyKey}
                    className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    <Copy className="w-4 h-4 mr-1" />
                    Copy
                  </button>
                </div>
              </div>

              {createdApiKey.expires_at && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Expires At
                  </label>
                  <div className="bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
                    <span className="text-sm text-gray-900">
                      {new Date(createdApiKey.expires_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Created At
                </label>
                <div className="bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
                  <span className="text-sm text-gray-900">
                    {new Date(createdApiKey.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Next Steps */}
          <div className="bg-blue-50 border border-blue-200 rounded-md p-6 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-blue-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">
                  Next Steps
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <ol className="list-decimal list-inside space-y-1">
                    <li>Copy and securely store your API key</li>
                    <li>Include the key in your API requests as a Bearer token</li>
                    <li>Check out the API documentation for usage examples</li>
                    <li>Monitor your API usage in the dashboard</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-center space-x-4">
            <Link
              href="/docs/api"
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              View API Docs
            </Link>
            
            <button
              onClick={handleFinish}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Continue to API Keys
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show creation form
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <Link
              href="/api-keys"
              className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back to API Keys
            </Link>
          </div>
          
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create New API Key</h1>
            <p className="text-gray-600 mt-1">
              Generate a new API key for programmatic access to Selextract
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Basic Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-6 flex items-center">
              <Key className="w-5 h-5 mr-2" />
              API Key Details
            </h2>
            
            <div className="space-y-6">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  API Key Name *
                </label>
                <input
                  {...register('name', { 
                    required: 'API key name is required',
                    minLength: { value: 3, message: 'Name must be at least 3 characters' },
                    maxLength: { value: 50, message: 'Name must be less than 50 characters' }
                  })}
                  type="text"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  placeholder="e.g., Production API Key, Development Key, Mobile App Key"
                />
                {errors.name && (
                  <p className="mt-2 text-sm text-red-600">{errors.name.message}</p>
                )}
                <p className="mt-1 text-sm text-gray-500">
                  Choose a descriptive name to help you identify this key later
                </p>
              </div>

              <div>
                <label htmlFor="expires_at" className="block text-sm font-medium text-gray-700">
                  Expiration Date (Optional)
                </label>
                <div className="mt-1 flex rounded-md shadow-sm">
                  <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                    <Calendar className="w-4 h-4" />
                  </span>
                  <input
                    {...register('expires_at')}
                    type="datetime-local"
                    className="flex-1 block w-full border-gray-300 rounded-none rounded-r-md focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    min={new Date().toISOString().slice(0, 16)}
                  />
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  Leave empty for a key that never expires. We recommend setting an expiration date for security.
                </p>
              </div>
            </div>
          </div>

          {/* Security Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Security Information</h3>
            
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <AlertCircle className="h-5 w-5 text-yellow-400" />
                </div>
                <div className="ml-3">
                  <h4 className="text-sm font-medium text-yellow-800">
                    Important Security Notes
                  </h4>
                  <div className="mt-2 text-sm text-yellow-700">
                    <ul className="list-disc list-inside space-y-1">
                      <li>Your API key will only be shown once after creation</li>
                      <li>Store your API key securely and never expose it in client-side code</li>
                      <li>Use environment variables or secure key management services</li>
                      <li>You can disable or delete this key at any time</li>
                      <li>Monitor your API usage regularly for any suspicious activity</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Usage Example */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Usage Example</h3>
            
            <div className="bg-gray-900 rounded-md p-4">
              <pre className="text-sm text-gray-100 overflow-x-auto">
{`# Using cURL
curl -H "Authorization: Bearer YOUR_API_KEY" \\
     -H "Content-Type: application/json" \\
     -d '{"name": "Test Task", "url": "https://example.com", "config": {...}}' \\
     https://api.selextract.com/v1/tasks

# Using Python requests
import requests

headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.selextract.com/v1/tasks",
    headers=headers,
    json={"name": "Test Task", "url": "https://example.com", "config": {...}}
)`}
              </pre>
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="flex items-center justify-end space-x-4">
            <Link
              href="/api-keys"
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Cancel
            </Link>
            
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
                  Creating API Key...
                </>
              ) : (
                'Create API Key'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateApiKeyPage;