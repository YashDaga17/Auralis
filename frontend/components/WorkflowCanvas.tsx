'use client';

import React, { useCallback, useRef, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  OnConnect,
  OnNodesChange,
  OnEdgesChange,
  ReactFlowProvider,
  ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useWorkflowStore, WorkflowNode, WorkflowEdge } from '@/stores/workflowStore';
import ValidationErrorDisplay from './ValidationErrorDisplay';
import CustomNode from './CustomNode';

interface WorkflowCanvasProps {
  onNodeSelect?: (node: WorkflowNode | null) => void;
  onFileUpload?: (file: File, position: { x: number; y: number }) => void;
  showValidationErrors?: boolean;
}

function WorkflowCanvasInner({ onNodeSelect, onFileUpload, showValidationErrors = false }: WorkflowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<ReactFlowInstance | null>(null);
  const [validationErrors, setValidationErrors] = React.useState<Array<{
    nodeId: string;
    errors: string[];
    position: { x: number; y: number };
  }>>([]);
  const [nodeErrorIds, setNodeErrorIds] = React.useState<Set<string>>(new Set());
  
  const { 
    nodes, 
    edges, 
    addNode, 
    addEdge: addStoreEdge, 
    setSelectedNode, 
    deleteNode, 
    deleteEdge,
    setNodes,
    setEdges,
    validateWorkflow,
  } = useWorkflowStore();
  
  // Define custom node types
  const nodeTypes = useMemo(() => ({
    trigger: CustomNode,
    rag: CustomNode,
    llm: CustomNode,
    tool: CustomNode,
    action: CustomNode,
    decision: CustomNode,
    graph_query: CustomNode,
    knowledge: CustomNode,
    multi_source_rag: CustomNode,
    fallback: CustomNode,
  }), []);
  
  const [localNodes, setLocalNodes, onNodesChange] = useNodesState(nodes);
  const [localEdges, setLocalEdges, onEdgesChange] = useEdgesState(edges);

  // Enhance nodes with error information
  const enhancedNodes = useMemo(() => {
    return localNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        hasError: nodeErrorIds.has(node.id),
      },
    }));
  }, [localNodes, nodeErrorIds]);

  // Sync store nodes/edges with local state
  React.useEffect(() => {
    setLocalNodes(nodes);
  }, [nodes, setLocalNodes]);

  React.useEffect(() => {
    setLocalEdges(edges);
  }, [edges, setLocalEdges]);

  // Sync local changes back to store (for position updates, etc.)
  React.useEffect(() => {
    // Only sync if nodes have actually changed (not just initial load)
    if (localNodes.length > 0 && JSON.stringify(localNodes) !== JSON.stringify(nodes)) {
      setNodes(localNodes as WorkflowNode[]);
    }
  }, [localNodes]);

  React.useEffect(() => {
    if (localEdges.length > 0 && JSON.stringify(localEdges) !== JSON.stringify(edges)) {
      setEdges(localEdges as WorkflowEdge[]);
    }
  }, [localEdges]);

  // Run validation when showValidationErrors changes or nodes/edges change
  React.useEffect(() => {
    if (showValidationErrors && nodes.length > 0) {
      const validation = validateWorkflow();
      
      if (!validation.valid && validation.nodeErrors) {
        const errors = Array.from(validation.nodeErrors.entries()).map(([nodeId, errs]) => {
          const node = nodes.find((n) => n.id === nodeId);
          return {
            nodeId: node?.data.label || nodeId,
            errors: errs,
            position: node?.position || { x: 0, y: 0 },
          };
        });
        setValidationErrors(errors);
        setNodeErrorIds(new Set(validation.nodeErrors.keys()));
      } else {
        setValidationErrors([]);
        setNodeErrorIds(new Set());
      }
    } else {
      setValidationErrors([]);
      setNodeErrorIds(new Set());
    }
  }, [showValidationErrors, nodes, edges, validateWorkflow]);

  // Handle edge connection with DAG validation
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      // Check if adding this edge would create a cycle
      if (wouldCreateCycle(connection, localEdges, localNodes)) {
        alert('Cannot create this connection: it would create a cycle. Workflows must be directed acyclic graphs (DAG).');
        return;
      }

      addStoreEdge(connection);
    },
    [addStoreEdge, localEdges, localNodes]
  );

  // Handle node selection
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNode(node as WorkflowNode);
      if (onNodeSelect) {
        onNodeSelect(node as WorkflowNode);
      }
    },
    [setSelectedNode, onNodeSelect]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    if (onNodeSelect) {
      onNodeSelect(null);
    }
  }, [setSelectedNode, onNodeSelect]);

  // Handle drag over for file drop
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop for both nodes and files
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowInstance || !reactFlowWrapper.current) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      
      // Check if it's a file drop
      if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
        const file = event.dataTransfer.files[0];
        const position = reactFlowInstance.project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        });

        if (onFileUpload) {
          onFileUpload(file, position);
        }
        return;
      }

      // Handle node drop from palette
      const nodeType = event.dataTransfer.getData('application/reactflow');
      if (!nodeType) return;

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode: WorkflowNode = {
        id: `${nodeType}_${Date.now()}`,
        type: nodeType as WorkflowNode['type'],
        position,
        data: {
          label: `${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)} Node`,
          config: getDefaultConfig(nodeType),
        },
      };

      addNode(newNode);
    },
    [reactFlowInstance, addNode, onFileUpload]
  );

  // Handle keyboard shortcuts
  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      // Delete selected nodes/edges with Delete or Backspace
      if (event.key === 'Delete' || event.key === 'Backspace') {
        const selectedNodes = localNodes.filter((node) => node.selected);
        const selectedEdges = localEdges.filter((edge) => edge.selected);

        selectedNodes.forEach((node) => deleteNode(node.id));
        selectedEdges.forEach((edge) => deleteEdge(edge.id));
      }
    },
    [localNodes, localEdges, deleteNode, deleteEdge]
  );

  return (
    <div 
      ref={reactFlowWrapper} 
      style={{ width: '100%', height: '100%', position: 'relative' }}
      onKeyDown={onKeyDown}
      tabIndex={0}
    >
      <ReactFlow
        nodes={enhancedNodes}
        edges={localEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onInit={setReactFlowInstance}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
      
      {/* Validation Error Display */}
      {showValidationErrors && (
        <ValidationErrorDisplay 
          errors={validationErrors}
          onClose={() => setValidationErrors([])}
        />
      )}
    </div>
  );
}

// Cycle detection using DFS
function wouldCreateCycle(
  newConnection: Connection,
  edges: Edge[],
  nodes: Node[]
): boolean {
  // Build adjacency list with the new edge
  const adjacencyList = new Map<string, string[]>();
  nodes.forEach((node) => adjacencyList.set(node.id, []));

  // Add existing edges
  edges.forEach((edge) => {
    const targets = adjacencyList.get(edge.source) || [];
    targets.push(edge.target);
    adjacencyList.set(edge.source, targets);
  });

  // Add the new edge
  if (newConnection.source && newConnection.target) {
    const targets = adjacencyList.get(newConnection.source) || [];
    targets.push(newConnection.target);
    adjacencyList.set(newConnection.source, targets);
  }

  // DFS to detect cycle
  const visited = new Set<string>();
  const recursionStack = new Set<string>();

  function dfs(nodeId: string): boolean {
    visited.add(nodeId);
    recursionStack.add(nodeId);

    const neighbors = adjacencyList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) return true;
      } else if (recursionStack.has(neighbor)) {
        return true; // Cycle detected
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  // Check all nodes
  for (const nodeId of adjacencyList.keys()) {
    if (!visited.has(nodeId)) {
      if (dfs(nodeId)) return true;
    }
  }

  return false;
}

// Get default configuration for each node type
function getDefaultConfig(nodeType: string): Record<string, any> {
  switch (nodeType) {
    case 'trigger':
      return { source: 'vapi' };
    case 'rag':
      return { collection_name: '', query_template: '{{trigger_output}}', result_limit: 5 };
    case 'llm':
      return { 
        system_prompt: 'You are a helpful assistant.',
        user_prompt: '{{trigger_output}}',
        temperature: 0.7,
        max_tokens: 1024,
        model: 'gemini-2.5-flash'
      };
    case 'tool':
      return { 
        api_endpoint: '',
        http_method: 'GET',
        headers: {},
        timeout_ms: 5000
      };
    case 'action':
      return { 
        integration: 'hubspot',
        action_type: '',
        parameters: {},
        require_confirmation: false
      };
    case 'decision':
      return { 
        classification_prompt: 'Classify the user intent.',
        intents: [],
        fallback_intent: 'unknown'
      };
    case 'graph_query':
      return { 
        max_depth: 3,
        entity_types: [],
        relationship_types: [],
        timeout_ms: 5000
      };
    case 'knowledge':
      return { 
        filename: '',
        collection_name: '',
        chunk_count: 0
      };
    case 'multi_source_rag':
      return { 
        collections: [],
        query_template: '{{trigger_output}}',
        result_limit: 5,
        weights: {}
      };
    default:
      return {};
  }
}

// Wrapper with ReactFlowProvider
export default function WorkflowCanvas(props: WorkflowCanvasProps) {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
