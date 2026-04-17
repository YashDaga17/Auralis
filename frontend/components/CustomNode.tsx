'use client';

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { WorkflowNode } from '@/stores/workflowStore';

interface CustomNodeProps extends NodeProps {
  data: WorkflowNode['data'] & {
    hasError?: boolean;
  };
}

export default function CustomNode({ data, selected }: CustomNodeProps) {
  const hasError = data.hasError || false;

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'trigger':
        return '#10b981'; // green
      case 'rag':
        return '#3b82f6'; // blue
      case 'llm':
        return '#8b5cf6'; // purple
      case 'tool':
        return '#f59e0b'; // amber
      case 'action':
        return '#ec4899'; // pink
      case 'decision':
        return '#06b6d4'; // cyan
      case 'graph_query':
        return '#14b8a6'; // teal
      case 'knowledge':
        return '#6366f1'; // indigo
      case 'multi_source_rag':
        return '#0ea5e9'; // sky
      case 'fallback':
        return '#ef4444'; // red
      default:
        return '#6b7280'; // gray
    }
  };

  const nodeColor = getNodeColor(data.label.toLowerCase().split(' ')[0]);

  return (
    <div
      className={`custom-node ${selected ? 'selected' : ''} ${hasError ? 'has-error' : ''}`}
      style={{
        borderColor: hasError ? '#ef4444' : nodeColor,
        backgroundColor: hasError ? '#fef2f2' : 'white',
      }}
    >
      <Handle type="target" position={Position.Top} />
      
      <div className="node-header" style={{ backgroundColor: hasError ? '#fee2e2' : nodeColor }}>
        <span className="node-label">{data.label}</span>
        {hasError && <span className="error-badge">⚠️</span>}
      </div>
      
      <div className="node-body">
        {Object.keys(data.config || {}).length > 0 ? (
          <div className="config-preview">
            {Object.entries(data.config).slice(0, 2).map(([key, value]) => (
              <div key={key} className="config-item">
                <span className="config-key">{key}:</span>
                <span className="config-value">
                  {typeof value === 'string' && value.length > 20
                    ? `${value.substring(0, 20)}...`
                    : String(value)}
                </span>
              </div>
            ))}
            {Object.keys(data.config).length > 2 && (
              <div className="config-more">+{Object.keys(data.config).length - 2} more</div>
            )}
          </div>
        ) : (
          <div className="no-config">Not configured</div>
        )}
      </div>
      
      <Handle type="source" position={Position.Bottom} />

      <style jsx>{`
        .custom-node {
          min-width: 180px;
          border: 2px solid;
          border-radius: 8px;
          background: white;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          transition: all 0.2s;
        }

        .custom-node.selected {
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
          transform: scale(1.02);
        }

        .custom-node.has-error {
          animation: errorPulse 2s infinite;
        }

        @keyframes errorPulse {
          0%, 100% {
            box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
          }
          50% {
            box-shadow: 0 4px 16px rgba(239, 68, 68, 0.5);
          }
        }

        .node-header {
          padding: 8px 12px;
          border-radius: 6px 6px 0 0;
          color: white;
          font-weight: 600;
          font-size: 13px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .node-label {
          flex: 1;
        }

        .error-badge {
          font-size: 16px;
          animation: shake 0.5s infinite;
        }

        @keyframes shake {
          0%, 100% {
            transform: translateX(0);
          }
          25% {
            transform: translateX(-2px);
          }
          75% {
            transform: translateX(2px);
          }
        }

        .node-body {
          padding: 12px;
          font-size: 12px;
          color: #374151;
        }

        .config-preview {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .config-item {
          display: flex;
          gap: 4px;
        }

        .config-key {
          font-weight: 500;
          color: #6b7280;
        }

        .config-value {
          color: #1f2937;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .config-more {
          color: #9ca3af;
          font-style: italic;
          margin-top: 4px;
        }

        .no-config {
          color: #9ca3af;
          font-style: italic;
        }
      `}</style>
    </div>
  );
}
