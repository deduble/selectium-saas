import React, { useState, useEffect } from 'react';
import { GetServerSideProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  CheckIcon,
  XMarkIcon,
  ArrowLeftIcon,
  StarIcon,
  CreditCardIcon
} from '@heroicons/react/24/outline';

import { withAuth } from '../../lib/auth';
import apiClient, { SubscriptionPlan as Plan } from '../../lib/api';
import Navbar from '../../components/Navbar';
import PlanComparison from '../../components/PlanComparison';

interface CurrentSubscription {
  plan_id: string;
  status: string;
  cancel_at_period_end: boolean;
}

const PlansPage: React.FC = () => {
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentSubscription, setCurrentSubscription] = useState<CurrentSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [plansLoading, setPlansLoading] = useState(true);
  const [subscriptionLoading, setSubscriptionLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [subscriptionError, setSubscriptionError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    
    // Load both plans and subscription data in parallel
    await Promise.allSettled([
      fetchPlans(),
      fetchCurrentSubscription()
    ]);
    
    setLoading(false);
  };

  const fetchPlans = async () => {
    setPlansLoading(true);
    setError(null);
    
    try {
      const data = await apiClient.getPlans();
      // Mark professional plan as popular
      const plansWithPopular = data.map((plan: Plan) => ({
        ...plan,
        popular: plan.id === 'professional' || plan.tier === 'professional'
      }));
      setPlans(plansWithPopular);
      setRetryCount(0); // Reset retry count on success
    } catch (err: any) {
      console.error('Failed to fetch plans:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Failed to load subscription plans';
      setError(errorMessage);
      
      // Auto-retry on network errors
      if (retryCount < 3 && (err.code === 'NETWORK_ERROR' || err.response?.status >= 500)) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchPlans();
        }, 2000 * (retryCount + 1)); // Exponential backoff
      }
    } finally {
      setPlansLoading(false);
    }
  };

  const fetchCurrentSubscription = async () => {
    setSubscriptionLoading(true);
    setSubscriptionError(null);
    
    try {
      const data = await apiClient.getSubscription() as any;
      setCurrentSubscription({
        plan_id: data.plan?.id || 'free',
        status: data.subscription?.status || 'none',
        cancel_at_period_end: data.subscription?.cancel_at_period_end || false
      });
    } catch (err: any) {
      // User might not have an active subscription - this is normal
      if (err.response?.status === 404 || err.response?.status === 401) {
        console.warn('No active subscription found - user likely on free plan');
        setCurrentSubscription({
          plan_id: 'free',
          status: 'none',
          cancel_at_period_end: false
        });
      } else {
        console.error('Failed to fetch subscription:', err);
        const errorMessage = err.response?.data?.message || err.message || 'Failed to load current subscription';
        setSubscriptionError(errorMessage);
      }
    } finally {
      setSubscriptionLoading(false);
    }
  };

  const handleSelectPlan = async (planId: string) => {
    if (planId === 'free') {
      // Handle downgrade to free plan
      if (currentSubscription && currentSubscription.plan_id !== 'free') {
        if (confirm('Are you sure you want to downgrade to the free plan? This will limit your compute units and features.')) {
          // For free plan, we need to cancel the current subscription
          setCheckoutLoading(planId);
          try {
            await apiClient.cancelSubscription();
            
            // Show success message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded z-50';
            alertDiv.innerHTML = 'Your subscription has been cancelled. You will be downgraded to the free plan at the end of your current billing period.';
            document.body.appendChild(alertDiv);
            setTimeout(() => document.body.removeChild(alertDiv), 5000);
            
            // Refresh data and redirect
            await fetchCurrentSubscription();
            router.push('/billing');
          } catch (err: any) {
            const errorMessage = err.response?.data?.message || err.message || 'Unknown error';
            
            // Show error message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
            alertDiv.innerHTML = `Failed to cancel subscription: ${errorMessage}`;
            document.body.appendChild(alertDiv);
            setTimeout(() => document.body.removeChild(alertDiv), 5000);
          } finally {
            setCheckoutLoading(null);
          }
        }
      }
      return;
    }

    // Check if user is already on this plan
    if (currentSubscription?.plan_id === planId) {
      // Show info message
      const alertDiv = document.createElement('div');
      alertDiv.className = 'fixed top-4 right-4 bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded z-50';
      alertDiv.innerHTML = 'You are already subscribed to this plan.';
      document.body.appendChild(alertDiv);
      setTimeout(() => document.body.removeChild(alertDiv), 3000);
      return;
    }

    setCheckoutLoading(planId);

    try {
      if (currentSubscription && currentSubscription.plan_id !== 'free' && currentSubscription.status !== 'none') {
        // This is an upgrade/downgrade
        const subscription = await apiClient.updateSubscription(planId);
        
        // Show success message
        const alertDiv = document.createElement('div');
        alertDiv.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded z-50';
        alertDiv.innerHTML = 'Subscription updated successfully!';
        document.body.appendChild(alertDiv);
        setTimeout(() => document.body.removeChild(alertDiv), 3000);
        
        router.push('/billing');
      } else {
        // This is a new subscription
        const { checkout_url } = await apiClient.createCheckoutSession(planId);

        // Redirect to Lemon Squeezy checkout
        if (checkout_url) {
          window.location.href = checkout_url;
        } else {
          throw new Error('No checkout URL received from payment provider');
        }
      }
    } catch (err: any) {
      console.error('Failed to process plan selection:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Unknown error occurred';
      
      // Show detailed error message
      const alertDiv = document.createElement('div');
      alertDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50 max-w-md';
      alertDiv.innerHTML = `
        <strong>Failed to process plan selection:</strong><br>
        ${errorMessage}
        ${err.response?.status ? `<br><small>Error code: ${err.response.status}</small>` : ''}
      `;
      document.body.appendChild(alertDiv);
      setTimeout(() => document.body.removeChild(alertDiv), 7000);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const formatPrice = (price: number | null | undefined) => {
    return `$${(price || 0).toFixed(2)}`;
  };

  const getPlanButtonText = (plan: Plan) => {
    if (checkoutLoading === plan.id) {
      return plan.id === 'free' ? 'Processing...' : 'Redirecting...';
    }

    if (currentSubscription?.plan_id === plan.id) {
      return 'Current Plan';
    }

    if (plan.id === 'free') {
      return currentSubscription?.plan_id !== 'free' ? 'Downgrade' : 'Current Plan';
    }

    if (currentSubscription && currentSubscription.plan_id !== 'free') {
      // Determine if it's an upgrade or downgrade
      const currentPlanIndex = plans.findIndex(p => p.id === currentSubscription.plan_id);
      const targetPlanIndex = plans.findIndex(p => p.id === plan.id);
      
      if (currentPlanIndex < targetPlanIndex) {
        return 'Upgrade';
      } else if (currentPlanIndex > targetPlanIndex) {
        return 'Downgrade';
      }
      return 'Switch Plan';
    }

    return 'Get Started';
  };

  const getPlanButtonStyle = (plan: Plan) => {
    const isCurrentPlan = currentSubscription?.plan_id === plan.id;
    const isLoading = checkoutLoading === plan.id;

    if (isCurrentPlan) {
      return 'bg-gray-100 text-gray-400 cursor-not-allowed';
    }

    if (plan.popular) {
      return `bg-blue-600 text-white hover:bg-blue-700 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`;
    }

    return `bg-white text-gray-900 border border-gray-300 hover:bg-gray-50 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading subscription plans...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <XMarkIcon className="h-12 w-12 text-red-500 mx-auto" />
            <p className="mt-4 text-gray-600">{error}</p>
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
        <title>Subscription Plans - Selextract Cloud</title>
        <meta name="description" content="Choose the perfect plan for your web scraping needs" />
      </Head>

      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <Link href="/billing" className="inline-flex items-center text-blue-600 hover:text-blue-500 mb-6">
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Billing
          </Link>
          
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Choose Your Plan
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Select the perfect plan for your web scraping and data extraction needs. 
            Upgrade or downgrade anytime.
          </p>

          {currentSubscription && (
            <div className="mt-6 inline-flex items-center px-4 py-2 bg-blue-50 text-blue-800 rounded-lg">
              <CreditCardIcon className="h-5 w-5 mr-2" />
              Currently on {plans.find(p => p.id === currentSubscription.plan_id)?.name || 'Unknown'} plan
              {currentSubscription.cancel_at_period_end && (
                <span className="ml-2 text-yellow-600">(Cancelling)</span>
              )}
            </div>
          )}
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative bg-white rounded-2xl shadow-lg ${
                plan.popular ? 'ring-2 ring-blue-600' : ''
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="inline-flex items-center px-4 py-1 rounded-full text-sm font-medium bg-blue-600 text-white">
                    <StarIcon className="h-4 w-4 mr-1" />
                    Most Popular
                  </span>
                </div>
              )}

              <div className="p-8">
                {/* Plan Header */}
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-gray-900">{plan.name}</h3>
                  <div className="mt-4">
                    <span className="text-4xl font-bold text-gray-900">
                      {formatPrice(plan.price)}
                    </span>
                    {plan.price > 0 && (
                      <span className="text-gray-500">/{plan.billing_interval}</span>
                    )}
                  </div>
                  <p className="mt-2 text-gray-600">
                    {(Number(plan.compute_units_limit) || 0).toLocaleString()} compute units per month
                  </p>
                </div>

                {/* Features */}
                <ul className="space-y-4 mb-8">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                      <CheckIcon className="h-5 w-5 text-green-500 mr-3 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* Action Button */}
                <button
                  onClick={() => handleSelectPlan(plan.id)}
                  disabled={
                    currentSubscription?.plan_id === plan.id || 
                    checkoutLoading === plan.id
                  }
                  className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${getPlanButtonStyle(plan)}`}
                >
                  {checkoutLoading === plan.id && (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current inline-block mr-2"></div>
                  )}
                  {getPlanButtonText(plan)}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Plan Comparison Table */}
        <PlanComparison plans={plans} currentPlanId={currentSubscription?.plan_id} />

        {/* FAQ Section */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">
            Frequently Asked Questions
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                What are compute units?
              </h3>
              <p className="text-gray-600">
                Compute units measure the processing power used for your web scraping tasks. 
                Generally, 1 compute unit equals about 1 minute of scraping time, though this can vary based on task complexity.
              </p>
            </div>

            <div className="bg-white rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Can I change my plan anytime?
              </h3>
              <p className="text-gray-600">
                Yes! You can upgrade or downgrade your plan at any time. Upgrades take effect immediately, 
                while downgrades take effect at the end of your current billing period.
              </p>
            </div>

            <div className="bg-white rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                What happens if I exceed my compute units?
              </h3>
              <p className="text-gray-600">
                If you exceed your monthly compute units, additional usage will be charged at standard overage rates. 
                We recommend upgrading to a higher plan to avoid overage charges.
              </p>
            </div>

            <div className="bg-white rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Is there a free trial?
              </h3>
              <p className="text-gray-600">
                Our free plan includes 100 compute units per month with no time limit. 
                This allows you to test our service and see if it meets your needs before upgrading.
              </p>
            </div>
          </div>
        </div>

        {/* Support Section */}
        <div className="mt-16 text-center">
          <div className="bg-blue-50 rounded-lg p-8 max-w-2xl mx-auto">
            <h3 className="text-2xl font-bold text-blue-900 mb-4">
              Need Help Choosing?
            </h3>
            <p className="text-blue-700 mb-6">
              Our team is here to help you find the perfect plan for your needs. 
              Contact us for a personalized recommendation.
            </p>
            <a
              href="mailto:support@selextract.com"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Contact Support
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default withAuth(PlansPage);