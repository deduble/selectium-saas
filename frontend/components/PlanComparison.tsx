import React, { useState, useEffect } from 'react';
import { CheckIcon, XMarkIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import apiClient from '../lib/api';

interface Plan {
  id: string;
  name: string;
  tier: string;
  price: number;
  currency: string;
  compute_units_limit: number;
  monthly_compute_units?: number;
  max_concurrent_tasks?: number;
  features: string[];
  billing_interval: string;
  popular?: boolean;
}

interface PlanComparisonProps {
  plans?: Plan[];
  currentPlanId?: string;
  loading?: boolean;
  error?: string | null;
}

const PlanComparison: React.FC<PlanComparisonProps> = ({
  plans: propPlans,
  currentPlanId,
  loading: propLoading,
  error: propError
}) => {
  const [plans, setPlans] = useState<Plan[]>(propPlans || []);
  const [loading, setLoading] = useState<boolean>(propLoading || !propPlans);
  const [error, setError] = useState<string | null>(propError || null);

  useEffect(() => {
    // If plans are provided as props, use them
    if (propPlans && propPlans.length > 0) {
      setPlans(propPlans);
      setLoading(false);
      setError(null);
      return;
    }

    // Otherwise, fetch plans from API
    fetchPlans();
  }, [propPlans]);

  const fetchPlans = async () => {
    if (propPlans && propPlans.length > 0) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await apiClient.getPlans();
      const plansWithPopular = data.map((plan: Plan) => ({
        ...plan,
        popular: plan.id === 'professional' || plan.tier === 'professional'
      }));
      setPlans(plansWithPopular);
    } catch (err: any) {
      console.error('Failed to fetch plans for comparison:', err);
      setError('Failed to load subscription plans for comparison');
    } finally {
      setLoading(false);
    }
  };

  // Show loading state
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Detailed Plan Comparison
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Compare all features across our subscription plans
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading plan comparison...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Detailed Plan Comparison
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Compare all features across our subscription plans
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto" />
            <p className="mt-4 text-gray-600">{error}</p>
            <button
              onClick={fetchPlans}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show empty state
  if (!plans || plans.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Detailed Plan Comparison
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Compare all features across our subscription plans
          </p>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <p className="text-gray-600">No subscription plans available</p>
          </div>
        </div>
      </div>
    );
  }
  const formatPrice = (price: number | null | undefined) => {
    return `$${(Number(price) || 0).toFixed(2)}`;
  };

  // Define comprehensive feature comparison
  const comparisonFeatures = [
    {
      category: 'Usage Limits',
      features: [
        {
          name: 'Monthly Compute Units',
          getValue: (plan: Plan) => {
            const limit = Number(plan.compute_units_limit || 0);
            return limit.toLocaleString();
          },
          type: 'text'
        },
        {
          name: 'Concurrent Tasks',
          getValue: (plan: Plan) => {
            const limits = {
              free: '1',
              starter: '3',
              professional: '10',
              enterprise: '50'
            };
            return limits[plan.id as keyof typeof limits] || (plan.max_concurrent_tasks?.toString()) || 'Unknown';
          },
          type: 'text'
        },
        {
          name: 'API Rate Limit',
          getValue: (plan: Plan) => {
            const limits = {
              free: '10/min',
              starter: '100/min',
              professional: '1000/min',
              enterprise: 'Unlimited'
            };
            return limits[plan.id as keyof typeof limits] || 'Unknown';
          },
          type: 'text'
        }
      ]
    },
    {
      category: 'Core Features',
      features: [
        {
          name: 'Web Scraping',
          getValue: (plan: Plan) => true,
          type: 'boolean'
        },
        {
          name: 'CSS Selectors',
          getValue: (plan: Plan) => true,
          type: 'boolean'
        },
        {
          name: 'XPath Support',
          getValue: (plan: Plan) => plan.id !== 'free',
          type: 'boolean'
        },
        {
          name: 'JavaScript Rendering',
          getValue: (plan: Plan) => plan.id !== 'free',
          type: 'boolean'
        },
        {
          name: 'Proxy Support',
          getValue: (plan: Plan) => plan.id !== 'free',
          type: 'boolean'
        },
        {
          name: 'Anti-Bot Detection',
          getValue: (plan: Plan) => ['professional', 'enterprise'].includes(plan.id),
          type: 'boolean'
        }
      ]
    },
    {
      category: 'Data Export',
      features: [
        {
          name: 'JSON Export',
          getValue: (plan: Plan) => true,
          type: 'boolean'
        },
        {
          name: 'CSV Export',
          getValue: (plan: Plan) => plan.id !== 'free',
          type: 'boolean'
        },
        {
          name: 'Excel Export',
          getValue: (plan: Plan) => ['professional', 'enterprise'].includes(plan.id),
          type: 'boolean'
        },
        {
          name: 'XML Export',
          getValue: (plan: Plan) => ['professional', 'enterprise'].includes(plan.id),
          type: 'boolean'
        },
        {
          name: 'Custom Formats',
          getValue: (plan: Plan) => plan.id === 'enterprise',
          type: 'boolean'
        }
      ]
    },
    {
      category: 'Integrations',
      features: [
        {
          name: 'REST API',
          getValue: (plan: Plan) => plan.id !== 'free',
          type: 'boolean'
        },
        {
          name: 'Webhooks',
          getValue: (plan: Plan) => ['professional', 'enterprise'].includes(plan.id),
          type: 'boolean'
        },
        {
          name: 'Zapier Integration',
          getValue: (plan: Plan) => ['professional', 'enterprise'].includes(plan.id),
          type: 'boolean'
        },
        {
          name: 'Custom API Endpoints',
          getValue: (plan: Plan) => plan.id === 'enterprise',
          type: 'boolean'
        },
        {
          name: 'Database Connections',
          getValue: (plan: Plan) => plan.id === 'enterprise',
          type: 'boolean'
        }
      ]
    },
    {
      category: 'Support & SLA',
      features: [
        {
          name: 'Support Type',
          getValue: (plan: Plan) => {
            const types = {
              free: 'Community',
              starter: 'Email',
              professional: 'Priority Email',
              enterprise: '24/7 Phone + Email'
            };
            return types[plan.id as keyof typeof types] || 'Unknown';
          },
          type: 'text'
        },
        {
          name: 'Response Time',
          getValue: (plan: Plan) => {
            const times = {
              free: 'Best effort',
              starter: '48 hours',
              professional: '24 hours',
              enterprise: '4 hours'
            };
            return times[plan.id as keyof typeof times] || 'Unknown';
          },
          type: 'text'
        },
        {
          name: 'SLA Guarantee',
          getValue: (plan: Plan) => plan.id === 'enterprise',
          type: 'boolean'
        },
        {
          name: 'Dedicated Account Manager',
          getValue: (plan: Plan) => plan.id === 'enterprise',
          type: 'boolean'
        }
      ]
    }
  ];

  const renderFeatureValue = (feature: any, plan: Plan) => {
    const value = feature.getValue(plan);
    
    if (feature.type === 'boolean') {
      return value ? (
        <CheckIcon className="h-5 w-5 text-green-500 mx-auto" />
      ) : (
        <XMarkIcon className="h-5 w-5 text-gray-300 mx-auto" />
      );
    }
    
    return <span className="text-sm text-gray-900">{value}</span>;
  };

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">
          Detailed Plan Comparison
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          Compare all features across our subscription plans
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full">
          {/* Header */}
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-900">
                Features
              </th>
              {plans.map((plan) => (
                <th key={plan.id} className="px-6 py-4 text-center">
                  <div className="space-y-2">
                    <div className="flex items-center justify-center">
                      <span className="text-lg font-bold text-gray-900">
                        {plan.name}
                      </span>
                      {plan.popular && (
                        <span className="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                          Popular
                        </span>
                      )}
                      {currentPlanId === plan.id && (
                        <span className="ml-2 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                          Current
                        </span>
                      )}
                    </div>
                    <div className="text-2xl font-bold text-gray-900">
                      {formatPrice(plan.price)}
                      {plan.price > 0 && (
                        <span className="text-sm font-normal text-gray-500">
                          /{plan.billing_interval}
                        </span>
                      )}
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Body */}
          <tbody className="divide-y divide-gray-200">
            {comparisonFeatures.map((category, categoryIndex) => (
              <React.Fragment key={category.category}>
                {/* Category Header */}
                <tr className="bg-gray-50">
                  <td
                    colSpan={plans.length + 1}
                    className="px-6 py-3 text-sm font-semibold text-gray-900"
                  >
                    {category.category}
                  </td>
                </tr>
                
                {/* Category Features */}
                {category.features.map((feature, featureIndex) => (
                  <tr key={`${categoryIndex}-${featureIndex}`} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900 font-medium">
                      {feature.name}
                    </td>
                    {plans.map((plan) => (
                      <td key={plan.id} className="px-6 py-4 text-center">
                        {renderFeatureValue(feature, plan)}
                      </td>
                    ))}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer Note */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center text-sm text-gray-600">
          <CheckIcon className="h-4 w-4 text-green-500 mr-2" />
          <span>Feature included</span>
          <XMarkIcon className="h-4 w-4 text-gray-300 ml-6 mr-2" />
          <span>Feature not available</span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          * Enterprise features can be customized based on your specific requirements. 
          Contact our sales team for more information.
        </p>
      </div>
    </div>
  );
};

export default PlanComparison;