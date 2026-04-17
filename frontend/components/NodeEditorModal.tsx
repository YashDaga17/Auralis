'use client';

import React, { useState, useEffect } from 'react';
import { GraphNode, useGraphStore } from '@/stores/graphStore';

interface NodeEditorModalProps {
  node: GraphNode | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (node: GraphNode) => void;
  onDelete?: (nodeId: string) => void;
  availableTypes: string[];
}

export default function NodeEditorModal({
  node,
  isOpen,
  onClose,
  onSave,
  onDelete,
  availableTypes,
}: NodeEditorModalProps) {
  const [name, setName] = useState('');
  const [type, setType] = useState('');
  const [properties, setProperties] = useState('{}');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (node) {
      setName(node.name);
      setType(node.type);
      setProperties(JSON.stringify(node.properties, null, 2));
    } else {
      setName('');
      setType(availableTypes[0] || '');
      setProperties('{}');
    }
    setError(null);
  }, [node, availableTypes]);

  const handleSave = () => {
    try {
      const parsedProperties = JSON.parse(properties);
      
      if (!name.trim()) {
        setError('Name is required');
        return;
      }

      if (!type.trim()) {
        setError('Type is required');
        return;
      }

      const updatedNode: GraphNode = {
        id: node?.id || '',
        name: name.trim(),
        type: type.trim(),
        properties: parsedProperties,
        company_id: node?.company_id || '',
      };

      onSave(updatedNode);
      onClose();
    } catch (err) {
      setError('Invalid JSON in properties');
    }
  };

  const handleDelete = () => {
    if (node && onDelete && confirm(`Are you sure you want to delete "${node.name}"?`)) {
      onDelete(node.id);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">
            {node ? 'Edit Node' : 'Create Node'}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Entity name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {availableTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Properties (JSON)
            </label>
            <textarea
              value={properties}
              onChange={(e) => setProperties(e.target.value)}
              rows={10}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              placeholder='{"key": "value"}'
            />
          </div>
        </div>

        <div className="p-6 border-t border-gray-200 flex items-center justify-between">
          <div>
            {node && onDelete && (
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Delete Node
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
