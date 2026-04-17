'use client';

import React, { useState } from 'react';

interface ActionNodeConfigProps {
  config: Record<string, any>;
  onUpdate: (config: Record<string, any>) => void;
  availableVariables: string[];
}

export default function ActionNodeConfig({ config, onUpdate, availableVariables }: ActionNodeConfigProps) {
  const [integration, setIntegration] = useState(config.integration || 'hubspot');
  const [actionType, setActionType] = useState(config.action_type || '');
  const [parameters, setParameters] = useState(JSON.stringify(config.parameters || {}, null, 2));
  const [requireConfirmation, setRequireConfirmation] = useState(config.require_confirmation || false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const actionTypesByIntegration: Record<string, string[]> = {
    hubspot: ['create_contact', 'update_contact', 'create_deal', 'add_note'],
    calendly: ['book_appointment', 'cancel_appointment', 'reschedule_appointment'],
    zendesk: ['create_ticket', 'update_ticket', 'add_comment'],
    salesforce: ['create_lead', 'update_opportunity', 'create_task'],
  };

  const validateAndUpdate = () => {
    const newErrors: Record<string, string> = {};

    if (!actionType.trim()) {
      newErrors.action_type = 'Action type is required';
    }

    // Validate parameters JSON
    let parsedParameters = {};
    try {
      parsedParameters = JSON.parse(parameters);
      if (typeof parsedParameters !== 'object' || Array.isArray(parsedParameters)) {
        newErrors.parameters = 'Parameters must be a valid JSON object';
      }
    } catch (e) {
      newErrors.parameters = 'Invalid JSON format';
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onUpdate({
        integration,
        action_type: actionType,
        parameters: parsedParameters,
        require_confirmation: requireConfirmation,
      });
    }
  };

  React.useEffect(() => {
    validateAndUpdate();
  }, [integration, actionType, parameters, requireConfirmation]);

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Action Node Configuration</h4>
      
      <div className="p-3 bg-yellow-50 rounded-lg text-sm text-yellow-900">
        <p className="font-medium mb-1">⚠️ External Integration</p>
        <p className="text-xs">
          This node executes actions in external systems. Ensure proper authentication is configured.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Integration <span className="text-red-500">*</span>
        </label>
        <select
          value={integration}
          onChange={(e) => {
            setIntegration(e.target.value);
            setActionType(''); // Reset action type when integration changes
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="hubspot">HubSpot</option>
          <option value="calendly">Calendly</option>
          <option value="zendesk">Zendesk</option>
          <option value="salesforce">Salesforce</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Action Type <span className="text-red-500">*</span>
        </label>
        <select
          value={actionType}
          onChange={(e) => setActionType(e.target.value)}
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.action_type ? 'border-red-500' : 'border-gray-300'
          }`}
        >
          <option value="">Select an action...</option>
          {actionTypesByIntegration[integration]?.map((type) => (
            <option key={type} value={type}>
              {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </option>
          ))}
        </select>
        {errors.action_type && (
          <p className="text-xs text-red-500 mt-1">{errors.action_type}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Parameters (JSON)
        </label>
        <textarea
          value={parameters}
          onChange={(e) => setParameters(e.target.value)}
          placeholder='{"email": "{{trigger_output}}", "name": "John Doe"}'
          rows={6}
          className={`w-full px-3 py-2 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.parameters ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.parameters && (
          <p className="text-xs text-red-500 mt-1">{errors.parameters}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Action parameters as JSON. Use {'{{variable}}'} syntax for dynamic values
        </p>
      </div>

      <div className="flex items-center">
        <input
          type="checkbox"
          id="require_confirmation"
          checked={requireConfirmation}
          onChange={(e) => setRequireConfirmation(e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label htmlFor="require_confirmation" className="ml-2 block text-sm text-gray-700">
          Require user confirmation before executing
        </label>
      </div>

      <div className="pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-600">
          <strong>Available Variables:</strong>
        </p>
        <div className="flex flex-wrap gap-1 mt-2">
          {availableVariables.map((variable) => (
            <code
              key={variable}
              className="text-xs bg-gray-100 px-2 py-1 rounded cursor-pointer hover:bg-gray-200"
              onClick={() => {
                try {
                  const parsed = JSON.parse(parameters);
                  parsed[`new_field_${Object.keys(parsed).length + 1}`] = `{{${variable}}}`;
                  setParameters(JSON.stringify(parsed, null, 2));
                } catch (e) {
                  // If invalid JSON, just append
                  setParameters(parameters + `\n"field": "{{${variable}}}"`);
                }
              }}
            >
              {`{{${variable}}}`}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}
