import React, { useState, useEffect } from 'react';
import { GetServerSideProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  XCircleIcon,
  ArrowLeftIcon,
  CreditCardIcon,
  QuestionMarkCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

import { withAuth } from '../../lib/auth';
import apiClient from '../../lib/api';
import Navbar from '../../components/Navbar';

interface CurrentSubscription {
  plan_id: string;
  plan_name: string;
  status: string;
  cancel_at_period_end?: boolean;
}

const PaymentCancelledPage: React.FC = () => {
  const router = useRouter();
  const [currentSubscription, setCurrentSubscription] = useState<CurrentSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCurrentSubscription();
  }, []);

  const fetchCurrentSubscription = async () => {
    try {
      const data = await apiClient.getSubscription() as any;
      if (data.plan && data.subscription) {
        setCurrentSubscription({
          plan_id: data.plan.id,
          plan_name: data.plan.name,
          status: data.subscription.status,
          cancel_at_period_end: data.subscription.cancel_at_period_end
        });
      }
    } catch (err: any) {
      // User might not have an active subscription - this is normal for cancelled page
      console.warn('No active subscription found');
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (message: string, type: 'success' | 'error') => {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 max-w-sm w-full ${
      type === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
    } border rounded-lg shadow-lg p-4`;
    
    notification.innerHTML = `
      <div class="flex">
        <div class="ml-3">
          <p class="text-sm font-medium ${
            type === 'success' ? 'text-green-800' : 'text-red-800'
          }">${message}</p>
        </div>
      </div>
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 5000);
  };

  const handleRetryCheckout = () => {
    const { plan_id } = router.query;
    if (plan_id) {
      router.push(`/billing/plans?plan=${plan_id}`);
    } else {
      router.push('/billing/plans');
    }
  };

  if (loading) {
    return (
      <>
        <Head>
          <title>Loading - Selextract Cloud</title>
        </Head>
        <Navbar />
        <div className="min-h-screen bg-gray-50 py-12">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading current subscription status...</p>
            </div>
          </div>
        </div>
      </>
    );
  }
  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Payment Cancelled - Selextract Cloud</title>
        <meta name="description" content="Your payment was cancelled" />
      </Head>

      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Cancelled Header */}
        <div className="text-center mb-12">
          <div className="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-yellow-100 mb-6">
            <XCircleIcon className="h-12 w-12 text-yellow-600" />
          </div>
          
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Payment Cancelled
          </h1>
          
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Your payment was cancelled and no charges were made to your account.
            You can still use our free plan or choose a different subscription option.
          </p>
        </div>

        {/* Current Subscription Status Alert */}
        {currentSubscription && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400 mt-0.5" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">
                  Current Subscription Status
                </h3>
                <div className="mt-2 text-sm text-yellow-700">
                  <p>
                    You currently have an active <strong>{currentSubscription.plan_name}</strong> subscription
                    with status: <strong className="capitalize">{currentSubscription.status.replace('_', ' ')}</strong>
                    {currentSubscription.cancel_at_period_end && (
                      <span className="block mt-1">
                        ⚠️ Your subscription is set to cancel at the end of the current period.
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* What Happened */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <div className="flex items-center mb-6">
            <QuestionMarkCircleIcon className="h-6 w-6 text-gray-400 mr-3" />
            <h2 className="text-2xl font-semibold text-gray-900">What Happened?</h2>
          </div>

          <div className="space-y-4 text-gray-700">
            <p>
              Your payment process was cancelled before completion. This could happen for several reasons:
            </p>
            
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>You chose to cancel the payment</li>
              <li>Your browser closed or lost connection during checkout</li>
              <li>Payment method verification failed</li>
              <li>You decided to review the plan details before subscribing</li>
            </ul>
            
            <p className="mt-4">
              <strong>No worries!</strong> No charges were made to your payment method, 
              and your account remains unchanged.
            </p>
          </div>
        </div>

        {/* Free Plan Benefits */}
        <div className="bg-blue-50 rounded-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-blue-900 mb-6">
            Continue with Our Free Plan
          </h2>
          
          <p className="text-blue-700 mb-6">
            You can still use Selextract Cloud with our generous free tier:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h3 className="font-medium text-blue-900">Free Plan Includes:</h3>
              <ul className="space-y-2 text-blue-700">
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  100 compute units per month
                </li>
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  1 concurrent task
                </li>
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  Basic web scraping
                </li>
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  Community support
                </li>
              </ul>
            </div>
            
            <div className="space-y-3">
              <h3 className="font-medium text-blue-900">Perfect For:</h3>
              <ul className="space-y-2 text-blue-700">
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  Testing our platform
                </li>
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  Small personal projects
                </li>
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  Learning web scraping
                </li>
                <li className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  Occasional data extraction
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Action Options */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6">
            What Would You Like to Do?
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Try Again */}
            <div className="text-center p-6 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors">
              <CreditCardIcon className="h-8 w-8 text-blue-600 mx-auto mb-4" />
              <h3 className="font-medium text-gray-900 mb-2">Try Payment Again</h3>
              <p className="text-sm text-gray-600 mb-4">
                Review our plans and complete your subscription
              </p>
              <button
                onClick={handleRetryCheckout}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                {router.query.plan_id ? 'Try Same Plan Again' : 'View Plans'}
              </button>
            </div>

            {/* Use Free Plan */}
            <div className="text-center p-6 border border-gray-200 rounded-lg hover:border-green-300 transition-colors">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-green-600 font-bold text-sm">FREE</span>
              </div>
              <h3 className="font-medium text-gray-900 mb-2">Start with Free Plan</h3>
              <p className="text-sm text-gray-600 mb-4">
                Begin scraping with our free tier
              </p>
              <Link href="/dashboard" className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors">
                Go to Dashboard
              </Link>
            </div>

            {/* Contact Support */}
            <div className="text-center p-6 border border-gray-200 rounded-lg hover:border-purple-300 transition-colors">
              <QuestionMarkCircleIcon className="h-8 w-8 text-purple-600 mx-auto mb-4" />
              <h3 className="font-medium text-gray-900 mb-2">Need Help?</h3>
              <p className="text-sm text-gray-600 mb-4">
                Have questions or encountered an issue?
              </p>
              <a
                href="mailto:support@selextract.com"
                className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
              >
                Contact Support
              </a>
            </div>
          </div>
        </div>

        {/* Common Questions */}
        <div className="bg-gray-50 rounded-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6">
            Common Questions
          </h2>

          <div className="space-y-6">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">
                Was I charged for the cancelled payment?
              </h3>
              <p className="text-gray-600">
                No, your payment was cancelled before any charges were processed. 
                Your payment method was not charged.
              </p>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-2">
                Can I try subscribing again?
              </h3>
              <p className="text-gray-600">
                Absolutely! You can return to our plans page anytime to subscribe. 
                Your account and free plan access remain unchanged.
              </p>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-2">
                What if I'm having payment issues?
              </h3>
              <p className="text-gray-600">
                If you're experiencing technical difficulties with payment, please contact our support team. 
                We're here to help resolve any issues you might encounter.
              </p>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-2">
                How does the free plan compare to paid plans?
              </h3>
              <p className="text-gray-600">
                Our free plan is perfect for getting started and includes 100 compute units monthly. 
                Paid plans offer more compute units, concurrent tasks, advanced features, and priority support.
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/billing/plans" className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors">
            <CreditCardIcon className="mr-2 h-5 w-5" />
            View Subscription Plans
          </Link>
          
          <Link href="/dashboard" className="inline-flex items-center justify-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors">
            <ArrowLeftIcon className="mr-2 h-5 w-5" />
            Return to Dashboard
          </Link>
        </div>

        {/* Support Contact */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-2">
            Still have questions or need assistance?
          </p>
          <p className="text-blue-600">
            Our support team is available at{' '}
            <a 
              href="mailto:support@selextract.com" 
              className="font-medium hover:text-blue-500"
            >
              support@selextract.com
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default withAuth(PaymentCancelledPage);