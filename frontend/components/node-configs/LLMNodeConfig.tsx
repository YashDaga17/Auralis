'use client';

import React, { useState } from 'react';
import VariableAutocomplete from './VariableAutocomplete';

interface LLMNodeConfigProps {
  config: Record<string, any>;
  onUpdate: (config: Record<string, any>) => void;
  availableVariables: string[];
}

export default function LLMNodeConfig({ config, onUpdate, availableVariables }: LLMNodeConfigProps) {
  const [systemPrompt, setSystemPrompt] = useState(config.system_prompt || 'You are a helpful assistant.');
  const [userPrompt, setUserPrompt] = useState(config.user_prompt || '{{trigger_output}}');
  const [temperature, setTemperature] = useState(config.temperature || 0.7);
  const [maxTokens, setMaxTokens] = useState(config.max_tokens || 1024);
  const [model, setModel] = useState(config.model || 'gemini-2.5-flash');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateAndUpdate = () => {
    const newErrors: Record<string, string> = {};

    if (!systemPrompt.trim()) {
      newErrors.system_prompt = 'System prompt is required';
    }

    if (!userPrompt.trim()) {
      newErrors.user_prompt = 'User prompt is required';
    }

    if (temperature < 0 || temperature > 1) {
      newErrors.temperature = 'Temperature must be between 0 and 1';
    }

    if (maxTokens < 1 || maxTokens > 8192) {
      newErrors.max_tokens = 'Max tokens must be between 1 and 8192';
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onUpdate({
        system_prompt: systemPrompt,
        user_prompt: userPrompt,
        temperature,
        max_tokens: maxTokens,
        model,
      });
    }
  };

  React.useEffect(() => {
    validateAndUpdate();
  }, [systemPrompt, userPrompt, temperature, maxTokens, model]);

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">LLM Node Configuration</h4>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Model <span className="text-red-500">*</span>
        </label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="gemini-2.5-flash">Gemini 2.5 Flash (Fast)</option>
          <option value="gemini-2.5-pro">Gemini 2.5 Pro (Advanced)</option>
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Choose the LLM model to use
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          System Prompt <span className="text-red-500">*</span>
        </label>
        <VariableAutocomplete
          value={systemPrompt}
          onChange={setSystemPrompt}
          availableVariables={availableVariables}
          placeholder="You are a helpful assistant."
          rows={3}
        />
        {errors.system_prompt && (
          <p className="text-xs text-red-500 mt-1">{errors.system_prompt}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Define the AI's role and behavior
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          User Prompt <span className="text-red-500">*</span>
        </label>
        <VariableAutocomplete
          value={userPrompt}
          onChange={setUserPrompt}
          availableVariables={availableVariables}
          placeholder="{{trigger_output}}"
          rows={4}
        />
        {errors.user_prompt && (
          <p className="text-xs text-red-500 mt-1">{errors.user_prompt}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          The prompt sent to the LLM. Use {'{{variable}}'} syntax for context
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Temperature <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value) || 0.7)}
            min="0"
            max="1"
            step="0.1"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.temperature ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors.temperature && (
            <p className="text-xs text-red-500 mt-1">{errors.temperature}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">
            0 = deterministic, 1 = creative
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Tokens <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            value={maxTokens}
            onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1024)}
            min="1"
            max="8192"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.max_tokens ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors.max_tokens && (
            <p className="text-xs text-red-500 mt-1">{errors.max_tokens}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Maximum response length
          </p>
        </div>
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
              onClick={() => setUserPrompt(userPrompt + `{{${variable}}}`)}
            >
              {`{{${variable}}}`}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}
