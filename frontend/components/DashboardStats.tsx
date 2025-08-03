import React from 'react';
import { 
  FileText, 
  CheckCircle, 
  XCircle, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  Activity,
  Zap
} from 'lucide-react';
import { DashboardStats as DashboardStatsType } from '../types/api';

interface DashboardStatsProps {
  stats: DashboardStatsType;
  isLoading?: boolean;
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<any>;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color: string;
  bgColor: string;
  isLoading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon: Icon,
  trend,
  color,
  bgColor,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="flex items-center">
            <div className={`p-2 rounded-lg ${bgColor}`}>
              <div className="w-6 h-6 bg-gray-300 rounded"></div>
            </div>
            <div className="ml-4 flex-1">
              <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-300 rounded w-1/2"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const formatValue = (val: string | number): string => {
    const numVal = Number(val) || 0;
    if (numVal >= 1000000) {
      return `${(numVal / 1000000).toFixed(1)}M`;
    }
    if (numVal >= 1000) {
      return `${(numVal / 1000).toFixed(1)}K`;
    }
    return numVal.toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center">
        <div className={`p-2 rounded-lg ${bgColor}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatValue(value)}
          </p>
          {trend && (
            <div className="flex items-center mt-1">
              {trend.isPositive ? (
                <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
              )}
              <span
                className={`text-xs font-medium ${
                  trend.isPositive ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {Math.abs(trend.value)}%
              </span>
              <span className="text-xs text-gray-500 ml-1">vs last month</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const DashboardStats: React.FC<DashboardStatsProps> = ({ stats, isLoading = false }) => {
  // Ensure all stats have default values to prevent undefined errors
  const safeStats = {
    total_tasks: stats.total_tasks || 0,
    completed_tasks: stats.completed_tasks || 0,
    failed_tasks: stats.failed_tasks || 0,
    pending_tasks: stats.pending_tasks || 0,
    api_calls_used: stats.api_calls_used || 0,
    api_calls_limit: stats.api_calls_limit || 0,
    success_rate: stats.success_rate || 0,
    avg_execution_time: stats.avg_execution_time || 0,
  };

  const successRate = safeStats.total_tasks > 0
    ? ((Number(safeStats.completed_tasks) || 0) / (Number(safeStats.total_tasks) || 1) * 100).toFixed(1)
    : '0';

  const formatExecutionTime = (seconds: number): string => {
    const safeSeconds = Number(seconds) || 0;
    if (safeSeconds < 60) return `${safeSeconds.toFixed(1)}s`;
    if (safeSeconds < 3600) return `${(safeSeconds / 60).toFixed(1)}m`;
    return `${(safeSeconds / 3600).toFixed(1)}h`;
  };

  const getUsagePercentage = (): number => {
    const limit = Number(safeStats.api_calls_limit) || 0;
    const used = Number(safeStats.api_calls_used) || 0;
    if (limit === 0) return 0;
    return Math.min(100, (used / limit) * 100);
  };

  const usagePercentage = getUsagePercentage();
  const remainingCalls = (Number(safeStats.api_calls_limit) || 0) - (Number(safeStats.api_calls_used) || 0);

  const statCards = [
    {
      title: 'Total Tasks',
      value: safeStats.total_tasks,
      icon: FileText,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      trend: {
        value: 12.5,
        isPositive: true,
      },
    },
    {
      title: 'Completed',
      value: safeStats.completed_tasks,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      trend: {
        value: 8.2,
        isPositive: true,
      },
    },
    {
      title: 'Failed',
      value: safeStats.failed_tasks,
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
      trend: {
        value: 2.1,
        isPositive: false,
      },
    },
    {
      title: 'Pending',
      value: safeStats.pending_tasks,
      icon: Clock,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <StatCard
            key={index}
            title={stat.title}
            value={stat.value}
            icon={stat.icon}
            trend={stat.trend}
            color={stat.color}
            bgColor={stat.bgColor}
            isLoading={isLoading}
          />
        ))}
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Success Rate */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {isLoading ? (
            <div className="animate-pulse">
              <div className="h-4 bg-gray-300 rounded w-3/4 mb-4"></div>
              <div className="h-8 bg-gray-300 rounded w-1/2 mb-4"></div>
              <div className="h-2 bg-gray-300 rounded"></div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-600">Success Rate</h3>
                <Activity className="w-5 h-5 text-gray-400" />
              </div>
              <div className="text-2xl font-bold text-gray-900 mb-2">
                {successRate}%
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full transition-all"
                  style={{ width: `${successRate}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2">
                {safeStats.completed_tasks} of {safeStats.total_tasks} tasks completed
              </p>
            </>
          )}
        </div>

        {/* API Usage */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {isLoading ? (
            <div className="animate-pulse">
              <div className="h-4 bg-gray-300 rounded w-3/4 mb-4"></div>
              <div className="h-8 bg-gray-300 rounded w-1/2 mb-4"></div>
              <div className="h-2 bg-gray-300 rounded"></div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-600">API Usage</h3>
                <Zap className="w-5 h-5 text-gray-400" />
              </div>
              <div className="text-2xl font-bold text-gray-900 mb-2">
                {(Number(safeStats.api_calls_used) || 0).toLocaleString()}
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    usagePercentage >= 90
                      ? 'bg-red-500'
                      : usagePercentage >= 75
                      ? 'bg-yellow-500'
                      : 'bg-blue-500'
                  }`}
                  style={{ width: `${usagePercentage}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2">
                {(Number(remainingCalls) || 0).toLocaleString()} of {(Number(safeStats.api_calls_limit) || 0).toLocaleString()} remaining
              </p>
            </>
          )}
        </div>

        {/* Avg Execution Time */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {isLoading ? (
            <div className="animate-pulse">
              <div className="h-4 bg-gray-300 rounded w-3/4 mb-4"></div>
              <div className="h-8 bg-gray-300 rounded w-1/2"></div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-600">Avg Execution Time</h3>
                <Clock className="w-5 h-5 text-gray-400" />
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {formatExecutionTime(safeStats.avg_execution_time)}
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Per task completion
              </p>
            </>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors">
            <FileText className="w-4 h-4 mr-2" />
            Create New Task
          </button>
          <button className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors">
            <Activity className="w-4 h-4 mr-2" />
            View Analytics
          </button>
          <button className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors">
            <Zap className="w-4 h-4 mr-2" />
            Manage API Keys
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardStats;