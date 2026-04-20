'use client';

import React, { useState, useEffect } from 'react';
import { createApiClient } from '@/lib/api-client';

interface UserPreference {
  user_id: string;
  communication_style: 'concise' | 'detailed' | 'technical';
  preferred_sources: string[];
  notification_preferences: {
    email_notifications?: boolean;
    sms_notifications?: boolean;
    in_app_notifications?: boolean;
  };
}

interface UserPreferencesPanelProps {
  token: string;
  userId: string;
  agentId?: string;
  onClose: () => void;
}

export default function UserPreferencesPanel({
  token,
  userId,
  agentId,
  onClose,
}: UserPreferencesPanelProps) {
  const [preferences, setPreferences] = useState<UserPreference>({
    user_id: userId,
    communication_style: 'detailed',
    preferred_sources: [],
    notification_preferences: {
      email_notifications: true,
      sms_notifications: false,
      in_app_notifications: true,
    },
  });
  const [availableCollections, setAvailableCollections] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadPreferences();
    loadAvailableCollections();
  }, [userId, agentId]);

  const loadPreferences = async () => {
    try {
      const apiClient = createApiClient(token);
      const params = agentId ? { agent_id: agentId } : {};
      const response = await apiClient.get(`/api/preferences/${userId}`, { params });
      
      if (response.data) {
        setPreferences({
          ...preferences,
          ...response.data,
        });
      }
    } catch (err: any) {
      // If preferences don't exist yet, that's okay - we'll create them on save
      if (err.response?.status !== 404) {
        console.error('Error loading preferences:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadAvailableCollections = async () => {
    try {
      const apiClient = createApiClient(token);
      const response = await apiClient.get('/api/knowledge/collections');
      setAvailableCollections(response.data.collections || []);
    } catch (err) {
      console.error('Error loading collections:', err);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const apiClient = createApiClient(token);
      const payload = {
        ...preferences,
        agent_id: agentId || null,
      };

      await apiClient.post('/api/preferences', payload);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const togglePreferredSource = (collection: string) => {
    setPreferences((prev) => {
      const sources = prev.preferred_sources.includes(collection)
        ? prev.preferred_sources.filter((s) => s !== collection)
        : [...prev.preferred_sources, collection];
      return { ...prev, preferred_sources: sources };
    });
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl p-6">
          <p className="text-gray-600">Loading preferences...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white">
          <h2 className="text-2xl font-semibold text-gray-800">User Preferences</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Communication Style */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Communication Style
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Choose how the agent should respond to you
            </p>
            <div className="space-y-2">
              <label className="flex items-center p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="communication_style"
                  value="concise"
                  checked={preferences.communication_style === 'concise'}
                  onChange={(e) =>
                    setPreferences({ ...preferences, communication_style: e.target.value as any })
                  }
                  className="mr-3"
                />
                <div>
                  <div className="font-medium text-gray-800">Concise</div>
                  <div className="text-xs text-gray-600">
                    Brief, to-the-point responses (2-3 sentences)
                  </div>
                </div>
              </label>

              <label className="flex items-center p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="communication_style"
                  value="detailed"
                  checked={preferences.communication_style === 'detailed'}
                  onChange={(e) =>
                    setPreferences({ ...preferences, communication_style: e.target.value as any })
                  }
                  className="mr-3"
                />
                <div>
                  <div className="font-medium text-gray-800">Detailed</div>
                  <div className="text-xs text-gray-600">
                    Comprehensive explanations with context and examples
                  </div>
                </div>
              </label>

              <label className="flex items-center p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="communication_style"
                  value="technical"
                  checked={preferences.communication_style === 'technical'}
                  onChange={(e) =>
                    setPreferences({ ...preferences, communication_style: e.target.value as any })
                  }
                  className="mr-3"
                />
                <div>
                  <div className="font-medium text-gray-800">Technical</div>
                  <div className="text-xs text-gray-600">
                    Precise terminology with technical depth and metrics
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Preferred Sources */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preferred Knowledge Sources
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Select collections to prioritize in search results (1.5x boost)
            </p>
            {availableCollections.length === 0 ? (
              <p className="text-sm text-gray-500 italic">
                No collections available. Upload documents to create collections.
              </p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-200 rounded-lg p-3">
                {availableCollections.map((collection) => (
                  <label
                    key={collection}
                    className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={preferences.preferred_sources.includes(collection)}
                      onChange={() => togglePreferredSource(collection)}
                      className="mr-3"
                    />
                    <span className="text-sm text-gray-800">{collection}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Notification Preferences */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Notification Preferences
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Choose how you want to receive notifications
            </p>
            <div className="space-y-2">
              <label className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.notification_preferences.email_notifications ?? true}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      notification_preferences: {
                        ...preferences.notification_preferences,
                        email_notifications: e.target.checked,
                      },
                    })
                  }
                  className="mr-3"
                />
                <span className="text-sm text-gray-800">Email Notifications</span>
              </label>

              <label className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.notification_preferences.sms_notifications ?? false}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      notification_preferences: {
                        ...preferences.notification_preferences,
                        sms_notifications: e.target.checked,
                      },
                    })
                  }
                  className="mr-3"
                />
                <span className="text-sm text-gray-800">SMS Notifications</span>
              </label>

              <label className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.notification_preferences.in_app_notifications ?? true}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      notification_preferences: {
                        ...preferences.notification_preferences,
                        in_app_notifications: e.target.checked,
                      },
                    })
                  }
                  className="mr-3"
                />
                <span className="text-sm text-gray-800">In-App Notifications</span>
              </label>
            </div>
          </div>

          {/* Error/Success Messages */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {success && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-800">Preferences saved successfully!</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 flex justify-end gap-3 sticky bottom-0 bg-white">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
}
