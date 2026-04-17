'use client';

import React, { useState } from 'react';
import VariableAutocomplete from './VariableAutocomplete';

interface ToolNodeConfigProps {
  config: Record<string, any>;
  onUpdate: (config: Record<string, any>) => void;
  availableVariables: string[];
}

export default function ToolNodeConfig({ config, onUpdate, availableVariables }: ToolNodeConfigProps) {
  const [apiEndpoint, setApiEndpoint] = useState(config.api_endpoint || '');
  const [httpMethod, setHttpMethod] = useState(config.http_method || 'GET');
  const [headers, setHeaders] = useState(JSON.stringify(config.headers || {}, null, 2));
  const [requestBody, setRequestBody] = useState(config.request_body || '');
  const [timeoutMs, setTimeoutMs] = useState(config.timeout_ms || 5000);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateAndUpdate = () => {
    const newErrors: Record<string, string> = {};

    if (!apiEndpoint.trim()) {
      newErrors.api_endpoint = 'API endpoint is required';
    }

    // Validate headers JSON
    let parsedHeaders = {};
    try {
      parsedHeaders = JSON.parse(headers);
      if (typeof parsedHeaders !== 'object' || Array.isArray(parsedHeaders)) {
        newErrors.headers = 'Headers must be a valid JSON object';
      }
    } catch (e) {
      newErrors.headers = 'Invalid JSON format';
    }

    if (timeoutMs < 100 || timeoutMs > 30000) {
      newErrors.timeout_ms = 'Timeout must be between 100 and 30000 ms';
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onUpdate({
        api_endpoint: apiEndpoint,
        http_method: httpMethod,
        headers: parsedHeaders,
        request_body: requestBody,
        timeout_ms: timeoutMs,
      });
    }
  };

  React.useEffect(() => {
    validateAndUpdate();
  }, [apiEndpoint, httpMethod, headers, requestBody, timeoutMs]);

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Tool Node Configuration</h4>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          API Endpoint <span className="text-red-500">*</span>
        </label>
        <VariableAutocomplete
          value={apiEndpoint}
          onChange={setApiEndpoint}
          availableVariables={availableVariables}
          placeholder="https://api.example.com/endpoint"
          rows={1}
        />
        {errors.api_endpoint && (
          <p className="text-xs text-red-500 mt-1">{errors.api_endpoint}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Full URL of the API endpoint. Supports {'{{variable}}'} syntax
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          HTTP Method <span className="text-red-500">*</span>
        </label>
        <select
          value={httpMethod}
          onChange={(e) => setHttpMethod(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
          <option value="DELETE">DELETE</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Headers (JSON)
        </label>
        <textarea
          value={headers}
          onChange={(e) => setHeaders(e.target.value)}
          placeholder='{"Content-Type": "application/json"}'
          rows={4}
          className={`w-full px-3 py-2 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.headers ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.headers && (
          <p className="text-xs text-red-500 mt-1">{errors.headers}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          HTTP headers as JSON object
        </p>
      </div>

      {(httpMethod === 'POST' || httpMethod === 'PUT') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Request Body
          </label>
          <VariableAutocomplete
            value={requestBody}
            onChange={setRequestBody}
            availableVariables={availableVariables}
            placeholder='{"key": "{{trigger_output}}"}'
            rows={5}
          />
          <p className="text-xs text-gray-500 mt-1">
            JSON request body. Use {'{{variable}}'} syntax for dynamic values
          </p>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Timeout (ms) <span className="text-red-500">*</span>
        </label>
        <input
          type="number"
          value={timeoutMs}
          onChange={(e) => setTimeoutMs(parseInt(e.target.value) || 5000)}
          min="100"
          max="30000"
          step="100"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.timeout_ms ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.timeout_ms && (
          <p className="text-xs text-red-500 mt-1">{errors.timeout_ms}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Request timeout in milliseconds (100-30000)
        </p>
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
              onClick={() => setRequestBody(requestBody + `{{${variable}}}`)}
            >
              {`{{${variable}}}`}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}
