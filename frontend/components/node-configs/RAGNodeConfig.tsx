'use client';

import React, { useState } from 'react';
import VariableAutocomplete from './VariableAutocomplete';

interface RAGNodeConfigProps {
  config: Record<string, any>;
  onUpdate: (config: Record<string, any>) => void;
  availableVariables: string[];
}

export default function RAGNodeConfig({ config, onUpdate, availableVariables }: RAGNodeConfigProps) {
  const [collectionName, setCollectionName] = useState(config.collection_name || '');
  const [queryTemplate, setQueryTemplate] = useState(config.query_template || '{{trigger_output}}');
  const [resultLimit, setResultLimit] = useState(config.result_limit || 5);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateAndUpdate = () => {
    const newErrors: Record<string, string> = {};

    if (!collectionName.trim()) {
      newErrors.collection_name = 'Collection name is required';
    }

    if (!queryTemplate.trim()) {
      newErrors.query_template = 'Query template is required';
    }

    if (resultLimit < 1 || resultLimit > 50) {
      newErrors.result_limit = 'Result limit must be between 1 and 50';
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onUpdate({
        collection_name: collectionName,
        query_template: queryTemplate,
        result_limit: resultLimit,
      });
    }
  };

  React.useEffect(() => {
    validateAndUpdate();
  }, [collectionName, queryTemplate, resultLimit]);

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">RAG Node Configuration</h4>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Collection Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={collectionName}
          onChange={(e) => setCollectionName(e.target.value)}
          placeholder="my_knowledge_base"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.collection_name ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.collection_name && (
          <p className="text-xs text-red-500 mt-1">{errors.collection_name}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          The Qdrant collection to search
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Query Template <span className="text-red-500">*</span>
        </label>
        <VariableAutocomplete
          value={queryTemplate}
          onChange={setQueryTemplate}
          availableVariables={availableVariables}
          placeholder="{{trigger_output}}"
          rows={3}
        />
        {errors.query_template && (
          <p className="text-xs text-red-500 mt-1">{errors.query_template}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Use {'{{variable}}'} syntax to reference context variables
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Result Limit <span className="text-red-500">*</span>
        </label>
        <input
          type="number"
          value={resultLimit}
          onChange={(e) => setResultLimit(parseInt(e.target.value) || 5)}
          min="1"
          max="50"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.result_limit ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.result_limit && (
          <p className="text-xs text-red-500 mt-1">{errors.result_limit}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Number of documents to retrieve (1-50)
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
              onClick={() => setQueryTemplate(queryTemplate + `{{${variable}}}`)}
            >
              {`{{${variable}}}`}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}
