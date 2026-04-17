'use client';

import React, { useState, useEffect } from 'react';
import { GraphLink, GraphNode } from '@/stores/graphStore';

interface LinkEditorModalProps {
  link: GraphLink | null;
  nodes: GraphNode[];
  isOpen: boolean;
  onClose: () => void;
  onSave: (link: GraphLink) => void;
  onDelete?: (linkId: string) => void;
  availableTypes: string[];
}

export default function LinkEditorModal({
  link,
  nodes,
  isOpen,
  onClose,
  onSave,
  onDelete,
  availableTypes,
}: LinkEditorModalProps) {
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [type, setType] = useState('');
  const [confidence, setConfidence] = useState(1.0);
  const [sourceDocumentId, setSourceDocumentId] = useState('');
  const [properties, setProperties] = useState('{}');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (link) {
      setSourceId(link.source);
      setTargetId(link.target);
      setType(link.type);
      setConfidence(link.confidence || 1.0);
      setSourceDocumentId(link.source_document_id || '');
      setProperties(JSON.stringify(link.properties, null, 2));
    } else {
      setSourceId(nodes[0]?.id || '');
      setTargetId(nodes[1]?.id || '');
      setType(availableTypes[0] || '');
      setConfidence(1.0);
      setSourceDocumentId('');
      setProperties('{}');
    }
    setError(null);
  }, [link, nodes, availableTypes]);

  const handleSave = () => {
    try {
      const parsedProperties = JSON.parse(properties);

      if (!sourceId || !targetId) {
        setError('Source and target nodes are required');
        return;
      }

      if (sourceId === targetId) {
        setError('Source and target must be different nodes');
        return;
      }

      if (!type.trim()) {
        setError('Relationship type is required');
        return;
      }

      const updatedLink: GraphLink = {
        id: link?.id || '',
        source: sourceId,
        target: targetId,
        type: type.trim(),
        confidence,
        source_document_id: sourceDocumentId || undefined,
        properties: parsedProperties,
      };

      onSave(updatedLink);
      onClose();
    } catch (err) {
      setError('Invalid JSON in properties');
    }
  };

  const handleDelete = () => {
    if (link && onDelete && confirm('Are you sure you want to delete this relationship?')) {
      onDelete(link.id);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">
            {link ? 'Edit Relationship' : 'Create Relationship'}
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Source Node *</label>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={!!link}
            >
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.name} ({node.type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Node *</label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={!!link}
            >
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.name} ({node.type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Relationship Type *
            </label>
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
              Confidence Score (0-1)
            </label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={confidence}
              onChange={(e) => setConfidence(parseFloat(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Document ID (optional)
            </label>
            <input
              type="text"
              value={sourceDocumentId}
              onChange={(e) => setSourceDocumentId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="document_123"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Properties (JSON)
            </label>
            <textarea
              value={properties}
              onChange={(e) => setProperties(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              placeholder='{"key": "value"}'
            />
          </div>
        </div>

        <div className="p-6 border-t border-gray-200 flex items-center justify-between">
          <div>
            {link && onDelete && (
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Delete Relationship
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
