import React, { useState, useEffect } from 'react';
import { GetServerSideProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  CreditCardIcon, 
  ClockIcon, 
  CalendarIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowUpIcon,
  CogIcon
} from '@heroicons/react/24/outline';

import { withAuth } from '../lib/auth';
import apiClient, { Invoice } from '../lib/api';
import Navbar from '../components/Navbar';
import SubscriptionCard from '../components/SubscriptionCard';
import UsageChart from '../components/UsageChart';

interface BillingData {
  plan: {
    id: string;
    name: string;
    price_cents: number;
    monthly_compute_units: number;
    max_concurrent_tasks: number;
  };
  subscription: {
    id: string;
    status: string;
    current_period_start: string;
    current_period_end: string;
    cancel_at_period_end: boolean;
    days_until_renewal: number;
  } | null;
  compute_units_remaining: number;
  compute_units_reset_date: string;
  can_upgrade: boolean;
  portal_url: string | null;
}

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

const BillingPage: React.FC = () => {
  const router = useRouter();
  const [billingData, setBillingData] = useState<BillingData | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [usageData, setUsageData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [invoicesLoading, setInvoicesLoading] = useState(true);
  const [usageLoading, setUsageLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [invoicesError, setInvoicesError] = useState<string | null>(null);
  const [usageError, setUsageError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    
    // Load billing data first as it's most critical
    await fetchBillingData();
    
    // Load other data in parallel
    await Promise.allSettled([
      fetchInvoices(),
      fetchUsageData()
    ]);
  };

  const fetchBillingData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    
    try {
      const data = await apiClient.getSubscription();
      setBillingData(data as any);
      setRetryCount(0); // Reset retry count on success
    } catch (err: any) {
      console.error('Failed to fetch billing data:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Failed to load billing information';
      setError(errorMessage);
      
      // Auto-retry on network errors
      if (retryCount < 3 && (err.code === 'NETWORK_ERROR' || err.response?.status >= 500)) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchBillingData(false);
        }, 2000 * (retryCount + 1)); // Exponential backoff
      }
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const fetchInvoices = async () => {
    setInvoicesLoading(true);
    setInvoicesError(null);
    
    try {
      const data = await apiClient.getInvoices();
      setInvoices(data);
    } catch (err: any) {
      console.error('Failed to fetch invoices:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Failed to load invoice history';
      setInvoicesError(errorMessage);
    } finally {
      setInvoicesLoading(false);
    }
  };

  const fetchUsageData = async () => {
    setUsageLoading(true);
    setUsageError(null);
    
    try {
      const data = await apiClient.getUsage({ granularity: 'month' });
      setUsageData(data as any);
    } catch (err: any) {
      console.error('Failed to fetch usage data:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Failed to load usage statistics';
      setUsageError(errorMessage);
    } finally {
      setUsageLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will retain access until the end of your current billing period.')) {
      return;
    }

    setActionLoading('cancel');
    try {
      await apiClient.cancelSubscription();
      await fetchBillingData(false); // Refresh data without full page loading
      
      // Show success message
      const alertDiv = document.createElement('div');
      alertDiv.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded z-50';
      alertDiv.innerHTML = 'Subscription cancellation initiated. You will retain access until the end of your current billing period.';
      document.body.appendChild(alertDiv);
      setTimeout(() => document.body.removeChild(alertDiv), 5000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Unknown error';
      
      // Show error message
      const alertDiv = document.createElement('div');
      alertDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
      alertDiv.innerHTML = `Failed to cancel subscription: ${errorMessage}`;
      document.body.appendChild(alertDiv);
      setTimeout(() => document.body.removeChild(alertDiv), 5000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleResumeSubscription = async () => {
    setActionLoading('resume');
    try {
      await apiClient.resumeSubscription();
      await fetchBillingData(false); // Refresh data without full page loading
      
      // Show success message
      const alertDiv = document.createElement('div');
      alertDiv.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded z-50';
      alertDiv.innerHTML = 'Subscription resumed successfully!';
      document.body.appendChild(alertDiv);
      setTimeout(() => document.body.removeChild(alertDiv), 5000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Unknown error';
      
      // Show error message
      const alertDiv = document.createElement('div');
      alertDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
      alertDiv.innerHTML = `Failed to resume subscription: ${errorMessage}`;
      document.body.appendChild(alertDiv);
      setTimeout(() => document.body.removeChild(alertDiv), 5000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleManageBilling = async () => {
    if (!billingData?.portal_url) {
      setActionLoading('portal');
      try {
        const { portal_url } = await apiClient.createPortalSession();
        window.open(portal_url, '_blank');
      } catch (err: any) {
        const errorMessage = err.response?.data?.message || err.message || 'Unknown error';
        
        // Show error message
        const alertDiv = document.createElement('div');
        alertDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
        alertDiv.innerHTML = `Failed to open customer portal: ${errorMessage}`;
        document.body.appendChild(alertDiv);
        setTimeout(() => document.body.removeChild(alertDiv), 5000);
      } finally {
        setActionLoading(null);
      }
    } else {
      window.open(billingData.portal_url, '_blank');
    }
  };

  const formatPrice = (cents: number | null | undefined) => {
    return `$${((cents || 0) / 100).toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getUsagePercentage = () => {
    if (!billingData) return 0;
    const used = billingData.plan.monthly_compute_units - billingData.compute_units_remaining;
    return (used / billingData.plan.monthly_compute_units) * 100;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-100';
      case 'cancelled': return 'text-yellow-600 bg-yellow-100';
      case 'past_due': return 'text-red-600 bg-red-100';
      case 'expired': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading billing information...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !billingData) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto" />
            <p className="mt-4 text-gray-600">{error || 'Failed to load billing information'}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Billing & Subscription - Selextract Cloud</title>
        <meta name="description" content="Manage your Selextract Cloud subscription and billing" />
      </Head>

      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Billing & Subscription</h1>
          <p className="mt-2 text-gray-600">
            Manage your subscription, view usage, and update billing information.
          </p>
        </div>

        {/* Subscription Status Alert */}
        {billingData.subscription?.cancel_at_period_end && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500 mr-2" />
              <div className="flex-1">
                <p className="text-yellow-800">
                  Your subscription is set to cancel at the end of the current billing period on{' '}
                  {formatDate(billingData.subscription.current_period_end)}.
                </p>
              </div>
              <button
                onClick={handleResumeSubscription}
                disabled={actionLoading === 'resume'}
                className="ml-4 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
              >
                {actionLoading === 'resume' ? 'Resuming...' : 'Resume Subscription'}
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Current Plan */}
            <SubscriptionCard
              plan={billingData.plan}
              subscription={billingData.subscription}
              onCancel={handleCancelSubscription}
              onResume={handleResumeSubscription}
              actionLoading={actionLoading}
            />

            {/* Usage Statistics */}
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Usage Overview</h2>
                <ChartBarIcon className="h-6 w-6 text-gray-400" />
              </div>

              {/* Compute Units Usage */}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Compute Units</span>
                  <span className="text-sm text-gray-500">
                    {billingData.compute_units_remaining} / {billingData.plan.monthly_compute_units} remaining
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${Math.min(100 - getUsagePercentage(), 100)}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Resets on {formatDate(billingData.compute_units_reset_date)}
                </p>
              </div>

              {/* Usage Chart */}
              {usageData && <UsageChart data={usageData} />}
            </div>

            {/* Invoice History */}
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Invoice History</h2>
                <CalendarIcon className="h-6 w-6 text-gray-400" />
              </div>

              {invoicesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <span className="ml-3 text-gray-600">Loading invoices...</span>
                </div>
              ) : invoicesError ? (
                <div className="text-center py-8">
                  <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
                  <p className="text-red-600 mb-4">{invoicesError}</p>
                  <button
                    onClick={fetchInvoices}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                </div>
              ) : invoices.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Amount
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {invoices.map((invoice) => (
                        <tr key={invoice.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatDate(invoice.created_at)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatPrice(invoice.amount)} {invoice.currency.toUpperCase()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(invoice.status)}`}>
                              {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {invoice.receipt_url && (
                              <a
                                href={invoice.receipt_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-900 mr-4"
                              >
                                Receipt
                              </a>
                            )}
                            {invoice.invoice_url && (
                              <a
                                href={invoice.invoice_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-900"
                              >
                                Invoice
                              </a>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8">
                  <CalendarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No invoices yet</p>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
              <div className="space-y-3">
                {billingData.can_upgrade && (
                  <Link href="/billing/plans" className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
                    <ArrowUpIcon className="h-4 w-4 mr-2" />
                    Upgrade Plan
                  </Link>
                )}

                <button
                  onClick={handleManageBilling}
                  disabled={actionLoading === 'portal'}
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  <CogIcon className="h-4 w-4 mr-2" />
                  {actionLoading === 'portal' ? 'Loading...' : 'Manage Billing'}
                </button>

                <Link href="/billing/plans" className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                  <CreditCardIcon className="h-4 w-4 mr-2" />
                  View All Plans
                </Link>
              </div>
            </div>

            {/* Billing Summary */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Billing Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Current Plan</span>
                  <span className="text-sm font-medium text-gray-900">{billingData.plan.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Monthly Cost</span>
                  <span className="text-sm font-medium text-gray-900">
                    {formatPrice(billingData.plan.price_cents)}
                  </span>
                </div>
                {billingData.subscription && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Status</span>
                      <span className={`text-sm font-medium ${getStatusColor(billingData.subscription.status).replace('bg-', 'text-').replace('100', '600')}`}>
                        {billingData.subscription.status.charAt(0).toUpperCase() + billingData.subscription.status.slice(1)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Next Billing</span>
                      <span className="text-sm font-medium text-gray-900">
                        {formatDate(billingData.subscription.current_period_end)}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Support */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-lg font-medium text-blue-900 mb-2">Need Help?</h3>
              <p className="text-sm text-blue-700 mb-4">
                Contact our support team for billing questions or assistance.
              </p>
              <a
                href="mailto:support@selextract.com"
                className="text-sm font-medium text-blue-600 hover:text-blue-500"
              >
                support@selextract.com
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default withAuth(BillingPage);