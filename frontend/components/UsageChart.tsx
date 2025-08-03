import React from 'react';

interface UsageData {
  period: string;
  start_date: string;
  end_date: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  compute_units_consumed: number;
  compute_units_limit: number;
}

interface UsageChartProps {
  data: UsageData;
}

const UsageChart: React.FC<UsageChartProps> = ({ data }) => {
  const successRate = (data.total_tasks || 0) > 0 ? ((data.completed_tasks || 0) / (data.total_tasks || 0)) * 100 : 0;
  const usagePercentage = (data.compute_units_limit || 0) > 0 ? ((data.compute_units_consumed || 0) / (data.compute_units_limit || 0)) * 100 : 0;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const getUsageColor = (percentage: number) => {
    if (percentage <= 50) return 'bg-green-500';
    if (percentage <= 80) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getSuccessColor = (rate: number) => {
    if (rate >= 90) return 'text-green-600';
    if (rate >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div>
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">
          Usage Period: {formatDate(data.start_date)} - {formatDate(data.end_date)}
        </h4>
      </div>

      {/* Usage Statistics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">{data.total_tasks}</div>
          <div className="text-xs text-gray-600">Total Tasks</div>
        </div>
        
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-green-600">{data.completed_tasks}</div>
          <div className="text-xs text-gray-600">Completed</div>
        </div>
        
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-red-600">{data.failed_tasks}</div>
          <div className="text-xs text-gray-600">Failed</div>
        </div>
        
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className={`text-2xl font-bold ${getSuccessColor(successRate)}`}>
            {(successRate || 0).toFixed(1)}%
          </div>
          <div className="text-xs text-gray-600">Success Rate</div>
        </div>
      </div>

      {/* Compute Units Usage Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Compute Units Usage</span>
          <span className="text-sm text-gray-500">
            {data.compute_units_consumed || 0} / {data.compute_units_limit || 0} ({(usagePercentage || 0).toFixed(1)}%)
          </span>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-300 ${getUsageColor(usagePercentage)}`}
            style={{ width: `${Math.min(usagePercentage, 100)}%` }}
          ></div>
        </div>
        
        {usagePercentage > 100 && (
          <p className="text-xs text-red-600 mt-1">
            Usage exceeded limit by {((usagePercentage || 0) - 100).toFixed(1)}%
          </p>
        )}
      </div>

      {/* Task Status Breakdown */}
      {data.total_tasks > 0 && (
        <div>
          <h5 className="text-sm font-medium text-gray-900 mb-3">Task Status Breakdown</h5>
          <div className="space-y-2">
            {/* Completed Tasks Bar */}
            <div>
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Completed</span>
                <span>{data.completed_tasks || 0} tasks</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${(data.completed_tasks / data.total_tasks) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Failed Tasks Bar */}
            {data.failed_tasks > 0 && (
              <div>
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>Failed</span>
                  <span>{data.failed_tasks || 0} tasks</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-red-500 h-2 rounded-full"
                    style={{ width: `${(data.failed_tasks / data.total_tasks) * 100}%` }}
                  ></div>
                </div>
              </div>
            )}

            {/* Pending/Other Tasks */}
            {(data.total_tasks - data.completed_tasks - data.failed_tasks) > 0 && (
              <div>
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>Other</span>
                  <span>{data.total_tasks - data.completed_tasks - data.failed_tasks} tasks</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full"
                    style={{ 
                      width: `${((data.total_tasks - data.completed_tasks - data.failed_tasks) / data.total_tasks) * 100}%` 
                    }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Usage Recommendations */}
      {usagePercentage > 80 && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-start">
            <div className="text-yellow-600 text-sm">
              <strong>High Usage Warning:</strong> You've used {(usagePercentage || 0).toFixed(1)}% of your monthly compute units.
              {usagePercentage > 100 ? (
                <span className="block mt-1">
                  Consider upgrading your plan to avoid overage charges.
                </span>
              ) : (
                <span className="block mt-1">
                  Consider upgrading your plan if you need more compute units.
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* No Usage Message */}
      {data.total_tasks === 0 && (
        <div className="text-center py-8">
          <div className="text-gray-400 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-gray-500 text-sm">No tasks executed in this period</p>
          <p className="text-gray-400 text-xs">Start creating tasks to see your usage analytics</p>
        </div>
      )}
    </div>
  );
};

export default UsageChart;