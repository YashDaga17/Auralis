import { create } from 'zustand';
import { Node, Edge, Connection, addEdge } from 'reactflow';
import { createApiClient } from '@/lib/api-client';

// Types from design document
export interface WorkflowNode extends Node {
  type: 'trigger' | 'rag' | 'llm' | 'tool' | 'action' | 'decision' | 'graph_query' | 'knowledge' | 'multi_source_rag' | 'fallback';
  data: {
    label: string;
    config: Record<string, any>;
  };
}

export type WorkflowEdge = Edge & {
  label?: string;
};

export interface WorkflowJSON {
  version: string;
  metadata: {
    workflow_name: string;
    description: string;
    created_by: string;
    updated_at: string;
  };
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

interface WorkflowState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  selectedNode: WorkflowNode | null;
  
  // Node operations
  addNode: (node: WorkflowNode) => void;
  updateNode: (nodeId: string, updates: Partial<WorkflowNode>) => void;
  deleteNode: (nodeId: string) => void;
  setSelectedNode: (node: WorkflowNode | null) => void;
  setNodes: (nodes: WorkflowNode[]) => void;
  
  // Edge operations
  addEdge: (connection: Connection) => void;
  deleteEdge: (edgeId: string) => void;
  setEdges: (edges: WorkflowEdge[]) => void;
  
  // Workflow operations
  validateWorkflow: () => { valid: boolean; errors: string[]; nodeErrors: Map<string, string[]> };
  compileWorkflow: (metadata: WorkflowJSON['metadata']) => WorkflowJSON;
  saveWorkflow: (token: string, agentId: string, metadata: WorkflowJSON['metadata']) => Promise<void>;
  loadWorkflow: (token: string, agentId: string) => Promise<void>;
  testWorkflow: (token: string, testInput: string) => Promise<any>;
  clearWorkflow: () => void;
  exportWorkflow: (metadata: WorkflowJSON['metadata']) => void;
  importWorkflow: (file: File) => Promise<void>;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNode: null,

  // Node operations
  addNode: (node) => {
    set((state) => ({
      nodes: [...state.nodes, node],
    }));
  },

  updateNode: (nodeId, updates) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, ...updates } : node
      ),
      selectedNode:
        state.selectedNode?.id === nodeId
          ? { ...state.selectedNode, ...updates }
          : state.selectedNode,
    }));
  },

  setNodes: (nodes) => {
    set({ nodes });
  },

  deleteNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      edges: state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
      selectedNode:
        state.selectedNode?.id === nodeId ? null : state.selectedNode,
    }));
  },

  setSelectedNode: (node) => {
    set({ selectedNode: node });
  },

  // Edge operations
  addEdge: (connection) => {
    set((state) => ({
      edges: addEdge(connection, state.edges) as WorkflowEdge[],
    }));
  },

  deleteEdge: (edgeId) => {
    set((state) => ({
      edges: state.edges.filter((edge) => edge.id !== edgeId),
    }));
  },

  setEdges: (edges) => {
    set({ edges });
  },

  // Workflow validation
  validateWorkflow: () => {
    const { nodes, edges } = get();
    const errors: string[] = [];
    const nodeErrors = new Map<string, string[]>();

    // Check for exactly one trigger node
    const triggerNodes = nodes.filter((node) => node.type === 'trigger');
    if (triggerNodes.length === 0) {
      errors.push('Workflow must have exactly one trigger node');
    } else if (triggerNodes.length > 1) {
      errors.push('Workflow can only have one trigger node');
      triggerNodes.forEach((node) => {
        const errs = nodeErrors.get(node.id) || [];
        errs.push('Multiple trigger nodes detected');
        nodeErrors.set(node.id, errs);
      });
    }

    // Check for required config fields per node type
    nodes.forEach((node) => {
      const errs: string[] = [];

      if (!node.data.label) {
        errs.push('Missing label');
      }

      if (!node.data.config || Object.keys(node.data.config).length === 0) {
        errs.push('Missing configuration');
      } else {
        // Validate required fields per node type
        const config = node.data.config;
        
        switch (node.type) {
          case 'rag':
            if (!config.collection_name) errs.push('Missing collection_name');
            if (!config.query_template) errs.push('Missing query_template');
            if (config.result_limit === undefined || config.result_limit <= 0) {
              errs.push('Invalid result_limit');
            }
            break;
          case 'llm':
            if (!config.system_prompt) errs.push('Missing system_prompt');
            if (!config.user_prompt) errs.push('Missing user_prompt');
            if (config.temperature === undefined) errs.push('Missing temperature');
            if (config.max_tokens === undefined) errs.push('Missing max_tokens');
            break;
          case 'tool':
            if (!config.api_endpoint) errs.push('Missing api_endpoint');
            if (!config.http_method) errs.push('Missing http_method');
            break;
          case 'action':
            if (!config.integration) errs.push('Missing integration');
            if (!config.action_type) errs.push('Missing action_type');
            break;
          case 'decision':
            if (!config.classification_prompt) errs.push('Missing classification_prompt');
            if (!config.intents || config.intents.length === 0) {
              errs.push('Missing intents');
            }
            break;
          case 'graph_query':
            if (config.max_depth === undefined || config.max_depth <= 0) {
              errs.push('Invalid max_depth');
            }
            break;
          case 'multi_source_rag':
            if (!config.collections || config.collections.length === 0) {
              errs.push('Missing collections');
            }
            if (!config.query_template) errs.push('Missing query_template');
            break;
        }
      }

      if (errs.length > 0) {
        nodeErrors.set(node.id, errs);
        errors.push(`Node ${node.data.label || node.id}: ${errs.join(', ')}`);
      }
    });

    // Check for cycles using DFS
    const hasCycle = () => {
      const adjacencyList = new Map<string, string[]>();
      nodes.forEach((node) => adjacencyList.set(node.id, []));
      edges.forEach((edge) => {
        const targets = adjacencyList.get(edge.source) || [];
        targets.push(edge.target);
        adjacencyList.set(edge.source, targets);
      });

      const visited = new Set<string>();
      const recursionStack = new Set<string>();

      const dfs = (nodeId: string): boolean => {
        visited.add(nodeId);
        recursionStack.add(nodeId);

        const neighbors = adjacencyList.get(nodeId) || [];
        for (const neighbor of neighbors) {
          if (!visited.has(neighbor)) {
            if (dfs(neighbor)) return true;
          } else if (recursionStack.has(neighbor)) {
            return true;
          }
        }

        recursionStack.delete(nodeId);
        return false;
      };

      for (const nodeId of adjacencyList.keys()) {
        if (!visited.has(nodeId)) {
          if (dfs(nodeId)) return true;
        }
      }

      return false;
    };

    if (hasCycle()) {
      errors.push('Workflow contains cycles - must be a directed acyclic graph (DAG)');
    }

    // Validate context variable references
    const availableVariables = new Set<string>();
    
    // Build execution order to check variable availability
    const getTopologicalOrder = () => {
      const adjacencyList = new Map<string, string[]>();
      const inDegree = new Map<string, number>();
      
      nodes.forEach((node) => {
        adjacencyList.set(node.id, []);
        inDegree.set(node.id, 0);
      });
      
      edges.forEach((edge) => {
        const targets = adjacencyList.get(edge.source) || [];
        targets.push(edge.target);
        adjacencyList.set(edge.source, targets);
        inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
      });
      
      const queue: string[] = [];
      inDegree.forEach((degree, nodeId) => {
        if (degree === 0) queue.push(nodeId);
      });
      
      const order: string[] = [];
      while (queue.length > 0) {
        const nodeId = queue.shift()!;
        order.push(nodeId);
        
        const neighbors = adjacencyList.get(nodeId) || [];
        neighbors.forEach((neighbor) => {
          const newDegree = (inDegree.get(neighbor) || 0) - 1;
          inDegree.set(neighbor, newDegree);
          if (newDegree === 0) queue.push(neighbor);
        });
      }
      
      return order;
    };
    
    const executionOrder = getTopologicalOrder();
    
    executionOrder.forEach((nodeId) => {
      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return;
      
      // Add this node's output to available variables
      availableVariables.add(`${nodeId}_output`);
      availableVariables.add(nodeId);
      
      // Check if this node references any unavailable variables
      const configStr = JSON.stringify(node.data.config);
      const variablePattern = /\{\{([^}]+)\}\}/g;
      let match;
      
      while ((match = variablePattern.exec(configStr)) !== null) {
        const varName = match[1].trim();
        if (!availableVariables.has(varName) && varName !== 'trigger_output') {
          const errs = nodeErrors.get(nodeId) || [];
          errs.push(`References unavailable variable: {{${varName}}}`);
          nodeErrors.set(nodeId, errs);
          errors.push(`Node ${node.data.label || nodeId}: References unavailable variable {{${varName}}}`);
        }
      }
    });

    return {
      valid: errors.length === 0,
      errors,
      nodeErrors,
    };
  },

  // Compile workflow to JSON
  compileWorkflow: (metadata) => {
    const { nodes, edges } = get();
    
    return {
      version: '1.0.0',
      metadata: {
        ...metadata,
        updated_at: new Date().toISOString(),
      },
      nodes,
      edges,
    };
  },

  // Save workflow to backend
  saveWorkflow: async (token, agentId, metadata) => {
    const { validateWorkflow, compileWorkflow } = get();
    
    // Validate before saving
    const validation = validateWorkflow();
    if (!validation.valid) {
      throw new Error(`Workflow validation failed: ${validation.errors.join(', ')}`);
    }

    const workflowJSON = compileWorkflow(metadata);
    const apiClient = createApiClient(token);

    try {
      await apiClient.post('/api/workflows', {
        agent_id: agentId,
        workflow_json: workflowJSON,
      });
    } catch (error: any) {
      throw new Error(`Failed to save workflow: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Load workflow from backend
  loadWorkflow: async (token, agentId) => {
    const apiClient = createApiClient(token);

    try {
      const response = await apiClient.get(`/api/workflows/${agentId}`);
      const workflowJSON: WorkflowJSON = response.data.workflow_json;

      set({
        nodes: workflowJSON.nodes,
        edges: workflowJSON.edges,
        selectedNode: null,
      });
    } catch (error: any) {
      throw new Error(`Failed to load workflow: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Test workflow without saving
  testWorkflow: async (token, testInput) => {
    const { validateWorkflow, compileWorkflow } = get();
    
    // Validate before testing
    const validation = validateWorkflow();
    if (!validation.valid) {
      throw new Error(`Workflow validation failed: ${validation.errors.join(', ')}`);
    }

    const workflowJSON = compileWorkflow({
      workflow_name: 'Test Workflow',
      description: 'Testing workflow execution',
      created_by: 'test_user',
      updated_at: new Date().toISOString(),
    });

    const apiClient = createApiClient(token);

    try {
      const response = await apiClient.post('/api/workflows/test', {
        workflow_json: workflowJSON,
        test_input: testInput,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(`Failed to test workflow: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Clear workflow
  clearWorkflow: () => {
    set({
      nodes: [],
      edges: [],
      selectedNode: null,
    });
  },

  // Export workflow as JSON file
  exportWorkflow: (metadata: WorkflowJSON['metadata']) => {
    const { compileWorkflow } = get();
    const workflowJSON = compileWorkflow(metadata);
    
    // Create downloadable JSON file
    const blob = new Blob([JSON.stringify(workflowJSON, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${metadata.workflow_name.replace(/\s+/g, '_')}_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },

  // Import workflow from JSON file
  importWorkflow: (file: File): Promise<void> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          const workflowJSON: WorkflowJSON = JSON.parse(content);
          
          // Validate JSON structure
          if (!workflowJSON.version || !workflowJSON.metadata || !workflowJSON.nodes || !workflowJSON.edges) {
            throw new Error('Invalid workflow JSON structure: missing required fields');
          }
          
          // Validate node types
          const validNodeTypes = ['trigger', 'rag', 'llm', 'tool', 'action', 'decision', 'graph_query', 'knowledge', 'multi_source_rag', 'fallback'];
          for (const node of workflowJSON.nodes) {
            if (!validNodeTypes.includes(node.type)) {
              throw new Error(`Invalid node type: ${node.type}`);
            }
          }
          
          // Generate new unique node IDs to prevent conflicts
          const idMap = new Map<string, string>();
          const newNodes = workflowJSON.nodes.map((node) => {
            const newId = `${node.type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            idMap.set(node.id, newId);
            return {
              ...node,
              id: newId,
            };
          });
          
          // Update edge source/target references to use new IDs
          const newEdges = workflowJSON.edges.map((edge) => {
            const newSourceId = idMap.get(edge.source);
            const newTargetId = idMap.get(edge.target);
            
            if (!newSourceId || !newTargetId) {
              throw new Error(`Edge references invalid node: ${edge.source} -> ${edge.target}`);
            }
            
            return {
              ...edge,
              id: `${newSourceId}-${newTargetId}`,
              source: newSourceId,
              target: newTargetId,
            };
          });
          
          // Load nodes and edges into canvas
          set({
            nodes: newNodes,
            edges: newEdges,
            selectedNode: null,
          });
          
          resolve();
        } catch (error: any) {
          reject(new Error(`Failed to import workflow: ${error.message}`));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };
      
      reader.readAsText(file);
    });
  },
}));
