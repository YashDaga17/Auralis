'use client';

import React, { useState } from 'react';
import VariableAutocomplete from './VariableAutocomplete';

interface Intent {
  name: string;
  description: string;
  confidence_threshold: number;
}

interface DecisionNodeConfigProps {
  config: Record<string, any>;
  onUpdate: (config: Record<string, any>) => void;
  availableVariables: string[];
}

export default function DecisionNodeConfig({ config, onUpdate, availableVariables }: DecisionNodeConfigProps) {
  const [classificationPrompt, setClassificationPrompt] = useState(
    config.classification_prompt || 'Classify the user intent.'
  );
  const [intents, setIntents] = useState<Intent[]>(config.intents || []);
  const [fallbackIntent, setFallbackIntent] = useState(config.fallback_intent || 'unknown');
  const [errors, setErrors] = useState<Record<string, string>>({});

  // New intent form state
  const [newIntentName, setNewIntentName] = useState('');
  const [newIntentDescription, setNewIntentDescription] = useState('');
  const [newIntentThreshold, setNewIntentThreshold] = useState(0.7);

  const validateAndUpdate = () => {
    const newErrors: Record<string, string> = {};

    if (!classificationPrompt.trim()) {
      newErrors.classification_prompt = 'Classification prompt is required';
    }

    if (intents.length === 0) {
      newErrors.intents = 'At least one intent is required';
    }

    if (!fallbackIntent.trim()) {
      newErrors.fallback_intent = 'Fallback intent is required';
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onUpdate({
        classification_prompt: classificationPrompt,
        intents,
        fallback_intent: fallbackIntent,
      });
    }
  };

  React.useEffect(() => {
    validateAndUpdate();
  }, [classificationPrompt, intents, fallbackIntent]);

  const addIntent = () => {
    if (!newIntentName.trim() || !newIntentDescription.trim()) {
      return;
    }

    const newIntent: Intent = {
      name: newIntentName.trim(),
      description: newIntentDescription.trim(),
      confidence_threshold: newIntentThreshold,
    };

    setIntents([...intents, newIntent]);
    setNewIntentName('');
    setNewIntentDescription('');
    setNewIntentThreshold(0.7);
  };

  const removeIntent = (index: number) => {
    setIntents(intents.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Decision Node Configuration</h4>
      
      <div className="p-3 bg-purple-50 rounded-lg text-sm text-purple-900">
        <p className="font-medium mb-1">About Decision Nodes</p>
        <p className="text-xs">
          Decision nodes classify user intent and route the conversation flow to different branches.
          Each intent can connect to a different downstream node.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Classification Prompt <span className="text-red-500">*</span>
        </label>
        <VariableAutocomplete
          value={classificationPrompt}
          onChange={setClassificationPrompt}
          availableVariables={availableVariables}
          placeholder="Classify the user intent based on their message."
          rows={3}
        />
        {errors.classification_prompt && (
          <p className="text-xs text-red-500 mt-1">{errors.classification_prompt}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Instructions for the LLM on how to classify intents
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Intents <span className="text-red-500">*</span>
        </label>
        
        {/* Intent List */}
        <div className="space-y-2 mb-3">
          {intents.map((intent, index) => (
            <div key={index} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="font-medium text-sm text-gray-900">{intent.name}</p>
                  <p className="text-xs text-gray-600 mt-1">{intent.description}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Confidence threshold: {intent.confidence_threshold}
                  </p>
                </div>
                <button
                  onClick={() => removeIntent(index)}
                  className="ml-2 text-red-500 hover:text-red-700 text-sm"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
          
          {intents.length === 0 && (
            <p className="text-sm text-gray-500 italic">No intents defined yet</p>
          )}
        </div>
        
        {errors.intents && (
          <p className="text-xs text-red-500 mb-2">{errors.intents}</p>
        )}

        {/* Add Intent Form */}
        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 space-y-3">
          <p className="text-sm font-medium text-blue-900">Add New Intent</p>
          
          <div>
            <input
              type="text"
              value={newIntentName}
              onChange={(e) => setNewIntentName(e.target.value)}
              placeholder="Intent name (e.g., book_appointment)"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          
          <div>
            <textarea
              value={newIntentDescription}
              onChange={(e) => setNewIntentDescription(e.target.value)}
              placeholder="Intent description (e.g., User wants to schedule a meeting)"
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-700">Confidence:</label>
            <input
              type="number"
              value={newIntentThreshold}
              onChange={(e) => setNewIntentThreshold(parseFloat(e.target.value) || 0.7)}
              min="0"
              max="1"
              step="0.05"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          
          <button
            onClick={addIntent}
            disabled={!newIntentName.trim() || !newIntentDescription.trim()}
            className="w-full px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Add Intent
          </button>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Fallback Intent <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={fallbackIntent}
          onChange={(e) => setFallbackIntent(e.target.value)}
          placeholder="unknown"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.fallback_intent ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.fallback_intent && (
          <p className="text-xs text-red-500 mt-1">{errors.fallback_intent}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Intent to use when classification confidence is below threshold
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
              onClick={() => setClassificationPrompt(classificationPrompt + `{{${variable}}}`)}
            >
              {`{{${variable}}}`}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}
