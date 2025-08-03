import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth, useSubscriptionAccess } from '../../lib/auth';
import { useForm } from 'react-hook-form';
import api from '../../lib/api';
import Navbar from '../../components/Navbar';
import { CreateTaskRequest, TaskConfig } from '../../types/api';
import { ArrowLeft, Plus, Trash2, Info, Clock, Globe, Settings } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

interface TaskFormData {
  name: string;
  description: string;
  url: string;
  priority: 'low' | 'medium' | 'high';
  scheduled_at?: string;
  selectors: { [key: string]: string };
  wait_for?: string;
  timeout?: number;
  screenshot?: boolean;
  pdf?: boolean;
  scroll_to_bottom?: boolean;
  wait_time?: number;
}

const CreateTaskPage: React.FC = () => {
  const router = useRouter();
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();
  const { canCreateTask, getRemainingCalls } = useSubscriptionAccess();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectors, setSelectors] = useState<{ name: string; selector: string }[]>([
    { name: '', selector: '' }
  ]);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<TaskFormData>({
    defaultValues: {
      priority: 'medium',
      timeout: 30000,
      wait_time: 2000,
      screenshot: false,
      pdf: false,
      scroll_to_bottom: false,
    },
  });

  // Authentication guard
  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const addSelector = () => {
    setSelectors([...selectors, { name: '', selector: '' }]);
  };

  const removeSelector = (index: number) => {
    if (selectors.length > 1) {
      setSelectors(selectors.filter((_, i) => i !== index));
    }
  };

  const updateSelector = (index: number, field: 'name' | 'selector', value: string) => {
    const updated = [...selectors];
    updated[index][field] = value;
    setSelectors(updated);
  };

  const onSubmit = async (data: TaskFormData) => {
    if (!canCreateTask()) {
      toast.error('You have no remaining compute units. Please upgrade your plan.');
      return;
    }

    // Validate selectors
    const validSelectors = selectors.filter(s => s.name.trim() && s.selector.trim());
    if (validSelectors.length === 0) {
      toast.error('At least one selector is required');
      return;
    }

    setIsSubmitting(true);

    try {
      // Build selectors object
      const selectorsObj: Record<string, string> = {};
      validSelectors.forEach(s => {
        selectorsObj[s.name.trim()] = s.selector.trim();
      });

      // Convert priority from string to number
      const priorityMap = { low: 3, medium: 5, high: 8 };
      const priorityNumber = priorityMap[data.priority] || 5;

      // Build task config - convert timeout from milliseconds to seconds
      const timeoutInSeconds = Math.floor((data.timeout || 30000) / 1000);
      
      const config: TaskConfig = {
        urls: [data.url.trim()],
        selectors: selectorsObj,
        output_format: 'json',
        include_metadata: true,
        follow_redirects: true,
        timeout: Math.min(Math.max(timeoutInSeconds, 5), 300), // Ensure timeout is between 5-300 seconds
      };

      // Build request
      const request: CreateTaskRequest = {
        name: data.name.trim(),
        description: data.description?.trim() || undefined,
        task_type: 'simple_scraping',
        config,
        priority: priorityNumber,
        scheduled_at: data.scheduled_at || undefined,
      };

      // Debug logging
      console.log('Form data:', data);
      console.log('Selectors state:', selectors);
      console.log('Valid selectors:', validSelectors);
      console.log('Selectors object:', selectorsObj);
      console.log('Final request:', JSON.stringify(request, null, 2));

      const task = await api.createTask(request);
      
      toast.success('Task created successfully!');
      router.push(`/tasks/${task.id}`);
    } catch (error: any) {
      console.error('Failed to create task:', error);
      
      // Handle different types of errors
      let errorMessage = 'Failed to create task';
      
      if (error.message && Array.isArray(error.message)) {
        // FastAPI validation errors return as array of objects with {type, loc, msg, input, url}
        errorMessage = error.message
          .map((err: any) => err.msg || err.message || String(err))
          .join(', ');
      } else if (error.details && Array.isArray(error.details)) {
        // Alternative error format
        errorMessage = error.details
          .map((detail: any) => detail.msg || detail.message || String(detail))
          .join(', ');
      } else if (error.message) {
        // Simple string message
        errorMessage = Array.isArray(error.message) ? error.message.join(', ') : error.message;
      }
      
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
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

  const remainingCalls = getRemainingCalls() || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Create New Task</h1>
              <p className="text-gray-600 mt-1">
                Set up a new data extraction task with custom selectors and configuration
              </p>
            </div>
            
            <div className="text-sm text-gray-600">
              <span className="font-medium">{(Number(remainingCalls) || 0).toLocaleString()}</span> compute units remaining
            </div>
          </div>
        </div>

        {/* Usage Warning */}
        {!canCreateTask() && (
          <div className="mb-6 bg-orange-50 border border-orange-200 rounded-md p-4">
            <div className="flex">
              <Info className="w-5 h-5 text-orange-400 mr-3 mt-0.5" />
              <div>
                <h3 className="text-sm font-medium text-orange-800">
                  No compute units remaining
                </h3>
                <p className="mt-2 text-sm text-orange-700">
                  You need compute units to create new tasks. 
                  <Link href="/billing" className="font-medium underline hover:text-orange-800">
                    Upgrade your plan
                  </Link> to get more compute units.
                </p>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {/* Basic Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-6">Basic Information</h2>
            
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  Task Name *
                </label>
                <input
                  {...register('name', { required: 'Task name is required' })}
                  type="text"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  placeholder="e.g., Extract product listings from e-commerce site"
                />
                {errors.name && (
                  <p className="mt-2 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  {...register('description')}
                  rows={3}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  placeholder="Optional description of what this task extracts..."
                />
              </div>

              <div>
                <label htmlFor="url" className="block text-sm font-medium text-gray-700">
                  Target URL *
                </label>
                <div className="mt-1 flex rounded-md shadow-sm">
                  <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                    <Globe className="w-4 h-4" />
                  </span>
                  <input
                    {...register('url', { 
                      required: 'URL is required',
                      pattern: {
                        value: /^https?:\/\/.+/,
                        message: 'Please enter a valid URL starting with http:// or https://'
                      }
                    })}
                    type="url"
                    className="flex-1 block w-full border-gray-300 rounded-none rounded-r-md focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="https://example.com/page-to-scrape"
                  />
                </div>
                {errors.url && (
                  <p className="mt-2 text-sm text-red-600">{errors.url.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="priority" className="block text-sm font-medium text-gray-700">
                    Priority
                  </label>
                  <select
                    {...register('priority')}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="scheduled_at" className="block text-sm font-medium text-gray-700">
                    Schedule (Optional)
                  </label>
                  <div className="mt-1 flex rounded-md shadow-sm">
                    <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                      <Clock className="w-4 h-4" />
                    </span>
                    <input
                      {...register('scheduled_at')}
                      type="datetime-local"
                      className="flex-1 block w-full border-gray-300 rounded-none rounded-r-md focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Selectors Configuration */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-medium text-gray-900">CSS Selectors</h2>
              <button
                type="button"
                onClick={addSelector}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-primary-700 bg-primary-100 hover:bg-primary-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Selector
              </button>
            </div>

            <div className="space-y-4">
              {selectors.map((selector, index) => (
                <div key={index} className="flex items-start space-x-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700">
                      Field Name
                    </label>
                    <input
                      type="text"
                      value={selector.name}
                      onChange={(e) => updateSelector(index, 'name', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="e.g., title, price, description"
                    />
                  </div>
                  
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700">
                      CSS Selector
                    </label>
                    <input
                      type="text"
                      value={selector.selector}
                      onChange={(e) => updateSelector(index, 'selector', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="e.g., .product-title, #price, [data-testid='description']"
                    />
                  </div>
                  
                  {selectors.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeSelector(index)}
                      className="mt-6 p-2 text-red-600 hover:text-red-800 focus:outline-none"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-4 p-4 bg-blue-50 rounded-md">
              <div className="flex">
                <Info className="w-5 h-5 text-blue-400 mr-2" />
                <div className="text-sm text-blue-700">
                  <p className="font-medium">CSS Selector Tips:</p>
                  <ul className="mt-1 list-disc list-inside space-y-1">
                    <li>Use class selectors: <code className="bg-blue-100 px-1 rounded">.product-title</code></li>
                    <li>Use ID selectors: <code className="bg-blue-100 px-1 rounded">#main-content</code></li>
                    <li>Use attribute selectors: <code className="bg-blue-100 px-1 rounded">[data-testid="price"]</code></li>
                    <li>Combine selectors: <code className="bg-blue-100 px-1 rounded">.product .title h2</code></li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-6 flex items-center">
              <Settings className="w-5 h-5 mr-2" />
              Advanced Options
            </h2>
            
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label htmlFor="wait_for" className="block text-sm font-medium text-gray-700">
                    Wait for Element (CSS Selector)
                  </label>
                  <input
                    {...register('wait_for')}
                    type="text"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="e.g., .content-loaded"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Wait for this element to appear before extracting data
                  </p>
                </div>

                <div>
                  <label htmlFor="timeout" className="block text-sm font-medium text-gray-700">
                    Timeout (milliseconds)
                  </label>
                  <input
                    {...register('timeout', { 
                      min: { value: 5000, message: 'Minimum timeout is 5000ms' },
                      max: { value: 120000, message: 'Maximum timeout is 120000ms' }
                    })}
                    type="number"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="30000"
                  />
                  {errors.timeout && (
                    <p className="mt-1 text-xs text-red-600">{errors.timeout.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="wait_time" className="block text-sm font-medium text-gray-700">
                    Wait Time (milliseconds)
                  </label>
                  <input
                    {...register('wait_time', { 
                      min: { value: 0, message: 'Wait time cannot be negative' },
                      max: { value: 30000, message: 'Maximum wait time is 30000ms' }
                    })}
                    type="number"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="2000"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Additional wait time after page load
                  </p>
                  {errors.wait_time && (
                    <p className="mt-1 text-xs text-red-600">{errors.wait_time.message}</p>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    {...register('screenshot')}
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 block text-sm text-gray-700">
                    Take screenshot
                  </label>
                </div>

                <div className="flex items-center">
                  <input
                    {...register('pdf')}
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 block text-sm text-gray-700">
                    Generate PDF
                  </label>
                </div>

                <div className="flex items-center">
                  <input
                    {...register('scroll_to_bottom')}
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 block text-sm text-gray-700">
                    Scroll to bottom before extracting
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="flex items-center justify-end space-x-4">
            <Link
              href="/tasks"
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Cancel
            </Link>
            
            <button
              type="submit"
              disabled={isSubmitting || !canCreateTask()}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
                  Creating Task...
                </>
              ) : (
                'Create Task'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateTaskPage;