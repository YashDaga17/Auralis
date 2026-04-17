'use client';

import React from 'react';

interface ValidationError {
  nodeId: string;
  errors: string[];
  position: { x: number; y: number };
}

interface ValidationErrorDisplayProps {
  errors: ValidationError[];
  onClose: () => void;
}

export default function ValidationErrorDisplay({ errors, onClose }: ValidationErrorDisplayProps) {
  if (errors.length === 0) return null;

  return (
    <>
      {/* Error badges on canvas */}
      {errors.map((error) => (
        <div
          key={error.nodeId}
          className="validation-error-badge"
          style={{
            position: 'absolute',
            left: error.position.x + 150,
            top: error.position.y - 10,
            zIndex: 1000,
          }}
        >
          <div className="error-icon">⚠️</div>
          <div className="error-tooltip">
            <div className="error-tooltip-header">Validation Errors</div>
            <ul className="error-list">
              {error.errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          </div>
        </div>
      ))}

      {/* Global error panel */}
      <div className="validation-error-panel">
        <div className="error-panel-header">
          <span className="error-icon">⚠️</span>
          <span className="error-title">Workflow Validation Errors ({errors.length})</span>
          <button onClick={onClose} className="close-button">✕</button>
        </div>
        <div className="error-panel-content">
          {errors.map((error) => (
            <div key={error.nodeId} className="error-item">
              <div className="error-node-id">Node: {error.nodeId}</div>
              <ul className="error-list">
                {error.errors.map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <style jsx>{`
        .validation-error-badge {
          pointer-events: none;
        }

        .error-icon {
          font-size: 24px;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.7;
            transform: scale(1.1);
          }
        }

        .error-tooltip {
          display: none;
          position: absolute;
          left: 30px;
          top: -10px;
          background: white;
          border: 2px solid #ef4444;
          border-radius: 8px;
          padding: 12px;
          min-width: 250px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          pointer-events: auto;
        }

        .validation-error-badge:hover .error-tooltip {
          display: block;
        }

        .error-tooltip-header {
          font-weight: 600;
          color: #ef4444;
          margin-bottom: 8px;
          font-size: 14px;
        }

        .error-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .error-list li {
          padding: 4px 0;
          font-size: 13px;
          color: #374151;
          border-bottom: 1px solid #f3f4f6;
        }

        .error-list li:last-child {
          border-bottom: none;
        }

        .validation-error-panel {
          position: fixed;
          bottom: 20px;
          right: 20px;
          width: 400px;
          max-height: 300px;
          background: white;
          border: 2px solid #ef4444;
          border-radius: 12px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
          z-index: 2000;
          overflow: hidden;
          animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
          from {
            transform: translateY(100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }

        .error-panel-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 16px;
          background: #fef2f2;
          border-bottom: 1px solid #fecaca;
        }

        .error-panel-header .error-icon {
          font-size: 20px;
          animation: none;
        }

        .error-title {
          flex: 1;
          font-weight: 600;
          color: #991b1b;
          font-size: 14px;
        }

        .close-button {
          background: none;
          border: none;
          color: #991b1b;
          font-size: 20px;
          cursor: pointer;
          padding: 0;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 4px;
          transition: background-color 0.2s;
        }

        .close-button:hover {
          background: #fecaca;
        }

        .error-panel-content {
          padding: 16px;
          max-height: 220px;
          overflow-y: auto;
        }

        .error-item {
          margin-bottom: 16px;
          padding-bottom: 16px;
          border-bottom: 1px solid #f3f4f6;
        }

        .error-item:last-child {
          margin-bottom: 0;
          padding-bottom: 0;
          border-bottom: none;
        }

        .error-node-id {
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 8px;
          font-size: 13px;
        }

        .error-item .error-list li {
          padding-left: 16px;
          position: relative;
        }

        .error-item .error-list li::before {
          content: '•';
          position: absolute;
          left: 4px;
          color: #ef4444;
        }
      `}</style>
    </>
  );
}
