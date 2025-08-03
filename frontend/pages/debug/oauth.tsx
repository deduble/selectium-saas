import React, { useState, useEffect } from 'react';
import { AlertCircle, Info, CheckCircle, Copy } from 'lucide-react';

const OAuthDebugPage: React.FC = () => {
  const [envVars, setEnvVars] = useState<any>({});
  const [oauthUrl, setOauthUrl] = useState<string>('');
  const [debugInfo, setDebugInfo] = useState<any>({});

  useEffect(() => {
    // Get environment variables available to frontend
    const frontendEnvVars = {
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
      NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
      NEXT_PUBLIC_GOOGLE_CLIENT_ID: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
    };
    setEnvVars(frontendEnvVars);

    // Calculate OAuth URLs
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    const appUrl = process.env.NEXT_PUBLIC_APP_URL;
    const frontendRedirectUri = `${appUrl}/auth/success`;
    
    const googleAuthUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    googleAuthUrl.searchParams.set('client_id', clientId || '');
    googleAuthUrl.searchParams.set('redirect_uri', frontendRedirectUri);
    googleAuthUrl.searchParams.set('response_type', 'code');
    googleAuthUrl.searchParams.set('scope', 'openid email profile');
    googleAuthUrl.searchParams.set('access_type', 'offline');
    googleAuthUrl.searchParams.set('prompt', 'consent');

    setOauthUrl(googleAuthUrl.toString());

    // Debug information
    setDebugInfo({
      frontendRedirectUri,
      expectedBackendRedirectUri: `${process.env.NEXT_PUBLIC_API_URL}/auth/google/callback`,
      googleAuthUrl: googleAuthUrl.toString(),
      currentUrl: typeof window !== 'undefined' ? window.location.href : 'N/A',
    });
  }, []);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const DebugSection = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">{title}</h2>
      {children}
    </div>
  );

  const ConfigItem = ({ label, value, status, description }: { 
    label: string; 
    value: string; 
    status?: 'good' | 'warning' | 'error';
    description?: string;
  }) => (
    <div className="mb-4 p-3 border rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-700">{label}:</span>
        <div className="flex items-center space-x-2">
          {status === 'good' && <CheckCircle className="w-4 h-4 text-green-500" />}
          {status === 'warning' && <AlertCircle className="w-4 h-4 text-yellow-500" />}
          {status === 'error' && <AlertCircle className="w-4 h-4 text-red-500" />}
          <button
            onClick={() => copyToClipboard(value)}
            className="p-1 hover:bg-gray-100 rounded"
            title="Copy to clipboard"
          >
            <Copy className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>
      <code className="text-sm bg-gray-100 p-2 rounded block break-all">{value || 'Not set'}</code>
      {description && (
        <p className="text-sm text-gray-600 mt-2">{description}</p>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">OAuth Debug Tool</h1>
          <p className="text-gray-600">
            Debug OAuth redirect URI configuration and environment variables
          </p>
        </div>

        <DebugSection title="Environment Variables">
          <ConfigItem
            label="NEXT_PUBLIC_API_URL"
            value={envVars.NEXT_PUBLIC_API_URL}
            status={envVars.NEXT_PUBLIC_API_URL ? 'good' : 'error'}
            description="Base URL for API calls"
          />
          <ConfigItem
            label="NEXT_PUBLIC_APP_URL"
            value={envVars.NEXT_PUBLIC_APP_URL}
            status={envVars.NEXT_PUBLIC_APP_URL ? 'good' : 'error'}
            description="Frontend application URL used for OAuth redirects"
          />
          <ConfigItem
            label="NEXT_PUBLIC_GOOGLE_CLIENT_ID"
            value={envVars.NEXT_PUBLIC_GOOGLE_CLIENT_ID}
            status={envVars.NEXT_PUBLIC_GOOGLE_CLIENT_ID ? 'good' : 'error'}
            description="Google OAuth client ID"
          />
        </DebugSection>

        <DebugSection title="OAuth Redirect URIs">
          <ConfigItem
            label="Frontend Redirect URI (Current Implementation)"
            value={debugInfo.frontendRedirectUri}
            status="warning"
            description="This is where Google will redirect after authentication. This should match what's configured in Google Console."
          />
          <ConfigItem
            label="Expected Backend Callback URI"
            value={debugInfo.expectedBackendRedirectUri}
            status="error"
            description="This is what the backend expects for server-side OAuth flow. There's a mismatch here!"
          />
        </DebugSection>

        <DebugSection title="Generated OAuth URL">
          <ConfigItem
            label="Google OAuth Authorization URL"
            value={debugInfo.googleAuthUrl}
            description="This is the URL that users are redirected to for Google authentication"
          />
        </DebugSection>

        <DebugSection title="Issues Detected">
          <div className="space-y-4">
            <div className="flex items-start space-x-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-800">OAuth Flow Mismatch</h3>
                <p className="text-sm text-red-700 mt-1">
                  Frontend uses client-side OAuth flow but backend expects server-side callback. 
                  Frontend redirects to /auth/success but backend expects /auth/google/callback.
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
              <div>
                <h3 className="font-medium text-yellow-800">API Endpoint Inconsistency</h3>
                <p className="text-sm text-yellow-700 mt-1">
                  Frontend calls /auth/google but should call /api/auth/google for consistency.
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <Info className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-800">Environment Configuration</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Backend GOOGLE_REDIRECT_URI should match frontend redirect URI for consistency.
                </p>
              </div>
            </div>
          </div>
        </DebugSection>

        <DebugSection title="Recommended Solutions">
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <h3 className="font-medium text-green-800 mb-2">Option 1: Fix Frontend to Match Backend (Recommended)</h3>
              <ol className="list-decimal list-inside text-sm text-green-700 space-y-1">
                <li>Update frontend to use server-side OAuth flow</li>
                <li>Call /api/auth/google to get authorization URL</li>
                <li>Configure Google Console redirect URI to: <code>{debugInfo.expectedBackendRedirectUri}</code></li>
                <li>Backend handles the callback and redirects to frontend success page</li>
              </ol>
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="font-medium text-blue-800 mb-2">Option 2: Update Backend to Match Frontend</h3>
              <ol className="list-decimal list-inside text-sm text-blue-700 space-y-1">
                <li>Update backend GOOGLE_REDIRECT_URI to: <code>{debugInfo.frontendRedirectUri}</code></li>
                <li>Modify /auth/success page to send auth code to backend</li>
                <li>Configure Google Console redirect URI to: <code>{debugInfo.frontendRedirectUri}</code></li>
              </ol>
            </div>
          </div>
        </DebugSection>

        <div className="text-center mt-8">
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Refresh Debug Info
          </button>
        </div>
      </div>
    </div>
  );
};

export default OAuthDebugPage;