'use client';

import React from 'react';
import { WorkflowNode, useWorkflowStore } from '@/stores/workflowStore';
import RAGNodeConfig from './node-configs/RAGNodeConfig';
import LLMNodeConfig from './node-configs/LLMNodeConfig';
import ToolNodeConfig from './node-configs/ToolNodeConfig';
import GraphQueryNodeConfig from './node-configs/GraphQueryNodeConfig';
import ActionNodeConfig from './node-configs/ActionNodeConfig';
import DecisionNodeConfig from './node-configs/DecisionNodeConfig';

interface ConfigurationPanelProps {
  selectedNode: WorkflowNode | null;
}

export default function ConfigurationPanel({ selectedNode }: ConfigurationPanelProps) {
  const { updateNode, nodes } = useWorkflowStore();

  // Get available context variables from upstream nodes
  const getAvailableContextVariables = (currentNodeId: string): string[] => {
    const variables = ['trigger_output'];
    
    // Find all nodes that come before this node in the workflow
    nodes.forEach((node) => {
      if (node.id !== currentNodeId) {
        variables.push(`${node.id}_output`);
      }
    });
    
    return variables;
  };

  const handleConfigUpdate = (nodeId: string, newConfig: Record<string, any>) => {
    if (!selectedNode) return;
    
    updateNode(nodeId, {
      data: {
        label: selectedNode.data.label,
        config: newConfig,
      },
    });
  };

  if (!selectedNode) {
    return (
      <div className="text-center text-slate-500 mt-8 p-6 bg-slate-50 rounded-lg border border-slate-200">
        <p className="text-lg font-medium">Select a node to configure</p>
        <p className="text-sm text-slate-400 mt-2">Click on any node in the canvas to edit its settings</p>
      </div>
    );
  }

  const availableVariables = getAvailableContextVariables(selectedNode.id);

  return (
    <div>
      <h3 className="text-lg font-semibold text-slate-800 mb-4 pb-3 border-b border-slate-200">
        Node Configuration
      </h3>
      
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Node Type
          </label>
          <input
            type="text"
            value={selectedNode.type}
            disabled
            className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-100 text-slate-700 font-medium"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Node ID
          </label>
          <input
            type="text"
            value={selectedNode.id}
            disabled
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600 text-xs"
          />
        </div>
      </div>

      <div className="border-t border-gray-200 pt-4">
        {selectedNode.type === 'rag' && (
          <RAGNodeConfig
            config={selectedNode.data.config}
            onUpdate={(config: Record<string, any>) => handleConfigUpdate(selectedNode.id, config)}
            availableVariables={availableVariables}
          />
        )}
        
        {selectedNode.type === 'llm' && (
          <LLMNodeConfig
            config={selectedNode.data.config}
            onUpdate={(config: Record<string, any>) => handleConfigUpdate(selectedNode.id, config)}
            availableVariables={availableVariables}
          />
        )}
        
        {selectedNode.type === 'tool' && (
          <ToolNodeConfig
            config={selectedNode.data.config}
            onUpdate={(config: Record<string, any>) => handleConfigUpdate(selectedNode.id, config)}
            availableVariables={availableVariables}
          />
        )}
        
        {selectedNode.type === 'graph_query' && (
          <GraphQueryNodeConfig
            config={selectedNode.data.config}
            onUpdate={(config: Record<string, any>) => handleConfigUpdate(selectedNode.id, config)}
            availableVariables={availableVariables}
          />
        )}
        
        {selectedNode.type === 'action' && (
          <ActionNodeConfig
            config={selectedNode.data.config}
            onUpdate={(config: Record<string, any>) => handleConfigUpdate(selectedNode.id, config)}
            availableVariables={availableVariables}
          />
        )}
        
        {selectedNode.type === 'decision' && (
          <DecisionNodeConfig
            config={selectedNode.data.config}
            onUpdate={(config: Record<string, any>) => handleConfigUpdate(selectedNode.id, config)}
            availableVariables={availableVariables}
          />
        )}
        
        {selectedNode.type === 'trigger' && (
          <div className="text-sm text-gray-600">
            <p>Trigger nodes receive input from Vapi and don't require additional configuration.</p>
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="font-medium text-blue-900">Available Output:</p>
              <code className="text-xs text-blue-700">{'{{trigger_output}}'}</code>
            </div>
          </div>
        )}
        
        {selectedNode.type === 'knowledge' && (
          <div className="text-sm text-gray-600">
            <p>Knowledge nodes represent uploaded documents. Configuration is set during file upload.</p>
            <div className="mt-4 space-y-2">
              <div>
                <span className="font-medium">Filename:</span>{' '}
                <span className="text-gray-800">{selectedNode.data.config.filename || 'N/A'}</span>
              </div>
              <div>
                <span className="font-medium">Collection:</span>{' '}
                <span className="text-gray-800">{selectedNode.data.config.collection_name || 'N/A'}</span>
              </div>
              <div>
                <span className="font-medium">Chunks:</span>{' '}
                <span className="text-gray-800">{selectedNode.data.config.chunk_count || 0}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
