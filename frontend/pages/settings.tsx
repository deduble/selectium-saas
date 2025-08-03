import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import Navbar from '../components/Navbar';
import { 
  Settings as SettingsIcon,
  Bell,
  Shield,
  Globe,
  Monitor,
  Moon,
  Sun,
  Eye,
  EyeOff,
  Save,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Palette,
  Clock,
  Database,
  Download,
  Trash2
} from 'lucide-react';
import toast from 'react-hot-toast';

interface NotificationSettings {
  email_notifications: boolean;
  task_completion: boolean;
  task_failure: boolean;
  weekly_summary: boolean;
  security_alerts: boolean;
  marketing_emails: boolean;
}

interface PrivacySettings {
  profile_visibility: 'public' | 'private';
  analytics_tracking: boolean;
  error_reporting: boolean;
  usage_statistics: boolean;
}

interface AppearanceSettings {
  theme: 'light' | 'dark' | 'system';
  compact_mode: boolean;
  show_animations: boolean;
  sidebar_collapsed: boolean;
}

interface DataSettings {
  auto_delete_tasks: boolean;
  auto_delete_days: number;
  export_format: 'json' | 'csv' | 'xlsx';
  timezone: string;
}

const SettingsPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState('notifications');
  const [isSaving, setIsSaving] = useState(false);

  // Settings state
  const [notifications, setNotifications] = useState<NotificationSettings>({
    email_notifications: true,
    task_completion: true,
    task_failure: true,
    weekly_summary: false,
    security_alerts: true,
    marketing_emails: false,
  });

  const [privacy, setPrivacy] = useState<PrivacySettings>({
    profile_visibility: 'private',
    analytics_tracking: true,
    error_reporting: true,
    usage_statistics: true,
  });

  const [appearance, setAppearance] = useState<AppearanceSettings>({
    theme: 'system',
    compact_mode: false,
    show_animations: true,
    sidebar_collapsed: false,
  });

  const [data, setData] = useState<DataSettings>({
    auto_delete_tasks: false,
    auto_delete_days: 90,
    export_format: 'json',
    timezone: 'UTC',
  });

  // Authentication guard
  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const handleSaveSettings = async () => {
    setIsSaving(true);
    
    try {
      // In a real app, this would make API calls to save settings
      // For now, we'll simulate a save operation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      toast.success('Settings saved successfully');
    } catch (error: any) {
      console.error('Failed to save settings:', error);
      toast.error('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleExportData = async () => {
    try {
      // Simulate data export
      toast.success('Data export initiated. You will receive an email when ready.');
    } catch (error: any) {
      toast.error('Failed to export data');
    }
  };

  const handleClearCache = async () => {
    try {
      // Clear browser cache and local storage related to the app
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
      }
      
      // Clear local storage items (be careful not to clear auth tokens)
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && !key.includes('auth') && !key.includes('token')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key));
      
      toast.success('Cache cleared successfully');
    } catch (error: any) {
      toast.error('Failed to clear cache');
    }
  };

  const tabs = [
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'privacy', name: 'Privacy & Security', icon: Shield },
    { id: 'appearance', name: 'Appearance', icon: Palette },
    { id: 'data', name: 'Data & Storage', icon: Database },
  ];

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  const renderNotificationsTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Email Notifications</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Enable email notifications</label>
              <p className="text-sm text-gray-500">Receive notifications via email</p>
            </div>
            <input
              type="checkbox"
              checked={notifications.email_notifications}
              onChange={(e) => setNotifications(prev => ({
                ...prev,
                email_notifications: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Task completion</label>
              <p className="text-sm text-gray-500">Notify when tasks complete successfully</p>
            </div>
            <input
              type="checkbox"
              checked={notifications.task_completion}
              onChange={(e) => setNotifications(prev => ({
                ...prev,
                task_completion: e.target.checked
              }))}
              disabled={!notifications.email_notifications}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Task failure</label>
              <p className="text-sm text-gray-500">Notify when tasks fail or encounter errors</p>
            </div>
            <input
              type="checkbox"
              checked={notifications.task_failure}
              onChange={(e) => setNotifications(prev => ({
                ...prev,
                task_failure: e.target.checked
              }))}
              disabled={!notifications.email_notifications}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Weekly summary</label>
              <p className="text-sm text-gray-500">Receive weekly usage and activity summaries</p>
            </div>
            <input
              type="checkbox"
              checked={notifications.weekly_summary}
              onChange={(e) => setNotifications(prev => ({
                ...prev,
                weekly_summary: e.target.checked
              }))}
              disabled={!notifications.email_notifications}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Security alerts</label>
              <p className="text-sm text-gray-500">Important security and account notifications</p>
            </div>
            <input
              type="checkbox"
              checked={notifications.security_alerts}
              onChange={(e) => setNotifications(prev => ({
                ...prev,
                security_alerts: e.target.checked
              }))}
              disabled={!notifications.email_notifications}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Marketing emails</label>
              <p className="text-sm text-gray-500">Product updates, tips, and promotional content</p>
            </div>
            <input
              type="checkbox"
              checked={notifications.marketing_emails}
              onChange={(e) => setNotifications(prev => ({
                ...prev,
                marketing_emails: e.target.checked
              }))}
              disabled={!notifications.email_notifications}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded disabled:opacity-50"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderPrivacyTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Privacy Settings</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Profile visibility</label>
              <p className="text-sm text-gray-500">Control who can see your profile information</p>
            </div>
            <select
              value={privacy.profile_visibility}
              onChange={(e) => setPrivacy(prev => ({
                ...prev,
                profile_visibility: e.target.value as 'public' | 'private'
              }))}
              className="block w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            >
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Analytics tracking</label>
              <p className="text-sm text-gray-500">Help improve the service with anonymous usage data</p>
            </div>
            <input
              type="checkbox"
              checked={privacy.analytics_tracking}
              onChange={(e) => setPrivacy(prev => ({
                ...prev,
                analytics_tracking: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Error reporting</label>
              <p className="text-sm text-gray-500">Automatically send error reports to help fix issues</p>
            </div>
            <input
              type="checkbox"
              checked={privacy.error_reporting}
              onChange={(e) => setPrivacy(prev => ({
                ...prev,
                error_reporting: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Usage statistics</label>
              <p className="text-sm text-gray-500">Share anonymous usage statistics for product improvement</p>
            </div>
            <input
              type="checkbox"
              checked={privacy.usage_statistics}
              onChange={(e) => setPrivacy(prev => ({
                ...prev,
                usage_statistics: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderAppearanceTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Theme</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Color theme</label>
              <p className="text-sm text-gray-500">Choose your preferred color theme</p>
            </div>
            <select
              value={appearance.theme}
              onChange={(e) => setAppearance(prev => ({
                ...prev,
                theme: e.target.value as 'light' | 'dark' | 'system'
              }))}
              className="block w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Compact mode</label>
              <p className="text-sm text-gray-500">Use a more compact layout to show more content</p>
            </div>
            <input
              type="checkbox"
              checked={appearance.compact_mode}
              onChange={(e) => setAppearance(prev => ({
                ...prev,
                compact_mode: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Show animations</label>
              <p className="text-sm text-gray-500">Enable smooth transitions and animations</p>
            </div>
            <input
              type="checkbox"
              checked={appearance.show_animations}
              onChange={(e) => setAppearance(prev => ({
                ...prev,
                show_animations: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Sidebar collapsed</label>
              <p className="text-sm text-gray-500">Start with the sidebar collapsed by default</p>
            </div>
            <input
              type="checkbox"
              checked={appearance.sidebar_collapsed}
              onChange={(e) => setAppearance(prev => ({
                ...prev,
                sidebar_collapsed: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderDataTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Data Management</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Auto-delete completed tasks</label>
              <p className="text-sm text-gray-500">Automatically delete old completed tasks</p>
            </div>
            <input
              type="checkbox"
              checked={data.auto_delete_tasks}
              onChange={(e) => setData(prev => ({
                ...prev,
                auto_delete_tasks: e.target.checked
              }))}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          {data.auto_delete_tasks && (
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Delete after (days)</label>
                <p className="text-sm text-gray-500">Number of days to keep completed tasks</p>
              </div>
              <input
                type="number"
                min="7"
                max="365"
                value={data.auto_delete_days}
                onChange={(e) => setData(prev => ({
                  ...prev,
                  auto_delete_days: parseInt(e.target.value) || 90
                }))}
                className="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          )}

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Default export format</label>
              <p className="text-sm text-gray-500">Preferred format for data exports</p>
            </div>
            <select
              value={data.export_format}
              onChange={(e) => setData(prev => ({
                ...prev,
                export_format: e.target.value as 'json' | 'csv' | 'xlsx'
              }))}
              className="block w-24 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="xlsx">Excel</option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Timezone</label>
              <p className="text-sm text-gray-500">Your preferred timezone for displaying dates</p>
            </div>
            <select
              value={data.timezone}
              onChange={(e) => setData(prev => ({
                ...prev,
                timezone: e.target.value
              }))}
              className="block w-40 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            >
              <option value="UTC">UTC</option>
              <option value="America/New_York">Eastern Time</option>
              <option value="America/Chicago">Central Time</option>
              <option value="America/Denver">Mountain Time</option>
              <option value="America/Los_Angeles">Pacific Time</option>
              <option value="Europe/London">London</option>
              <option value="Europe/Paris">Paris</option>
              <option value="Asia/Tokyo">Tokyo</option>
              <option value="Asia/Shanghai">Shanghai</option>
            </select>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 pt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Data Operations</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Export all data</label>
              <p className="text-sm text-gray-500">Download a complete archive of your account data</p>
            </div>
            <button
              onClick={handleExportData}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <Download className="w-4 h-4 mr-1" />
              Export
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Clear cache</label>
              <p className="text-sm text-gray-500">Clear stored data and refresh the application</p>
            </div>
            <button
              onClick={handleClearCache}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              Clear Cache
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center">
                <SettingsIcon className="w-6 h-6 mr-2" />
                Settings
              </h1>
              <p className="text-gray-600 mt-1">
                Customize your experience and manage your preferences
              </p>
            </div>
            
            <button
              onClick={handleSaveSettings}
              disabled={isSaving}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar Navigation */}
          <div className="lg:col-span-1">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full group flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                      activeTab === tab.id
                        ? 'bg-primary-100 text-primary-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    {tab.name}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <div className="bg-white shadow rounded-lg p-6">
              {activeTab === 'notifications' && renderNotificationsTab()}
              {activeTab === 'privacy' && renderPrivacyTab()}
              {activeTab === 'appearance' && renderAppearanceTab()}
              {activeTab === 'data' && renderDataTab()}
            </div>
          </div>
        </div>

        {/* Information Section */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-md p-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <AlertCircle className="h-5 w-5 text-blue-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                Settings Information
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <ul className="list-disc list-inside space-y-1">
                  <li>Settings are saved automatically and applied immediately</li>
                  <li>Some changes may require a page refresh to take effect</li>
                  <li>Your preferences are stored securely and privately</li>
                  <li>You can reset settings to defaults by contacting support</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;