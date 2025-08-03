import React from 'react';
import { 
  Clock, 
  Play, 
  CheckCircle, 
  XCircle, 
  StopCircle,
  AlertTriangle,
  Loader
} from 'lucide-react';
import { Task } from '../types/api';

interface TaskStatusProps {
  status: Task['status'];
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showText?: boolean;
  className?: string;
}

const TaskStatus: React.FC<TaskStatusProps> = ({
  status,
  size = 'md',
  showIcon = true,
  showText = true,
  className = '',
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'pending':
        return {
          icon: Clock,
          text: 'Pending',
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-100',
          borderColor: 'border-yellow-200',
          dotColor: 'bg-yellow-500',
        };
      case 'queued':
        return {
          icon: Clock,
          text: 'Queued',
          color: 'text-orange-600',
          bgColor: 'bg-orange-100',
          borderColor: 'border-orange-200',
          dotColor: 'bg-orange-500',
        };
      case 'running':
        return {
          icon: Loader,
          text: 'Running',
          color: 'text-blue-600',
          bgColor: 'bg-blue-100',
          borderColor: 'border-blue-200',
          dotColor: 'bg-blue-500',
          animate: true,
        };
      case 'completed':
        return {
          icon: CheckCircle,
          text: 'Completed',
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          borderColor: 'border-green-200',
          dotColor: 'bg-green-500',
        };
      case 'failed':
        return {
          icon: XCircle,
          text: 'Failed',
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          borderColor: 'border-red-200',
          dotColor: 'bg-red-500',
        };
      case 'cancelled':
        return {
          icon: StopCircle,
          text: 'Cancelled',
          color: 'text-gray-600',
          bgColor: 'bg-gray-100',
          borderColor: 'border-gray-200',
          dotColor: 'bg-gray-500',
        };
      default:
        return {
          icon: AlertTriangle,
          text: 'Unknown',
          color: 'text-gray-600',
          bgColor: 'bg-gray-100',
          borderColor: 'border-gray-200',
          dotColor: 'bg-gray-500',
        };
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return {
          container: 'px-2 py-1 text-xs',
          icon: 'w-3 h-3',
          text: 'text-xs',
          dot: 'w-2 h-2',
        };
      case 'lg':
        return {
          container: 'px-4 py-2 text-base',
          icon: 'w-6 h-6',
          text: 'text-base',
          dot: 'w-4 h-4',
        };
      default: // md
        return {
          container: 'px-3 py-1.5 text-sm',
          icon: 'w-4 h-4',
          text: 'text-sm',
          dot: 'w-3 h-3',
        };
    }
  };

  const config = getStatusConfig();
  const sizeClasses = getSizeClasses();
  const Icon = config.icon;

  return (
    <span
      className={`
        inline-flex items-center rounded-full border font-medium
        ${config.color} ${config.bgColor} ${config.borderColor}
        ${sizeClasses.container}
        ${className}
      `}
    >
      {showIcon && (
        <Icon
          className={`
            ${sizeClasses.icon}
            ${showText ? 'mr-1.5' : ''}
            ${config.animate ? 'animate-spin' : ''}
          `}
        />
      )}
      {showText && (
        <span className={sizeClasses.text}>
          {config.text}
        </span>
      )}
    </span>
  );
};

// Dot variant for minimal display
interface TaskStatusDotProps {
  status: Task['status'];
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showTooltip?: boolean;
}

export const TaskStatusDot: React.FC<TaskStatusDotProps> = ({
  status,
  size = 'md',
  className = '',
  showTooltip = true,
}) => {
  const config = getStatusConfig(status);
  const sizeClasses = getSizeClasses(size);

  return (
    <div className={`relative ${className}`}>
      <div
        className={`
          rounded-full border-2 border-white shadow-sm
          ${config.dotColor}
          ${sizeClasses.dot}
          ${config.animate ? 'animate-pulse' : ''}
        `}
        title={showTooltip ? config.text : undefined}
      />
    </div>
  );
};

// Progress bar variant for detailed status
interface TaskStatusProgressProps {
  status: Task['status'];
  progress?: number;
  startTime?: string;
  className?: string;
}

export const TaskStatusProgress: React.FC<TaskStatusProgressProps> = ({
  status,
  progress = 0,
  startTime,
  className = '',
}) => {
  const config = getStatusConfig(status);
  
  const getElapsedTime = () => {
    if (!startTime) return null;
    const start = new Date(startTime);
    const now = new Date();
    const elapsed = Math.floor((now.getTime() - start.getTime()) / 1000);
    
    if (elapsed < 60) return `${elapsed}s`;
    if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`;
    return `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m`;
  };

  const elapsedTime = getElapsedTime();

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
        <TaskStatus status={status} size="sm" />
        {elapsedTime && (
          <span className="text-xs text-gray-500">
            {elapsedTime}
          </span>
        )}
      </div>
      
      {status === 'running' && (
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${config.dotColor}`}
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </div>
  );
};

// Helper function used by other components
const getStatusConfig = (status: Task['status']) => {
  switch (status) {
    case 'pending':
      return {
        icon: Clock,
        text: 'Pending',
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-100',
        borderColor: 'border-yellow-200',
        dotColor: 'bg-yellow-500',
      };
    case 'queued':
      return {
        icon: Clock,
        text: 'Queued',
        color: 'text-orange-600',
        bgColor: 'bg-orange-100',
        borderColor: 'border-orange-200',
        dotColor: 'bg-orange-500',
      };
    case 'running':
      return {
        icon: Loader,
        text: 'Running',
        color: 'text-blue-600',
        bgColor: 'bg-blue-100',
        borderColor: 'border-blue-200',
        dotColor: 'bg-blue-500',
        animate: true,
      };
    case 'completed':
      return {
        icon: CheckCircle,
        text: 'Completed',
        color: 'text-green-600',
        bgColor: 'bg-green-100',
        borderColor: 'border-green-200',
        dotColor: 'bg-green-500',
      };
    case 'failed':
      return {
        icon: XCircle,
        text: 'Failed',
        color: 'text-red-600',
        bgColor: 'bg-red-100',
        borderColor: 'border-red-200',
        dotColor: 'bg-red-500',
      };
    case 'cancelled':
      return {
        icon: StopCircle,
        text: 'Cancelled',
        color: 'text-gray-600',
        bgColor: 'bg-gray-100',
        borderColor: 'border-gray-200',
        dotColor: 'bg-gray-500',
      };
    default:
      return {
        icon: AlertTriangle,
        text: 'Unknown',
        color: 'text-gray-600',
        bgColor: 'bg-gray-100',
        borderColor: 'border-gray-200',
        dotColor: 'bg-gray-500',
      };
  }
};

const getSizeClasses = (size: 'sm' | 'md' | 'lg') => {
  switch (size) {
    case 'sm':
      return {
        container: 'px-2 py-1 text-xs',
        icon: 'w-3 h-3',
        text: 'text-xs',
        dot: 'w-2 h-2',
      };
    case 'lg':
      return {
        container: 'px-4 py-2 text-base',
        icon: 'w-6 h-6',
        text: 'text-base',
        dot: 'w-4 h-4',
      };
    default: // md
      return {
        container: 'px-3 py-1.5 text-sm',
        icon: 'w-4 h-4',
        text: 'text-sm',
        dot: 'w-3 h-3',
      };
  }
};

export default TaskStatus;