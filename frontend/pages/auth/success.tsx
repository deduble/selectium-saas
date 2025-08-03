import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../../lib/auth';
import { api } from '../../lib/api';
import { CheckCircle, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const AuthSuccessPage: React.FC = () => {
  const router = useRouter();
  const { login } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const handleGoogleCallback = async () => {
      try {
        const { token, error } = router.query;

        if (error) {
          setStatus('error');
          const errorMsg = typeof error === 'string' ? error : 'Authentication failed';
          setErrorMessage(`Authentication error: ${errorMsg}`);
          return;
        }

        if (!token) {
          setStatus('error');
          setErrorMessage('No authentication token received from server');
          return;
        }

        // Validate token format (basic check)
        if (typeof token !== 'string' || token.length < 10) {
          setStatus('error');
          setErrorMessage('Invalid authentication token format');
          return;
        }

        console.log('Auth success: received token, attempting login...');
        
        // Login with the received token
        await login(token);
        
        setStatus('success');
        
        // Redirect after a brief delay to show success message
        setTimeout(() => {
          const redirectTo = (router.query.redirect as string) || '/dashboard';
          router.replace(redirectTo);
        }, 1500);

      } catch (error: any) {
        console.error('Google auth callback error:', error);
        setStatus('error');
        const errorMsg = error?.message || error?.response?.data?.message || 'Authentication failed';
        setErrorMessage(errorMsg);
        toast.error('Authentication failed. Please try again.');
        
        // Redirect to login page after error with delay
        setTimeout(() => {
          router.replace('/login?error=auth_callback_failed');
        }, 3000);
      }
    };

    if (router.isReady && status === 'loading') {
      handleGoogleCallback();
    }
  }, [router.isReady, router.query, login, status, router]);

  const renderContent = () => {
    switch (status) {
      case 'loading':
        return (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <h2 className="mt-4 text-xl font-semibold text-gray-900">
              Completing your sign in...
            </h2>
            <p className="mt-2 text-gray-600">
              Please wait while we set up your account
            </p>
          </div>
        );

      case 'success':
        return (
          <div className="text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
            <h2 className="mt-4 text-xl font-semibold text-gray-900">
              Welcome to Selextract Cloud!
            </h2>
            <p className="mt-2 text-gray-600">
              You have been successfully signed in. Redirecting to your dashboard...
            </p>
          </div>
        );

      case 'error':
        return (
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
            <h2 className="mt-4 text-xl font-semibold text-gray-900">
              Authentication Failed
            </h2>
            <p className="mt-2 text-gray-600">
              {errorMessage || 'Something went wrong during sign in.'}
            </p>
            <button
              onClick={() => router.push('/login')}
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Try Again
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {renderContent()}
        </div>
      </div>
      
      {status === 'error' && (
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            If you continue to experience issues, please{' '}
            <a 
              href="mailto:support@selextract.com" 
              className="text-primary-600 hover:text-primary-500"
            >
              contact support
            </a>
          </p>
        </div>
      )}
    </div>
  );
};

export default AuthSuccessPage;