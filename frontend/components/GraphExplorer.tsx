'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useGraphStore, GraphNode, GraphLink } from '@/stores/graphStore';
import { useAuth } from '@/hooks/useAuth';
import NodeEditorModal from './NodeEditorModal';
import LinkEditorModal from './LinkEditorModal';

// Dynamically import ForceGraph2D to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
});

interface GraphExplorerProps {
  companyId: string;
}

export default function GraphExplorer({ companyId }: GraphExplorerProps) {
  const { token } = useAuth();
  const graphRef = useRef<any>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNodeEditor, setShowNodeEditor] = useState(false);
  const [showLinkEditor, setShowLinkEditor] = useState(false);
  const [editingNode, setEditingNode] = useState<GraphNode | null>(null);
  const [editingLink, setEditingLink] = useState<GraphLink | null>(null);
  
  const {
    graphData,
    selectedNode,
    selectedLink,
    entityTypeFilter,
    relationshipTypeFilter,
    searchQuery,
    pathFinderActive,
    pathStartNode,
    pathEndNode,
    pathResult,
    availableEntityTypes,
    availableRelationshipTypes,
    setSelectedNode,
    setSelectedLink,
    setEntityTypeFilter,
    setRelationshipTypeFilter,
    setSearchQuery,
    fetchGraphData,
    fetchGraphSchema,
    activatePathFinder,
    deactivatePathFinder,
    setPathStartNode,
    setPathEndNode,
    findShortestPath,
  } = useGraphStore();

  // Load graph data on mount
  useEffect(() => {
    if (token && companyId) {
      Promise.all([
        fetchGraphData(token, companyId),
        fetchGraphSchema(token, companyId),
      ])
        .then(() => setLoading(false))
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [token, companyId]);

  // Filter graph data based on filters and search
  const filteredGraphData = React.useMemo(() => {
    let nodes = graphData.nodes;
    let links = graphData.links;

    // Apply entity type filter
    if (entityTypeFilter.length > 0) {
      nodes = nodes.filter((node) => entityTypeFilter.includes(node.type));
      const nodeIds = new Set(nodes.map((n) => n.id));
      links = links.filter((link) => nodeIds.has(link.source) && nodeIds.has(link.target));
    }

    // Apply relationship type filter
    if (relationshipTypeFilter.length > 0) {
      links = links.filter((link) => relationshipTypeFilter.includes(link.type));
    }

    // Apply search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      nodes = nodes.filter((node) =>
        node.name.toLowerCase().includes(query) ||
        node.type.toLowerCase().includes(query)
      );
      const nodeIds = new Set(nodes.map((n) => n.id));
      links = links.filter((link) => nodeIds.has(link.source) && nodeIds.has(link.target));
    }

    return { nodes, links };
  }, [graphData, entityTypeFilter, relationshipTypeFilter, searchQuery]);

  // Handle node click
  const handleNodeClick = useCallback((node: any) => {
    if (pathFinderActive) {
      // Path finder mode
      if (!pathStartNode) {
        setPathStartNode(node);
      } else if (!pathEndNode) {
        setPathEndNode(node);
        // Find path
        if (token) {
          findShortestPath(token, pathStartNode.id, node.id);
        }
      } else {
        // Reset and start over
        setPathStartNode(node);
        setPathEndNode(null);
      }
    } else {
      // Normal selection mode
      setSelectedNode(node);
      setSelectedLink(null);
    }
  }, [pathFinderActive, pathStartNode, pathEndNode, token]);

  // Handle link click
  const handleLinkClick = useCallback((link: any) => {
    if (!pathFinderActive) {
      setSelectedLink(link);
      setSelectedNode(null);
    }
  }, [pathFinderActive]);

  // Node color based on type
  const getNodeColor = useCallback((node: GraphNode) => {
    const colors: Record<string, string> = {
      Person: '#3b82f6',
      Project: '#10b981',
      Product: '#f59e0b',
      Department: '#8b5cf6',
      Document: '#ef4444',
    };
    return colors[node.type] || '#6b7280';
  }, []);

  // Highlight nodes in path
  const getNodeSize = useCallback((node: GraphNode) => {
    if (pathResult) {
      const inPath = pathResult.nodes.some((n) => n.id === node.id);
      return inPath ? 8 : 4;
    }
    if (node.id === selectedNode?.id) return 8;
    if (node.id === pathStartNode?.id || node.id === pathEndNode?.id) return 7;
    return 4;
  }, [pathResult, selectedNode, pathStartNode, pathEndNode]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading knowledge graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-red-600">
          <p className="text-lg font-semibold">Error loading graph</p>
          <p className="mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-explorer-container">
      {/* Toolbar */}
      <div className="graph-toolbar bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Search */}
            <input
              type="text"
              placeholder="Search entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            {/* Entity Type Filter */}
            <select
              multiple
              value={entityTypeFilter}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                setEntityTypeFilter(selected);
              }}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Entity Types</option>
              {availableEntityTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>

            {/* Relationship Type Filter */}
            <select
              multiple
              value={relationshipTypeFilter}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                setRelationshipTypeFilter(selected);
              }}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Relationship Types</option>
              {availableRelationshipTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            {/* Create Node Button */}
            <button
              onClick={() => {
                setEditingNode(null);
                setShowNodeEditor(true);
              }}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              ➕ Add Node
            </button>

            {/* Create Link Button */}
            <button
              onClick={() => {
                setEditingLink(null);
                setShowLinkEditor(true);
              }}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              disabled={graphData.nodes.length < 2}
            >
              🔗 Add Edge
            </button>

            {/* Path Finder Toggle */}
            <button
              onClick={() => {
                if (pathFinderActive) {
                  deactivatePathFinder();
                } else {
                  activatePathFinder();
                }
              }}
              className={`px-4 py-2 rounded-lg transition-colors ${
                pathFinderActive
                  ? 'bg-purple-600 text-white'
                  : 'bg-purple-500 text-white hover:bg-purple-600'
              }`}
            >
              {pathFinderActive ? '🔍 Path Finder Active' : '🔍 Find Path'}
            </button>

            {/* Stats */}
            <div className="text-sm text-gray-600">
              {filteredGraphData.nodes.length} nodes, {filteredGraphData.links.length} edges
            </div>
          </div>
        </div>

        {/* Path Finder Status */}
        {pathFinderActive && (
          <div className="mt-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <p className="text-sm text-purple-800">
              {!pathStartNode && 'Click a node to select start point'}
              {pathStartNode && !pathEndNode && `Start: ${pathStartNode.name}. Click another node to find path.`}
              {pathStartNode && pathEndNode && pathResult && (
                <span>
                  Path found: {pathResult.length} hop{pathResult.length !== 1 ? 's' : ''} from{' '}
                  <strong>{pathStartNode.name}</strong> to <strong>{pathEndNode.name}</strong>
                </span>
              )}
              {pathStartNode && pathEndNode && !pathResult && 'No path found between selected nodes'}
            </p>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="graph-content">
        {/* Graph Visualization */}
        <div className="graph-canvas">
          <ForceGraph2D
            ref={graphRef}
            graphData={filteredGraphData}
            nodeLabel={(node: any) => `${node.name} (${node.type})`}
            nodeColor={(node: any) => getNodeColor(node)}
            nodeVal={(node: any) => getNodeSize(node)}
            linkLabel={(link: any) => `${link.type} (confidence: ${link.confidence?.toFixed(2) || 'N/A'})`}
            linkColor={(link: any) => {
              if (pathResult) {
                const inPath = pathResult.relationships.some((r) => r.id === link.id);
                return inPath ? '#8b5cf6' : '#d1d5db';
              }
              return link.id === selectedLink?.id ? '#3b82f6' : '#d1d5db';
            }}
            linkWidth={(link: any) => {
              if (pathResult) {
                const inPath = pathResult.relationships.some((r) => r.id === link.id);
                return inPath ? 3 : 1;
              }
              return link.id === selectedLink?.id ? 3 : 1;
            }}
            linkDirectionalArrowLength={6}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
            onLinkClick={handleLinkClick}
            cooldownTicks={100}
            onEngineStop={() => graphRef.current?.zoomToFit(400)}
          />
        </div>

        {/* Side Panel */}
        <div className="graph-side-panel bg-white border-l border-gray-200 p-4 overflow-y-auto">
          {selectedNode && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Node Details</h3>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-600">Name</label>
                  <p className="text-gray-800">{selectedNode.name}</p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">Type</label>
                  <p className="text-gray-800">{selectedNode.type}</p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">Properties</label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border border-gray-200">
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                      {JSON.stringify(selectedNode.properties, null, 2)}
                    </pre>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">Connections</label>
                  <div className="mt-1 space-y-1">
                    {graphData.links
                      .filter(
                        (link) =>
                          link.source === selectedNode.id || link.target === selectedNode.id
                      )
                      .map((link) => (
                        <div
                          key={link.id}
                          className="p-2 bg-gray-50 rounded border border-gray-200 text-sm"
                        >
                          <span className="font-medium text-blue-600">{link.type}</span>
                          {link.source === selectedNode.id ? ' → ' : ' ← '}
                          <span>
                            {link.source === selectedNode.id
                              ? graphData.nodes.find((n) => n.id === link.target)?.name
                              : graphData.nodes.find((n) => n.id === link.source)?.name}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>

                <div className="pt-3 border-t border-gray-200">
                  <button
                    onClick={() => {
                      setEditingNode(selectedNode);
                      setShowNodeEditor(true);
                    }}
                    className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Edit Node
                  </button>
                </div>
              </div>
            </div>
          )}

          {selectedLink && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Edge Details</h3>
                <button
                  onClick={() => setSelectedLink(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-600">Relationship Type</label>
                  <p className="text-gray-800">{selectedLink.type}</p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">From</label>
                  <p className="text-gray-800">
                    {graphData.nodes.find((n) => n.id === selectedLink.source)?.name || 'Unknown'}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">To</label>
                  <p className="text-gray-800">
                    {graphData.nodes.find((n) => n.id === selectedLink.target)?.name || 'Unknown'}
                  </p>
                </div>

                {selectedLink.source_document_id && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">Source Document</label>
                    <p className="text-gray-800 text-sm">{selectedLink.source_document_id}</p>
                  </div>
                )}

                {selectedLink.confidence !== undefined && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">Confidence Score</label>
                    <p className="text-gray-800">{(selectedLink.confidence * 100).toFixed(1)}%</p>
                  </div>
                )}

                <div>
                  <label className="text-sm font-medium text-gray-600">Properties</label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border border-gray-200">
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                      {JSON.stringify(selectedLink.properties, null, 2)}
                    </pre>
                  </div>
                </div>

                <div className="pt-3 border-t border-gray-200">
                  <button
                    onClick={() => {
                      setEditingLink(selectedLink);
                      setShowLinkEditor(true);
                    }}
                    className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Edit Edge
                  </button>
                </div>
              </div>
            </div>
          )}

          {!selectedNode && !selectedLink && (
            <div className="text-center text-gray-500 mt-8">
              <p>Click a node or edge to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Node Editor Modal */}
      <NodeEditorModal
        node={editingNode}
        isOpen={showNodeEditor}
        onClose={() => {
          setShowNodeEditor(false);
          setEditingNode(null);
        }}
        onSave={async (node) => {
          if (editingNode) {
            await useGraphStore.getState().updateNode(node.id, node);
          } else {
            await useGraphStore.getState().addNode(node);
          }
          if (token) {
            await fetchGraphData(token, companyId);
          }
        }}
        onDelete={async (nodeId) => {
          await useGraphStore.getState().deleteNode(nodeId);
          if (token) {
            await fetchGraphData(token, companyId);
          }
        }}
        availableTypes={availableEntityTypes}
      />

      {/* Link Editor Modal */}
      <LinkEditorModal
        link={editingLink}
        nodes={graphData.nodes}
        isOpen={showLinkEditor}
        onClose={() => {
          setShowLinkEditor(false);
          setEditingLink(null);
        }}
        onSave={async (link) => {
          if (editingLink) {
            await useGraphStore.getState().updateLink(link.id, link);
          } else {
            await useGraphStore.getState().addLink(link);
          }
          if (token) {
            await fetchGraphData(token, companyId);
          }
        }}
        onDelete={async (linkId) => {
          await useGraphStore.getState().deleteLink(linkId);
          if (token) {
            await fetchGraphData(token, companyId);
          }
        }}
        availableTypes={availableRelationshipTypes}
      />

      <style jsx>{`
        .graph-explorer-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          overflow: hidden;
        }

        .graph-toolbar {
          flex-shrink: 0;
        }

        .graph-content {
          flex: 1;
          display: grid;
          grid-template-columns: 1fr 400px;
          overflow: hidden;
        }

        .graph-canvas {
          position: relative;
          background: #f9fafb;
        }

        .graph-side-panel {
          overflow-y: auto;
        }
      `}</style>
    </div>
  );
}
