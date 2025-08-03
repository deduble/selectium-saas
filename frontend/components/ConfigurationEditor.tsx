import React, { useState, useCallback } from 'react';
import { Settings, Edit, Save, X, Plus, Trash2 } from 'lucide-react';
import { Task, TaskConfig } from '../types/api';
import toast from 'react-hot-toast';

// Form data interface for configuration editing
interface ConfigFormData {
  urls: string[];
  selectors: Record<string, string>;
  options: {
    output_format: 'json' | 'csv' | 'xlsx';
    include_metadata: boolean;
    follow_redirects: boolean;
    timeout: number;
  };
}

// Validation errors interface
interface ValidationErrors {
  [key: string]: string;
}

// Props interfaces
interface ConfigurationEditorProps {
  task: Task;
  onSave: (config: TaskConfig) => Promise<void>;
  isLoading?: boolean;
  readOnly?: boolean;
}

interface ConfigurationDisplayProps {
  config: TaskConfig;
}

interface ConfigurationFormProps {
  formData: ConfigFormData;
  onChange: (data: ConfigFormData) => void;
  errors: ValidationErrors;
}

// Configuration Display Component (Read-only)
const ConfigurationDisplay: React.FC<ConfigurationDisplayProps> = ({ config }) => {
  return (
    <div className="space-y-4">
      {/* URLs Section */}
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-2">URLs</h3>
        <div className="bg-gray-50 rounded-md p-3">
          {config.urls && config.urls.length > 0 ? (
            <div className="space-y-1">
              {config.urls.map((url, index) => (
                <div key={index} className="text-sm text-gray-700 break-all">
                  {url}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-gray-500 italic">No URLs configured</div>
          )}
        </div>
      </div>

      {/* Selectors Section */}
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-2">Selectors</h3>
        <div className="bg-gray-50 rounded-md p-3">
          {config.selectors && Object.keys(config.selectors).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(config.selectors).map(([name, selector]) => (
                <div key={name} className="flex justify-between items-start">
                  <div className="text-sm font-medium text-gray-700">{name}:</div>
                  <div className="text-sm text-gray-600 ml-2 flex-1 text-right break-all">
                    <code className="bg-gray-200 px-1 rounded">{selector}</code>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-gray-500 italic">No selectors configured</div>
          )}
        </div>
      </div>

      {/* Options Section */}
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-2">Options</h3>
        <div className="bg-gray-50 rounded-md p-3">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-700">Output Format:</span>
              <span className="text-gray-900 font-medium uppercase">{config.output_format || 'json'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-700">Include Metadata:</span>
              <span className="text-gray-900 font-medium">{config.include_metadata ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-700">Follow Redirects:</span>
              <span className="text-gray-900 font-medium">{config.follow_redirects ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-700">Timeout:</span>
              <span className="text-gray-900 font-medium">{config.timeout || 30}s</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Configuration Form Component (Editable)
const ConfigurationForm: React.FC<ConfigurationFormProps> = ({ formData, onChange, errors }) => {
  // URL management
  const addUrl = () => {
    onChange({
      ...formData,
      urls: [...formData.urls, '']
    });
  };

  const removeUrl = (index: number) => {
    onChange({
      ...formData,
      urls: formData.urls.filter((_, i) => i !== index)
    });
  };

  const updateUrl = (index: number, value: string) => {
    const newUrls = [...formData.urls];
    newUrls[index] = value;
    onChange({
      ...formData,
      urls: newUrls
    });
  };

  // Selector management
  const addSelector = () => {
    const newSelectors = { ...formData.selectors };
    let newKey = 'selector1';
    let counter = 1;
    while (newSelectors[newKey]) {
      counter++;
      newKey = `selector${counter}`;
    }
    newSelectors[newKey] = '';
    onChange({
      ...formData,
      selectors: newSelectors
    });
  };

  const removeSelector = (key: string) => {
    const newSelectors = { ...formData.selectors };
    delete newSelectors[key];
    onChange({
      ...formData,
      selectors: newSelectors
    });
  };

  const updateSelector = (oldKey: string, newKey: string, value: string) => {
    const newSelectors = { ...formData.selectors };
    delete newSelectors[oldKey];
    newSelectors[newKey] = value;
    onChange({
      ...formData,
      selectors: newSelectors
    });
  };

  const updateSelectorKey = (oldKey: string, newKey: string) => {
    if (oldKey === newKey) return;
    const newSelectors = { ...formData.selectors };
    const value = newSelectors[oldKey];
    delete newSelectors[oldKey];
    newSelectors[newKey] = value;
    onChange({
      ...formData,
      selectors: newSelectors
    });
  };

  const updateSelectorValue = (key: string, value: string) => {
    onChange({
      ...formData,
      selectors: {
        ...formData.selectors,
        [key]: value
      }
    });
  };

  return (
    <div className="space-y-6">
      {/* URLs Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-sm font-medium text-gray-900">URLs</label>
          <button
            type="button"
            onClick={addUrl}
            className="inline-flex items-center px-2 py-1 text-xs font-medium rounded text-primary-600 bg-primary-50 hover:bg-primary-100"
          >
            <Plus className="w-3 h-3 mr-1" />
            Add URL
          </button>
        </div>
        <div className="space-y-2">
          {formData.urls.map((url, index) => (
            <div key={index} className="flex items-center space-x-2">
              <input
                type="url"
                value={url}
                onChange={(e) => updateUrl(index, e.target.value)}
                placeholder="https://example.com"
                className={`flex-1 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                  errors[`url-${index}`] ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {formData.urls.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeUrl(index)}
                  className="p-1 text-red-600 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
        {errors.urls && (
          <p className="mt-1 text-sm text-red-600">{errors.urls}</p>
        )}
      </div>

      {/* Selectors Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-sm font-medium text-gray-900">Selectors</label>
          <button
            type="button"
            onClick={addSelector}
            className="inline-flex items-center px-2 py-1 text-xs font-medium rounded text-primary-600 bg-primary-50 hover:bg-primary-100"
          >
            <Plus className="w-3 h-3 mr-1" />
            Add Selector
          </button>
        </div>
        <div className="space-y-3">
          {Object.entries(formData.selectors).map(([key, value]) => (
            <div key={key} className="flex items-center space-x-2">
              <input
                type="text"
                value={key}
                onChange={(e) => updateSelectorKey(key, e.target.value)}
                placeholder="Field name"
                className="w-32 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <input
                type="text"
                value={value}
                onChange={(e) => updateSelectorValue(key, e.target.value)}
                placeholder="CSS selector (e.g., .title, #content)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              {Object.keys(formData.selectors).length > 1 && (
                <button
                  type="button"
                  onClick={() => removeSelector(key)}
                  className="p-1 text-red-600 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
        {errors.selectors && (
          <p className="mt-1 text-sm text-red-600">{errors.selectors}</p>
        )}
      </div>

      {/* Options Section */}
      <div>
        <label className="text-sm font-medium text-gray-900 mb-3 block">Options</label>
        <div className="space-y-4 bg-gray-50 rounded-md p-4">
          {/* Output Format */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Output Format</label>
            <select
              value={formData.options.output_format}
              onChange={(e) => onChange({
                ...formData,
                options: {
                  ...formData.options,
                  output_format: e.target.value as 'json' | 'csv' | 'xlsx'
                }
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="xlsx">Excel (XLSX)</option>
            </select>
          </div>

          {/* Timeout */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">
              Timeout (seconds)
            </label>
            <input
              type="number"
              min="5"
              max="300"
              value={formData.options.timeout}
              onChange={(e) => onChange({
                ...formData,
                options: {
                  ...formData.options,
                  timeout: parseInt(e.target.value) || 30
                }
              })}
              className={`w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                errors.timeout ? 'border-red-300' : 'border-gray-300'
              }`}
            />
            {errors.timeout && (
              <p className="mt-1 text-sm text-red-600">{errors.timeout}</p>
            )}
          </div>

          {/* Boolean Options */}
          <div className="space-y-3">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="include_metadata"
                checked={formData.options.include_metadata}
                onChange={(e) => onChange({
                  ...formData,
                  options: {
                    ...formData.options,
                    include_metadata: e.target.checked
                  }
                })}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label htmlFor="include_metadata" className="ml-2 text-sm text-gray-700">
                Include metadata in results
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="follow_redirects"
                checked={formData.options.follow_redirects}
                onChange={(e) => onChange({
                  ...formData,
                  options: {
                    ...formData.options,
                    follow_redirects: e.target.checked
                  }
                })}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label htmlFor="follow_redirects" className="ml-2 text-sm text-gray-700">
                Follow redirects automatically
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main Configuration Editor Component
const ConfigurationEditor: React.FC<ConfigurationEditorProps> = ({
  task,
  onSave,
  isLoading = false,
  readOnly = false
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<ConfigFormData>(() => ({
    urls: task.config.urls || [''],
    selectors: task.config.selectors || {},
    options: {
      output_format: task.config.output_format || 'json',
      include_metadata: task.config.include_metadata ?? true,
      follow_redirects: task.config.follow_redirects ?? true,
      timeout: task.config.timeout || 30
    }
  }));
  const [errors, setErrors] = useState<ValidationErrors>({});

  // Validation function
  const validateForm = useCallback((): boolean => {
    const newErrors: ValidationErrors = {};

    // URL validation
    if (formData.urls.length === 0 || formData.urls.every(url => !url.trim())) {
      newErrors.urls = 'At least one URL is required';
    } else {
      formData.urls.forEach((url, index) => {
        if (url.trim()) {
          try {
            new URL(url);
          } catch {
            newErrors[`url-${index}`] = 'Invalid URL format';
          }
        }
      });
    }

    // Selectors validation
    if (Object.keys(formData.selectors).length === 0) {
      newErrors.selectors = 'At least one selector is required';
    } else {
      const hasValidSelector = Object.entries(formData.selectors).some(([key, value]) => 
        key.trim() && value.trim()
      );
      if (!hasValidSelector) {
        newErrors.selectors = 'At least one complete selector (name and CSS selector) is required';
      }
    }

    // Timeout validation
    if (formData.options.timeout < 5 || formData.options.timeout > 300) {
      newErrors.timeout = 'Timeout must be between 5 and 300 seconds';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  // Save handler
  const handleSave = async () => {
    if (!validateForm()) {
      toast.error('Please fix validation errors before saving');
      return;
    }

    try {
      // Filter out empty URLs and selectors
      const cleanUrls = formData.urls.filter(url => url.trim());
      const cleanSelectors = Object.fromEntries(
        Object.entries(formData.selectors).filter(([key, value]) => key.trim() && value.trim())
      );

      const config: TaskConfig = {
        urls: cleanUrls,
        selectors: cleanSelectors,
        output_format: formData.options.output_format,
        include_metadata: formData.options.include_metadata,
        follow_redirects: formData.options.follow_redirects,
        timeout: formData.options.timeout
      };

      await onSave(config);
      setIsEditing(false);
      toast.success('Configuration updated successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to save configuration');
    }
  };

  // Cancel handler
  const handleCancel = () => {
    setFormData({
      urls: task.config.urls || [''],
      selectors: task.config.selectors || {},
      options: {
        output_format: task.config.output_format || 'json',
        include_metadata: task.config.include_metadata ?? true,
        follow_redirects: task.config.follow_redirects ?? true,
        timeout: task.config.timeout || 30
      }
    });
    setErrors({});
    setIsEditing(false);
  };

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-gray-900 flex items-center">
          <Settings className="w-5 h-5 mr-2" />
          Configuration
        </h2>
        
        {!readOnly && (
          <div className="flex items-center space-x-2">
            {isEditing ? (
              <>
                <button
                  onClick={handleCancel}
                  disabled={isLoading}
                  className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <X className="w-4 h-4 mr-1" />
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={isLoading || Object.keys(errors).length > 0}
                  className="inline-flex items-center px-3 py-1.5 text-sm border border-transparent rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Save className="w-4 h-4 mr-1" />
                  {isLoading ? 'Saving...' : 'Save'}
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <Edit className="w-4 h-4 mr-1" />
                Edit
              </button>
            )}
          </div>
        )}
      </div>

      {isEditing ? (
        <ConfigurationForm
          formData={formData}
          onChange={setFormData}
          errors={errors}
        />
      ) : (
        <ConfigurationDisplay config={task.config} />
      )}
    </div>
  );
};

export default ConfigurationEditor;