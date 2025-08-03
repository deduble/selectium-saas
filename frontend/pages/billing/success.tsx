import React, { useEffect, useState } from 'react';
import { GetServerSideProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  CheckCircleIcon,
  CreditCardIcon,
  ArrowRightIcon,
  StarIcon
} from '@heroicons/react/24/outline';

import { withAuth } from '../../lib/auth';
import apiClient from '../../lib/api';
import Navbar from '../../components/Navbar';

interface SuccessPageData {
  subscription?: {
    plan_name: string;
    plan_id: string;
    amount: number;
    currency: string;
    billing_interval: string;
    next_billing_date: string;
  };
  transaction?: {
    id: string;
    amount: number;
    currency: string;
  };
}

const PaymentSuccessPage: React.FC = () => {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [successData, setSuccessData] = useState<SuccessPageData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    // Get query parameters from URL
    const { subscription_id, transaction_id, plan_id, status } = router.query;
    
    // Add a delay to allow webhook processing to complete
    const fetchDelay = setTimeout(() => {
      if (subscription_id || transaction_id || plan_id) {
        fetchSuccessData(subscription_id as string, transaction_id as string, plan_id as string);
      } else {
        // If no params, show generic success
        setLoading(false);
      }
    }, 2000); // 2 second delay to allow webhook processing

    return () => clearTimeout(fetchDelay);
  }, [router.query]);

  const fetchSuccessData = async (subscriptionId?: string, transactionId?: string, planId?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch the current subscription info with retries for webhook processing
      const data = await apiClient.getSubscription() as any;
      
      // If we have a plan_id from URL but subscription doesn't match, retry
      if (planId && data.plan?.id !== planId && retryCount < 5) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchSuccessData(subscriptionId, transactionId, planId);
        }, 3000); // Wait 3 seconds before retry
        return;
      }
      
      setSuccessData({
        subscription: {
          plan_name: data.plan?.name || 'Unknown Plan',
          plan_id: data.plan?.id || planId || 'free',
          amount: (data.plan?.price_cents || data.plan?.price || 0) / 100,
          currency: data.plan?.currency || 'USD',
          billing_interval: data.plan?.billing_interval || 'monthly',
          next_billing_date: data.subscription?.current_period_end || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
        },
        transaction: transactionId ? {
          id: transactionId,
          amount: (data.plan?.price_cents || data.plan?.price || 0) / 100,
          currency: data.plan?.currency || 'USD'
        } : undefined
      });
      setRetryCount(0); // Reset retry count on success
    } catch (err: any) {
      console.error('Failed to fetch success data:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Unable to load subscription details';
      setError(errorMessage);
      
      // Auto-retry on certain errors
      if (retryCount < 3 && (err.response?.status === 404 || err.response?.status >= 500)) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchSuccessData(subscriptionId, transactionId, planId);
        }, 2000 * (retryCount + 1)); // Exponential backoff
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    const { subscription_id, transaction_id, plan_id } = router.query;
    setRetryCount(0);
    fetchSuccessData(subscription_id as string, transaction_id as string, plan_id as string);
  };

  const formatPrice = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase()
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getPlanBenefits = (planId: string) => {
    const benefits = {
      starter: [
        '1,000 compute units per month',
        '3 concurrent tasks',
        'Email support',
        'Advanced selectors',
        'Data export (JSON, CSV)'
      ],
      professional: [
        '5,000 compute units per month',
        '10 concurrent tasks',
        'Priority support',
        'API access',
        'Webhook integrations',
        'Custom data formats'
      ],
      enterprise: [
        '25,000 compute units per month',
        '50 concurrent tasks',
        '24/7 phone support',
        'Dedicated account manager',
        'Custom integrations',
        'SLA guarantee'
      ]
    };

    return benefits[planId as keyof typeof benefits] || [];
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">
              {retryCount > 0 ? 'Syncing subscription data...' : 'Processing your payment...'}
            </p>
            {retryCount > 0 && (
              <p className="mt-2 text-sm text-gray-500">
                Please wait while we sync your subscription (Attempt {retryCount}/5)
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Payment Successful - Selextract Cloud</title>
        <meta name="description" content="Your payment was processed successfully" />
      </Head>

      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Success Header */}
        <div className="text-center mb-12">
          <div className="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-green-100 mb-6">
            <CheckCircleIcon className="h-12 w-12 text-green-600" />
          </div>
          
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Payment Successful!
          </h1>
          
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            {successData?.subscription ? (
              `Welcome to ${successData.subscription.plan_name}! Your subscription is now active and ready to use.`
            ) : (
              'Your payment has been processed successfully. Thank you for your purchase!'
            )}
          </p>
        </div>

        {/* Subscription Details */}
        {successData?.subscription && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <div className="flex items-center mb-6">
              <CreditCardIcon className="h-6 w-6 text-gray-400 mr-3" />
              <h2 className="text-2xl font-semibold text-gray-900">Subscription Details</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Payment Info */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Payment Information</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Plan:</span>
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900">
                        {successData.subscription.plan_name}
                      </span>
                      {successData.subscription.plan_id === 'professional' && (
                        <StarIcon className="h-4 w-4 text-yellow-500 ml-1" />
                      )}
                    </div>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Amount:</span>
                    <span className="font-medium text-gray-900">
                      {formatPrice(successData.subscription.amount, successData.subscription.currency)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Billing:</span>
                    <span className="font-medium text-gray-900 capitalize">
                      {successData.subscription.billing_interval}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Next billing:</span>
                    <span className="font-medium text-gray-900">
                      {formatDate(successData.subscription.next_billing_date)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Plan Benefits */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">What's Included</h3>
                <ul className="space-y-2">
                  {getPlanBenefits(successData.subscription.plan_id).map((benefit, index) => (
                    <li key={index} className="flex items-start">
                      <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700">{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Next Steps */}
        <div className="bg-blue-50 rounded-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-blue-900 mb-6">What's Next?</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-blue-600 font-bold">1</span>
              </div>
              <h3 className="font-medium text-blue-900 mb-2">Start Scraping</h3>
              <p className="text-blue-700 text-sm">
                Create your first scraping task and start extracting data immediately.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-blue-600 font-bold">2</span>
              </div>
              <h3 className="font-medium text-blue-900 mb-2">Explore Features</h3>
              <p className="text-blue-700 text-sm">
                Check out advanced features like webhooks, API access, and data exports.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-blue-600 font-bold">3</span>
              </div>
              <h3 className="font-medium text-blue-900 mb-2">Get Support</h3>
              <p className="text-blue-700 text-sm">
                Need help? Our support team is ready to assist you with any questions.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/dashboard" className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors">
            Go to Dashboard
            <ArrowRightIcon className="ml-2 h-5 w-5" />
          </Link>
          
          <Link href="/billing" className="inline-flex items-center justify-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors">
            View Billing Details
          </Link>
        </div>

        {/* Support Info */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-2">
            Need assistance or have questions about your subscription?
          </p>
          <p className="text-blue-600">
            Contact us at{' '}
            <a 
              href="mailto:support@selextract.com" 
              className="font-medium hover:text-blue-500"
            >
              support@selextract.com
            </a>
          </p>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-8">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Unable to load subscription details
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{error}</p>
                  <p className="mt-1">
                    Don't worry - your payment was successful. You can view your subscription details in your billing dashboard.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default withAuth(PaymentSuccessPage);