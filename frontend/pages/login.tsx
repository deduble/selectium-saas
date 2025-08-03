import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth, initiateGoogleAuth } from '../lib/auth';
import { Chrome, Shield, Zap, Users } from 'lucide-react';
import toast from 'react-hot-toast';

const LoginPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      const redirectTo = (router.query.redirect as string) || '/dashboard';
      router.replace(redirectTo);
    }
  }, [isAuthenticated, isLoading, router]);

  const handleGoogleLogin = async () => {
    try {
      setIsAuthenticating(true);
      await initiateGoogleAuth();
    } catch (error) {
      console.error('Google login failed:', error);
      toast.error('Failed to initiate Google login. Please try again.');
      setIsAuthenticating(false);
    }
  };

  // Handle error states from URL parameters
  useEffect(() => {
    const { error } = router.query;
    if (error && !isLoading) {
      const errorMessages: Record<string, string> = {
        'auth_callback_failed': 'Authentication failed. Please try logging in again.',
        'invalid_state': 'Authentication session expired. Please try again.',
        'missing_parameters': 'Authentication request was incomplete. Please try again.',
        'state_expired': 'Authentication session expired. Please try again.',
        'authentication_failed': 'Google authentication failed. Please try again.',
        'server_error': 'Server error during authentication. Please try again later.'
      };
      
      const errorMsg = errorMessages[error as string] || 'Authentication failed. Please try again.';
      toast.error(errorMsg);
      
      // Clear error from URL
      router.replace('/login', undefined, { shallow: true });
    }
  }, [router.query, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-16 h-16 bg-primary-600 rounded-lg flex items-center justify-center">
            <Zap className="w-8 h-8 text-white" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
          Sign in to Selextract Cloud
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          The fastest way to extract data from any website
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          <div className="space-y-6">
            <button
              onClick={handleGoogleLogin}
              disabled={isAuthenticating}
              className="w-full flex justify-center items-center py-3 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isAuthenticating ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-900"></div>
              ) : (
                <>
                  <Chrome className="w-5 h-5 mr-3 text-red-500" />
                  Continue with Google
                </>
              )}
            </button>

            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Why choose Selextract?</span>
                </div>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="flex items-start space-x-3">
                <Shield className="w-6 h-6 text-primary-600 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-gray-900">Secure & Reliable</h3>
                  <p className="text-sm text-gray-600">Enterprise-grade security with 99.9% uptime</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <Zap className="w-6 h-6 text-primary-600 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-gray-900">Lightning Fast</h3>
                  <p className="text-sm text-gray-600">Extract data from thousands of pages in minutes</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <Users className="w-6 h-6 text-primary-600 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-gray-900">Developer Friendly</h3>
                  <p className="text-sm text-gray-600">RESTful API with comprehensive documentation</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <div className="text-center text-xs text-gray-500">
            By signing in, you agree to our{' '}
            <a href="/terms" className="text-primary-600 hover:text-primary-500">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="/privacy" className="text-primary-600 hover:text-primary-500">
              Privacy Policy
            </a>
          </div>
        </div>
      </div>

      <div className="mt-12 text-center">
        <div className="text-sm text-gray-600">
          <p>Trusted by developers at</p>
          <div className="mt-4 flex justify-center items-center space-x-8 opacity-60">
            <div className="text-lg font-bold">TechCorp</div>
            <div className="text-lg font-bold">DataFlow</div>
            <div className="text-lg font-bold">WebScale</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;