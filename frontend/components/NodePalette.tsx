'use client';

import React from 'react';

interface NodeTypeConfig {
  type: string;
  label: string;
  description: string;
  icon: string;
  color: string;
}

const nodeTypes: NodeTypeConfig[] = [
  {
    type: 'trigger',
    label: 'Trigger',
    description: 'Entry point for workflow execution',
    icon: '▶️',
    color: 'bg-green-500',
  },
  {
    type: 'rag',
    label: 'RAG',
    description: 'Retrieve information from vector database',
    icon: '🔍',
    color: 'bg-blue-500',
  },
  {
    type: 'llm',
    label: 'LLM',
    description: 'Generate text using language model',
    icon: '🤖',
    color: 'bg-purple-500',
  },
  {
    type: 'tool',
    label: 'Tool',
    description: 'Execute external API calls',
    icon: '🔧',
    color: 'bg-orange-500',
  },
  {
    type: 'action',
    label: 'Action',
    description: 'Perform business workflow actions',
    icon: '⚡',
    color: 'bg-yellow-500',
  },
  {
    type: 'decision',
    label: 'Decision',
    description: 'Route based on intent classification',
    icon: '🔀',
    color: 'bg-pink-500',
  },
  {
    type: 'graph_query',
    label: 'Graph Query',
    description: 'Query knowledge graph with Cypher',
    icon: '🕸️',
    color: 'bg-indigo-500',
  },
  {
    type: 'multi_source_rag',
    label: 'Multi-Source RAG',
    description: 'Retrieve from multiple collections',
    icon: '📚',
    color: 'bg-teal-500',
  },
];

interface NodePaletteProps {
  className?: string;
}

export default function NodePalette({ className = '' }: NodePaletteProps) {
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className={`node-palette ${className}`}>
      <div className="p-4 bg-gray-50 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-800">Node Palette</h3>
        <p className="text-sm text-gray-600 mt-1">Drag nodes onto the canvas</p>
      </div>
      
      <div className="p-4 space-y-2 overflow-y-auto">
        {nodeTypes.map((nodeType) => (
          <div
            key={nodeType.type}
            draggable
            onDragStart={(e) => onDragStart(e, nodeType.type)}
            className="node-palette-item cursor-move p-3 bg-white border-2 border-gray-200 rounded-lg hover:border-gray-400 hover:shadow-md transition-all"
          >
            <div className="flex items-start gap-3">
              <div className={`flex-shrink-0 w-10 h-10 ${nodeType.color} rounded-lg flex items-center justify-center text-xl`}>
                {nodeType.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-gray-800 text-sm">{nodeType.label}</h4>
                <p className="text-xs text-gray-600 mt-1">{nodeType.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <style jsx>{`
        .node-palette {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: white;
          border-right: 1px solid #e5e7eb;
        }
        
        .node-palette-item {
          user-select: none;
        }
        
        .node-palette-item:active {
          cursor: grabbing;
        }
      `}</style>
    </div>
  );
}
