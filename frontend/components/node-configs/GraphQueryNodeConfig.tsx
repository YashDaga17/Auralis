'use client';

import React, { useState } from 'react';

interface GraphQueryNodeConfigProps {
  config: Record<string, any>;
  onUpdate: (config: Record<string, any>) => void;
  availableVariables: string[];
}

export default function GraphQueryNodeConfig({ config, onUpdate, availableVariables }: GraphQueryNodeConfigProps) {
  const [maxDepth, setMaxDepth] = useState(config.max_depth || 3);
  const [entityTypes, setEntityTypes] = useState((config.entity_types || []).join(', '));
  const [relationshipTypes, setRelationshipTypes] = useState((config.relationship_types || []).join(', '));
  const [timeoutMs, setTimeoutMs] = useState(config.timeout_ms || 5000);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateAndUpdate = () => {
    const newErrors: Record<string, string> = {};

    if (maxDepth < 1 || maxDepth > 10) {
      newErrors.max_depth = 'Max depth must be between 1 and 10';
    }

    if (timeoutMs < 100 || timeoutMs > 30000) {
      newErrors.timeout_ms = 'Timeout must be between 100 and 30000 ms';
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onUpdate({
        max_depth: maxDepth,
        entity_types: entityTypes.split(',').map((t: string) => t.trim()).filter((t: string) => t),
        relationship_types: relationshipTypes.split(',').map((t: string) => t.trim()).filter((t: string) => t),
        timeout_ms: timeoutMs,
      });
    }
  };

  React.useEffect(() => {
    validateAndUpdate();
  }, [maxDepth, entityTypes, relationshipTypes, timeoutMs]);

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Graph Query Node Configuration</h4>
      
      <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-900">
        <p className="font-medium mb-1">About Graph Queries</p>
        <p className="text-xs">
          This node uses LLM to generate Cypher queries that traverse your knowledge graph,
          finding relationships between entities.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Max Depth <span className="text-red-500">*</span>
        </label>
        <input
          type="number"
          value={maxDepth}
          onChange={(e) => setMaxDepth(parseInt(e.target.value) || 3)}
          min="1"
          max="10"
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.max_depth ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.max_depth && (
          <p className="text-xs text-red-500 mt-1">{errors.max_depth}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Maximum number of relationship hops to traverse (1-10)
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Entity Types (Optional)
        </label>
        <input
          type="text"
          value={entityTypes}
          onChange={(e) => setEntityTypes(e.target.value)}
          placeholder="Person, Project, Product, Department"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="text-xs text-gray-500 mt-1">
          Comma-separated list of entity types to filter by (leave empty for all)
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Relationship Types (Optional)
        </label>
        <input
          type="text"
          value={relationshipTypes}
          onChange={(e) => setRelationshipTypes(e.target.value)}
          placeholder="MANAGES, OWNS, REPORTS_TO, WORKS_ON"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="text-xs text-gray-500 mt-1">
          Comma-separated list of relationship types to filter by (leave empty for all)
        </p>
      </div>

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
          Query timeout in milliseconds (100-30000)
        </p>
      </div>

      <div className="pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-600">
          <strong>Common Entity Types:</strong>
        </p>
        <div className="flex flex-wrap gap-1 mt-2">
          {['Person', 'Project', 'Product', 'Department', 'Document'].map((type) => (
            <code
              key={type}
              className="text-xs bg-gray-100 px-2 py-1 rounded cursor-pointer hover:bg-gray-200"
              onClick={() => setEntityTypes(entityTypes ? `${entityTypes}, ${type}` : type)}
            >
              {type}
            </code>
          ))}
        </div>
        
        <p className="text-xs text-gray-600 mt-3">
          <strong>Common Relationship Types:</strong>
        </p>
        <div className="flex flex-wrap gap-1 mt-2">
          {['MANAGES', 'OWNS', 'REPORTS_TO', 'WORKS_ON', 'CREATED', 'MENTIONS'].map((type) => (
            <code
              key={type}
              className="text-xs bg-gray-100 px-2 py-1 rounded cursor-pointer hover:bg-gray-200"
              onClick={() => setRelationshipTypes(relationshipTypes ? `${relationshipTypes}, ${type}` : type)}
            >
              {type}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}
