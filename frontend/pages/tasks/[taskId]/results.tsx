import React, { useState, useMemo } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from 'react-query';
import { useAuth } from '../../../lib/auth';
import api from '../../../lib/api';
import Navbar from '../../../components/Navbar';
import { Task, ApiError } from '../../../types/api';
import { 
  ArrowLeft, 
  Download, 
  Search, 
  Filter, 
  Table, 
  Grid, 
  RefreshCw,
  Eye,
  EyeOff,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  FileText,
  BarChart3
} from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';

const TaskResultsPage: React.FC = () => {
  const router = useRouter();
  const { taskId } = router.query;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

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
  } = useQuery<Task, ApiError>(
    ['task', taskId, refreshKey],
    () => api.getTask(taskId as string),
    {
      enabled: isAuthenticated && !!taskId,
      refetchOnWindowFocus: true,
    }
  );

  // Process results data
  const { processedResults, availableFields, totalItems } = useMemo(() => {
    if (!task?.result || !Array.isArray(task.result)) {
      return { processedResults: [], availableFields: [], totalItems: 0 };
    }

    // Extract available fields from first item
    const fields = task.result.length > 0 ? Object.keys(task.result[0]) : [];
    
    // Filter results based on search term
    const filtered = task.result.filter((item: any) => {
      if (!searchTerm) return true;
      
      return Object.values(item).some((value: any) =>
        String(value).toLowerCase().includes(searchTerm.toLowerCase())
      );
    });

    // Paginate results
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginated = filtered.slice(startIndex, endIndex);

    return {
      processedResults: paginated,
      availableFields: fields,
      totalItems: filtered.length,
    };
  }, [task?.result, searchTerm, currentPage, itemsPerPage]);

  // Initialize selected fields when available fields change
  React.useEffect(() => {
    if (availableFields.length > 0 && selectedFields.length === 0) {
      setSelectedFields(availableFields);
    }
  }, [availableFields, selectedFields.length]);

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

  const handleFieldToggle = (field: string) => {
    setSelectedFields(prev => 
      prev.includes(field) 
        ? prev.filter(f => f !== field)
        : [...prev, field]
    );
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
    toast.success('Results refreshed');
  };

  const renderTableView = () => {
    const visibleFields = selectedFields.length > 0 ? selectedFields : availableFields;

    return (
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {visibleFields.map((field) => (
                  <th
                    key={field}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {field}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processedResults.map((item: any, index: number) => (
                <tr key={index} className="hover:bg-gray-50">
                  {visibleFields.map((field) => (
                    <td key={field} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div className="max-w-xs truncate" title={String(item[field] || '')}>
                        {item[field] || '-'}
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderGridView = () => {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {processedResults.map((item: any, index: number) => (
          <div key={index} className="bg-white shadow rounded-lg p-6">
            <div className="space-y-3">
              {selectedFields.length > 0 ? selectedFields : availableFields.map((field) => (
                <div key={field}>
                  <dt className="text-sm font-medium text-gray-500">{field}</dt>
                  <dd className="mt-1 text-sm text-gray-900 break-words">
                    {item[field] || '-'}
                  </dd>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderPagination = () => {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    
    if (totalPages <= 1) return null;

    return (
      <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
        <div className="flex-1 flex justify-between sm:hidden">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
        <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-700">
              Showing <span className="font-medium">{(currentPage - 1) * itemsPerPage + 1}</span> to{' '}
              <span className="font-medium">
                {Math.min(currentPage * itemsPerPage, totalItems)}
              </span>{' '}
              of <span className="font-medium">{totalItems}</span> results
            </p>
          </div>
          <div>
            <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const page = i + 1;
                return (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                      page === currentPage
                        ? 'z-10 bg-primary-50 border-primary-500 text-primary-600'
                        : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    {page}
                  </button>
                );
              })}
              
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </nav>
          </div>
        </div>
      </div>
    );
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

  if (task.status !== 'completed' || !task.result) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-6">
            <div className="flex">
              <AlertCircle className="w-5 h-5 text-yellow-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-yellow-800">No results available</h3>
                <p className="mt-2 text-sm text-yellow-700">
                  This task has not completed yet or has no results to display.
                </p>
                <div className="mt-4">
                  <Link
                    href={`/tasks/${task.id}`}
                    className="text-sm bg-yellow-100 text-yellow-800 rounded-md px-3 py-1.5 font-medium hover:bg-yellow-200"
                  >
                    View Task Details
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <Link
              href={`/tasks/${task.id}`}
              className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back to Task
            </Link>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Results: {task.name}</h1>
              <p className="text-gray-600 mt-1">
                Extracted data from {task.url}
              </p>
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
              
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => handleDownload('json')}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-l-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Download className="w-4 h-4 mr-1" />
                  JSON
                </button>
                <button
                  onClick={() => handleDownload('csv')}
                  className="inline-flex items-center px-3 py-2 border-t border-b border-gray-300 shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  CSV
                </button>
                <button
                  onClick={() => handleDownload('xlsx')}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-r-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Excel
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <FileText className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Records</dt>
                    <dd className="text-lg font-medium text-gray-900">{totalItems}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <BarChart3 className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Fields</dt>
                    <dd className="text-lg font-medium text-gray-900">{availableFields.length}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Filter className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Filtered</dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {searchTerm ? `${totalItems} of ${task.result.length}` : 'None'}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Eye className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Visible Fields</dt>
                    <dd className="text-lg font-medium text-gray-900">{selectedFields.length}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
            <div className="flex items-center space-x-4">
              {/* Search */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search results..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                />
              </div>

              {/* Items per page */}
              <select
                value={itemsPerPage}
                onChange={(e) => {
                  setItemsPerPage(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span className="text-sm text-gray-500">per page</span>
            </div>

            <div className="flex items-center space-x-4">
              {/* View mode toggle */}
              <div className="flex rounded-md shadow-sm">
                <button
                  onClick={() => setViewMode('table')}
                  className={`relative inline-flex items-center px-3 py-2 rounded-l-md border text-sm font-medium ${
                    viewMode === 'table'
                      ? 'bg-primary-50 border-primary-500 text-primary-700'
                      : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  <Table className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`relative inline-flex items-center px-3 py-2 rounded-r-md border text-sm font-medium ${
                    viewMode === 'grid'
                      ? 'bg-primary-50 border-primary-500 text-primary-700'
                      : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  <Grid className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Field selector */}
          {availableFields.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Visible Fields</h4>
              <div className="flex flex-wrap gap-2">
                {availableFields.map((field) => (
                  <button
                    key={field}
                    onClick={() => handleFieldToggle(field)}
                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                      selectedFields.includes(field)
                        ? 'bg-primary-100 text-primary-800'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {selectedFields.includes(field) ? (
                      <Eye className="w-3 h-3 mr-1" />
                    ) : (
                      <EyeOff className="w-3 h-3 mr-1" />
                    )}
                    {field}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Results */}
        {processedResults.length > 0 ? (
          <div className="space-y-6">
            {viewMode === 'table' ? renderTableView() : renderGridView()}
            {renderPagination()}
          </div>
        ) : (
          <div className="text-center py-12">
            <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm ? 'Try adjusting your search terms.' : 'This task has no data to display.'}
            </p>
            {searchTerm && (
              <div className="mt-6">
                <button
                  onClick={() => setSearchTerm('')}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                >
                  Clear search
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskResultsPage;