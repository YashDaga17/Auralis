import { create } from 'zustand';

export interface GraphNode {
  id: string;
  name: string;
  type: string; // Person, Project, Product, Department, Document, etc.
  properties: Record<string, any>;
  company_id: string;
}

export interface GraphLink {
  id: string;
  source: string;
  target: string;
  type: string; // MANAGES, OWNS, REPORTS_TO, WORKS_ON, CREATED, etc.
  properties: Record<string, any>;
  source_document_id?: string;
  confidence?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface PathResult {
  nodes: GraphNode[];
  relationships: GraphLink[];
  length: number;
}

interface GraphStore {
  // Graph data
  graphData: GraphData;
  selectedNode: GraphNode | null;
  selectedLink: GraphLink | null;
  
  // Filters
  entityTypeFilter: string[];
  relationshipTypeFilter: string[];
  searchQuery: string;
  
  // Path finder
  pathFinderActive: boolean;
  pathStartNode: GraphNode | null;
  pathEndNode: GraphNode | null;
  pathResult: PathResult | null;
  
  // Available types (from schema)
  availableEntityTypes: string[];
  availableRelationshipTypes: string[];
  
  // Actions
  setGraphData: (data: GraphData) => void;
  setSelectedNode: (node: GraphNode | null) => void;
  setSelectedLink: (link: GraphLink | null) => void;
  setEntityTypeFilter: (types: string[]) => void;
  setRelationshipTypeFilter: (types: string[]) => void;
  setSearchQuery: (query: string) => void;
  setAvailableTypes: (entityTypes: string[], relationshipTypes: string[]) => void;
  
  // Path finder actions
  activatePathFinder: () => void;
  deactivatePathFinder: () => void;
  setPathStartNode: (node: GraphNode | null) => void;
  setPathEndNode: (node: GraphNode | null) => void;
  setPathResult: (result: PathResult | null) => void;
  
  // Graph editing actions
  addNode: (node: Omit<GraphNode, 'id'>) => Promise<GraphNode>;
  updateNode: (nodeId: string, updates: Partial<GraphNode>) => Promise<void>;
  deleteNode: (nodeId: string) => Promise<void>;
  addLink: (link: Omit<GraphLink, 'id'>) => Promise<GraphLink>;
  updateLink: (linkId: string, updates: Partial<GraphLink>) => Promise<void>;
  deleteLink: (linkId: string) => Promise<void>;
  
  // Data fetching
  fetchGraphData: (token: string, companyId: string) => Promise<void>;
  fetchGraphSchema: (token: string, companyId: string) => Promise<void>;
  findShortestPath: (token: string, startNodeId: string, endNodeId: string) => Promise<void>;
}

export const useGraphStore = create<GraphStore>((set, get) => ({
  // Initial state
  graphData: { nodes: [], links: [] },
  selectedNode: null,
  selectedLink: null,
  entityTypeFilter: [],
  relationshipTypeFilter: [],
  searchQuery: '',
  pathFinderActive: false,
  pathStartNode: null,
  pathEndNode: null,
  pathResult: null,
  availableEntityTypes: [],
  availableRelationshipTypes: [],
  
  // Basic setters
  setGraphData: (data) => set({ graphData: data }),
  setSelectedNode: (node) => set({ selectedNode: node }),
  setSelectedLink: (link) => set({ selectedLink: link }),
  setEntityTypeFilter: (types) => set({ entityTypeFilter: types }),
  setRelationshipTypeFilter: (types) => set({ relationshipTypeFilter: types }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setAvailableTypes: (entityTypes, relationshipTypes) => 
    set({ availableEntityTypes: entityTypes, availableRelationshipTypes: relationshipTypes }),
  
  // Path finder actions
  activatePathFinder: () => set({ 
    pathFinderActive: true, 
    pathStartNode: null, 
    pathEndNode: null, 
    pathResult: null 
  }),
  deactivatePathFinder: () => set({ 
    pathFinderActive: false, 
    pathStartNode: null, 
    pathEndNode: null, 
    pathResult: null 
  }),
  setPathStartNode: (node) => set({ pathStartNode: node }),
  setPathEndNode: (node) => set({ pathEndNode: node }),
  setPathResult: (result) => set({ pathResult: result }),
  
  // Graph editing actions
  addNode: async (nodeData) => {
    // This will be implemented with API calls
    const newNode: GraphNode = {
      ...nodeData,
      id: `node_${Date.now()}`,
    };
    
    const currentData = get().graphData;
    set({
      graphData: {
        ...currentData,
        nodes: [...currentData.nodes, newNode],
      },
    });
    
    return newNode;
  },
  
  updateNode: async (nodeId, updates) => {
    const currentData = get().graphData;
    set({
      graphData: {
        ...currentData,
        nodes: currentData.nodes.map((node) =>
          node.id === nodeId ? { ...node, ...updates } : node
        ),
      },
    });
  },
  
  deleteNode: async (nodeId) => {
    const currentData = get().graphData;
    set({
      graphData: {
        nodes: currentData.nodes.filter((node) => node.id !== nodeId),
        links: currentData.links.filter(
          (link) => link.source !== nodeId && link.target !== nodeId
        ),
      },
    });
  },
  
  addLink: async (linkData) => {
    const newLink: GraphLink = {
      ...linkData,
      id: `link_${Date.now()}`,
    };
    
    const currentData = get().graphData;
    set({
      graphData: {
        ...currentData,
        links: [...currentData.links, newLink],
      },
    });
    
    return newLink;
  },
  
  updateLink: async (linkId, updates) => {
    const currentData = get().graphData;
    set({
      graphData: {
        ...currentData,
        links: currentData.links.map((link) =>
          link.id === linkId ? { ...link, ...updates } : link
        ),
      },
    });
  },
  
  deleteLink: async (linkId) => {
    const currentData = get().graphData;
    set({
      graphData: {
        ...currentData,
        links: currentData.links.filter((link) => link.id !== linkId),
      },
    });
  },
  
  // Fetch graph data from backend
  fetchGraphData: async (token, companyId) => {
    try {
      const { createApiClient } = await import('@/lib/api-client');
      const client = createApiClient(token);
      
      // Query to get all nodes and relationships for the company
      const query = `
        MATCH (n {company_id: $company_id})
        OPTIONAL MATCH (n)-[r]->(m {company_id: $company_id})
        RETURN n, r, m
      `;
      
      const response = await client.post('/api/knowledge/graph/query', {
        query,
        parameters: { company_id: companyId },
      });
      
      const results = response.data.results;
      
      // Transform Neo4j results to graph data
      const nodesMap = new Map<string, GraphNode>();
      const links: GraphLink[] = [];
      
      results.forEach((record: any) => {
        // Add source node
        if (record.n) {
          const nodeId = record.n.id.toString();
          if (!nodesMap.has(nodeId)) {
            nodesMap.set(nodeId, {
              id: nodeId,
              name: record.n.properties.name || nodeId,
              type: record.n.labels[0] || 'Unknown',
              properties: record.n.properties,
              company_id: companyId,
            });
          }
        }
        
        // Add target node
        if (record.m) {
          const nodeId = record.m.id.toString();
          if (!nodesMap.has(nodeId)) {
            nodesMap.set(nodeId, {
              id: nodeId,
              name: record.m.properties.name || nodeId,
              type: record.m.labels[0] || 'Unknown',
              properties: record.m.properties,
              company_id: companyId,
            });
          }
        }
        
        // Add relationship
        if (record.r) {
          links.push({
            id: record.r.id.toString(),
            source: record.r.start_node.toString(),
            target: record.r.end_node.toString(),
            type: record.r.type,
            properties: record.r.properties,
            source_document_id: record.r.properties.source_document_id,
            confidence: record.r.properties.confidence,
          });
        }
      });
      
      set({
        graphData: {
          nodes: Array.from(nodesMap.values()),
          links,
        },
      });
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
      throw error;
    }
  },
  
  // Fetch graph schema
  fetchGraphSchema: async (token, companyId) => {
    try {
      const { createApiClient } = await import('@/lib/api-client');
      const client = createApiClient(token);
      
      const response = await client.get('/api/knowledge/graph/schema', {
        params: { company_id: companyId },
      });
      
      const schema = response.data;
      set({
        availableEntityTypes: schema.entity_types || [],
        availableRelationshipTypes: schema.relationship_types || [],
      });
    } catch (error) {
      console.error('Failed to fetch graph schema:', error);
      throw error;
    }
  },
  
  // Find shortest path between two nodes
  findShortestPath: async (token, startNodeId, endNodeId) => {
    try {
      const { createApiClient } = await import('@/lib/api-client');
      const client = createApiClient(token);
      
      const query = `
        MATCH path = shortestPath(
          (start {company_id: $company_id})-[*]-(end {company_id: $company_id})
        )
        WHERE id(start) = $start_id AND id(end) = $end_id
        RETURN path
      `;
      
      const response = await client.post('/api/knowledge/graph/query', {
        query,
        parameters: {
          company_id: get().graphData.nodes[0]?.company_id || '',
          start_id: parseInt(startNodeId),
          end_id: parseInt(endNodeId),
        },
      });
      
      const results = response.data.results;
      
      if (results.length > 0 && results[0].path) {
        const path = results[0].path;
        
        const pathNodes: GraphNode[] = path.nodes.map((node: any) => ({
          id: node.id.toString(),
          name: node.properties.name || node.id.toString(),
          type: node.labels[0] || 'Unknown',
          properties: node.properties,
          company_id: node.properties.company_id,
        }));
        
        const pathLinks: GraphLink[] = path.relationships.map((rel: any) => ({
          id: rel.id.toString(),
          source: rel.start_node.toString(),
          target: rel.end_node.toString(),
          type: rel.type,
          properties: rel.properties,
          source_document_id: rel.properties.source_document_id,
          confidence: rel.properties.confidence,
        }));
        
        set({
          pathResult: {
            nodes: pathNodes,
            relationships: pathLinks,
            length: pathNodes.length - 1,
          },
        });
      } else {
        set({ pathResult: null });
      }
    } catch (error) {
      console.error('Failed to find shortest path:', error);
      throw error;
    }
  },
}));
