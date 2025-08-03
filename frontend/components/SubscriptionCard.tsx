import React from 'react';
import {
  CreditCardIcon,
  CalendarIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  PauseIcon,
  BanknotesIcon
} from '@heroicons/react/24/outline';

interface Plan {
  id: string;
  name: string;
  price_cents: number;
  monthly_compute_units: number;
  max_concurrent_tasks: number;
}

interface Subscription {
  id: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  days_until_renewal?: number;
}

interface SubscriptionCardProps {
  plan: Plan;
  subscription: Subscription | null;
  onCancel: () => void;
  onResume: () => void;
  actionLoading: string | null;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  plan,
  subscription,
  onCancel,
  onResume,
  actionLoading
}) => {
  const formatPrice = (cents: number | null | undefined) => {
    return `$${((Number(cents) || 0) / 100).toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      active: {
        color: 'bg-green-100 text-green-800',
        icon: CheckCircleIcon,
        label: 'Active'
      },
      on_trial: {
        color: 'bg-blue-100 text-blue-800',
        icon: ClockIcon,
        label: 'Trial Period'
      },
      paused: {
        color: 'bg-yellow-100 text-yellow-800',
        icon: PauseIcon,
        label: 'Paused'
      },
      past_due: {
        color: 'bg-red-100 text-red-800',
        icon: XCircleIcon,
        label: 'Payment Overdue'
      },
      unpaid: {
        color: 'bg-red-100 text-red-800',
        icon: XCircleIcon,
        label: 'Unpaid'
      },
      cancelled: {
        color: 'bg-yellow-100 text-yellow-800',
        icon: ExclamationTriangleIcon,
        label: 'Cancelled'
      },
      expired: {
        color: 'bg-gray-100 text-gray-800',
        icon: XCircleIcon,
        label: 'Expired'
      }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.expired;
    const IconComponent = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        <IconComponent className="h-3 w-3 mr-1" />
        {config.label}
      </span>
    );
  };

  const getPlanFeatures = (planName: string) => {
    const features: Record<string, string[]> = {
      'Free': [
        '100 compute units/month',
        '1 concurrent task',
        'Community support',
        'Basic web scraping'
      ],
      'Basic': [
        '1,000 compute units/month',
        '3 concurrent tasks',
        'Email support',
        'Advanced selectors',
        'Data export (JSON, CSV)'
      ],
      'Pro': [
        '5,000 compute units/month',
        '10 concurrent tasks',
        'Priority support',
        'API access',
        'Webhook integrations',
        'Custom data formats'
      ],
      'Enterprise': [
        '25,000 compute units/month',
        '50 concurrent tasks',
        '24/7 phone support',
        'Dedicated account manager',
        'Custom integrations',
        'SLA guarantee'
      ]
    };

    return features[planName] || [
      `${(Number(plan.monthly_compute_units) || 0).toLocaleString()} compute units/month`,
      `${plan.max_concurrent_tasks || 0} concurrent tasks`,
      'Standard support'
    ];
  };

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <CreditCardIcon className="h-6 w-6 text-gray-400 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">Current Plan</h2>
        </div>
        {subscription && getStatusBadge(subscription.status)}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Plan Details */}
        <div>
          <div className="mb-4">
            <h3 className="text-2xl font-bold text-gray-900">{plan.name}</h3>
            <div className="flex items-baseline mt-1">
              <span className="text-3xl font-bold text-gray-900">
                {formatPrice(plan.price_cents)}
              </span>
              {plan.price_cents > 0 && (
                <span className="text-gray-500 ml-1">/month</span>
              )}
            </div>
          </div>

          {/* Plan Features */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Features included:</h4>
            <ul className="space-y-1">
              {getPlanFeatures(plan.name).map((feature, index) => (
                <li key={index} className="flex items-center text-sm text-gray-600">
                  <CheckCircleIcon className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Subscription Info */}
        <div>
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                {subscription ? 'Billing Information' : 'Plan Information'}
              </h4>
              <div className="space-y-2">
                {subscription ? (
                  <>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Current period:</span>
                      <span className="text-gray-900">
                        {formatDate(subscription.current_period_start)} - {formatDate(subscription.current_period_end)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Next billing:</span>
                      <span className="text-gray-900">
                        {subscription.cancel_at_period_end 
                          ? 'Subscription will end' 
                          : formatDate(subscription.current_period_end)
                        }
                      </span>
                    </div>
                    {subscription.days_until_renewal !== undefined && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Days remaining:</span>
                        <span className="text-gray-900">{subscription.days_until_renewal} days</span>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-sm text-gray-600">
                    <p>No active subscription found.</p>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Compute Units:</span>
                  <span className="text-gray-900">
                    {(Number(plan.monthly_compute_units) || 0).toLocaleString()} /month
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Concurrent Tasks:</span>
                  <span className="text-gray-900">{plan.max_concurrent_tasks}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      {subscription && (
        <div className="mt-6 flex flex-wrap gap-3">
          {subscription.cancel_at_period_end ? (
            <button
              onClick={onResume}
              disabled={actionLoading === 'resume'}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading === 'resume' ? 'Resuming...' : 'Resume Subscription'}
            </button>
          ) : subscription.status === 'active' ? (
            <button
              onClick={onCancel}
              disabled={actionLoading === 'cancel'}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading === 'cancel' ? 'Cancelling...' : 'Cancel Subscription'}
            </button>
          ) : subscription.status === 'paused' ? (
            <button
              onClick={onResume}
              disabled={actionLoading === 'resume'}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading === 'resume' ? 'Resuming...' : 'Resume Subscription'}
            </button>
          ) : (subscription.status === 'past_due' || subscription.status === 'unpaid') ? (
            <button
              onClick={() => window.open('https://app.lemonsqueezy.com/', '_blank')}
              className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 text-sm font-medium"
            >
              Update Payment Method
            </button>
          ) : null}
          
          {/* Manage Billing Button for active subscriptions */}
          {(subscription.status === 'active' || subscription.status === 'on_trial') && (
            <button
              onClick={() => window.open('https://app.lemonsqueezy.com/', '_blank')}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm font-medium"
            >
              Manage Billing
            </button>
          )}
        </div>
      )}

      {/* Warning for cancellation */}
      {subscription?.cancel_at_period_end && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                Subscription Cancellation Scheduled
              </h3>
              <div className="mt-2 text-sm text-yellow-700">
                <p>
                  Your subscription will end on {formatDate(subscription.current_period_end)}. 
                  You'll continue to have access to all features until then.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status-specific warnings and notices */}
      {subscription?.status === 'past_due' && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex">
            <XCircleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Payment Past Due
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>
                  Your payment is past due. Please update your payment method to continue using your subscription.
                  Your service may be suspended if payment isn't received soon.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {subscription?.status === 'unpaid' && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex">
            <BanknotesIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Payment Required
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>
                  Your subscription is unpaid. Please update your payment method immediately to restore access to your account.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {subscription?.status === 'paused' && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex">
            <PauseIcon className="h-5 w-5 text-yellow-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                Subscription Paused
              </h3>
              <div className="mt-2 text-sm text-yellow-700">
                <p>
                  Your subscription is currently paused. You can resume it at any time to regain full access to all features.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {subscription?.status === 'on_trial' && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex">
            <ClockIcon className="h-5 w-5 text-blue-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                Trial Period Active
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>
                  You're currently in your trial period. Enjoy full access to all features until {formatDate(subscription.current_period_end)}.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {subscription?.status === 'expired' && (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex">
            <XCircleIcon className="h-5 w-5 text-gray-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-gray-800">
                Subscription Expired
              </h3>
              <div className="mt-2 text-sm text-gray-700">
                <p>
                  Your subscription has expired. You're now on the free plan.
                  <a href="/billing/plans" className="ml-1 text-blue-600 hover:text-blue-500 underline">
                    Reactivate your subscription
                  </a> to regain access to premium features.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SubscriptionCard;