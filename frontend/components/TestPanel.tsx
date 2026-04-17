'use client';

import React, { useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { createApiClient } from '@/lib/api-client';

interface NodeExecutionLog {
  node_id: string;
  node_type: string;
  node_label: string;
  input: Record<string, any>;
  output: string;
  execution_time_ms: number;
  status: 'success' | 'failed' | 'slow';
  error?: string;
}

interface TestExecutionResult {
  success: boolean;
  total_duration_ms: number;
  node_logs: NodeExecutionLog[];
  final_output: string;
  error?: string;
}

interface TestPanelProps {
  token: string;
  onClose?: () => void;
}

export default function TestPanel({ token, onClose }: TestPanelProps) {
  const { nodes, edges, compileWorkflow, validateWorkflow } = useWorkflowStore();
  const [testTranscript, setTestTranscript] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<TestExecutionResult | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  const handleTestExecution = async () => {
    if (!testTranscript.trim()) {
      alert('Please enter a test transcript');
      return;
    }

    // Validate workflow first
    const validation = validateWorkflow();
    if (!validation.valid) {
      alert(`Workflow validation failed:\n${validation.errors.join('\n')}`);
      return;
    }

    setIsExecuting(true);
    setExecutionResult(null);

    try {
      // Compile workflow
      const workflowJSON = compileWorkflow({
        workflow_name: 'Test Workflow',
        description: 'Testing workflow execution',
        created_by: 'test_user',
        updated_at: new Date().toISOString(),
      });

      // Call test endpoint
      const apiClient = createApiClient(token);
      const response = await apiClient.post('/api/workflows/test', {
        workflow_json: workflowJSON,
        test_input: testTranscript,
      });

      setExecutionResult(response.data);
    } catch (error: any) {
      setExecutionResult({
        success: false,
        total_duration_ms: 0,
        node_logs: [],
        final_output: '',
        error: error.response?.data?.detail || error.message || 'Test execution failed',
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const toggleNodeExpansion = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 border-green-300 text-green-800';
      case 'failed':
        return 'bg-red-100 border-red-300 text-red-800';
      case 'slow':
        return 'bg-yellow-100 border-yellow-300 text-yellow-800';
      default:
        return 'bg-gray-100 border-gray-300 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return '✓';
      case 'failed':
        return '✗';
      case 'slow':
        return '⚠';
      default:
        return '○';
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-1/3 bg-white border-l border-gray-300 shadow-lg overflow-hidden flex flex-col z-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold">Test Workflow</h2>
          <p className="text-sm text-purple-100">Execute workflow with sample input</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-white hover:text-purple-200 text-2xl font-bold"
            aria-label="Close test panel"
          >
            ×
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Test Input Section */}
        <div className="space-y-2">
          <label htmlFor="test-transcript" className="block text-sm font-semibold text-gray-700">
            Test Transcript
          </label>
          <textarea
            id="test-transcript"
            value={testTranscript}
            onChange={(e) => setTestTranscript(e.target.value)}
            placeholder="Enter a sample user transcript to test the workflow..."
            className="w-full h-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
            disabled={isExecuting}
          />
          <button
            onClick={handleTestExecution}
            disabled={isExecuting || !testTranscript.trim()}
            className="w-full bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isExecuting ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Executing...
              </span>
            ) : (
              'Run Test'
            )}
          </button>
        </div>

        {/* Execution Results */}
        {executionResult && (
          <div className="space-y-4">
            {/* Summary */}
            <div className={`p-4 rounded-lg border-2 ${
              executionResult.success 
                ? 'bg-green-50 border-green-300' 
                : 'bg-red-50 border-red-300'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-bold text-lg">
                  {executionResult.success ? '✓ Test Passed' : '✗ Test Failed'}
                </h3>
                <span className={`text-sm font-mono ${
                  executionResult.total_duration_ms > 800 
                    ? 'text-red-600 font-bold' 
                    : 'text-gray-600'
                }`}>
                  {executionResult.total_duration_ms}ms
                  {executionResult.total_duration_ms > 800 && ' ⚠ Exceeds 800ms target'}
                </span>
              </div>
              
              {executionResult.error && (
                <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded text-sm text-red-800">
                  <strong>Error:</strong> {executionResult.error}
                </div>
              )}
              
              {executionResult.final_output && (
                <div className="mt-2">
                  <strong className="text-sm text-gray-700">Final Output:</strong>
                  <div className="mt-1 p-2 bg-white border border-gray-300 rounded text-sm">
                    {executionResult.final_output}
                  </div>
                </div>
              )}
            </div>

            {/* Timeline View */}
            {executionResult.node_logs && executionResult.node_logs.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-bold text-gray-800">Execution Timeline</h3>
                <div className="space-y-2">
                  {executionResult.node_logs.map((log, index) => (
                    <div
                      key={log.node_id}
                      className={`border-2 rounded-lg overflow-hidden ${getStatusColor(log.status)}`}
                    >
                      {/* Node Header */}
                      <button
                        onClick={() => toggleNodeExpansion(log.node_id)}
                        className="w-full p-3 flex items-center justify-between hover:opacity-80 transition-opacity"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-xl font-bold">{getStatusIcon(log.status)}</span>
                          <div className="text-left">
                            <div className="font-semibold">
                              {index + 1}. {log.node_label}
                            </div>
                            <div className="text-xs opacity-75">
                              {log.node_type} • {log.node_id}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <span className={`text-sm font-mono ${
                            log.execution_time_ms > 200 ? 'font-bold' : ''
                          }`}>
                            {log.execution_time_ms}ms
                          </span>
                          <span className="text-lg">
                            {expandedNodes.has(log.node_id) ? '▼' : '▶'}
                          </span>
                        </div>
                      </button>

                      {/* Expanded Details */}
                      {expandedNodes.has(log.node_id) && (
                        <div className="px-3 pb-3 space-y-2 border-t border-current border-opacity-20">
                          {/* Input */}
                          <div>
                            <div className="text-xs font-semibold mb-1 mt-2">Input:</div>
                            <pre className="text-xs bg-white bg-opacity-50 p-2 rounded overflow-x-auto">
                              {JSON.stringify(log.input, null, 2)}
                            </pre>
                          </div>

                          {/* Output */}
                          <div>
                            <div className="text-xs font-semibold mb-1">Output:</div>
                            <pre className="text-xs bg-white bg-opacity-50 p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                              {log.output}
                            </pre>
                          </div>

                          {/* Error */}
                          {log.error && (
                            <div>
                              <div className="text-xs font-semibold mb-1">Error:</div>
                              <pre className="text-xs bg-red-50 p-2 rounded overflow-x-auto">
                                {log.error}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!executionResult && !isExecuting && (
          <div className="text-center py-12 text-gray-400">
            <svg className="mx-auto h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            <p className="text-sm">Enter a test transcript and click "Run Test" to see execution logs</p>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="border-t border-gray-200 bg-gray-50 p-3 text-xs text-gray-600">
        <div className="flex items-center justify-between">
          <span>Nodes: {nodes.length}</span>
          <span>Edges: {edges.length}</span>
          <span className="flex items-center">
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-1"></span>
            Success
            <span className="inline-block w-2 h-2 bg-yellow-500 rounded-full ml-2 mr-1"></span>
            Slow (&gt;200ms)
            <span className="inline-block w-2 h-2 bg-red-500 rounded-full ml-2 mr-1"></span>
            Failed
          </span>
        </div>
      </div>
    </div>
  );
}
