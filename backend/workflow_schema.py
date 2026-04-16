"""
Pydantic models for Workflow JSON schema validation.

This module defines the data models for visual workflow configurations,
including nodes, edges, and complete workflow structures.

Requirements: 19.1, 19.2, 19.3, 19.4, 19.5
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from enum import Enum


class NodeType(str, Enum):
    """Enumeration of available node types in the workflow system."""
    TRIGGER = "trigger"
    RAG = "rag"
    LLM = "llm"
    TOOL = "tool"
    ACTION = "action"
    DECISION = "decision"
    GRAPH_QUERY = "graph_query"
    KNOWLEDGE = "knowledge"
    MULTI_SOURCE_RAG = "multi_source_rag"
    FALLBACK = "fallback"


class Position(BaseModel):
    """Node position on the canvas."""
    x: float = Field(..., description="X coordinate on canvas")
    y: float = Field(..., description="Y coordinate on canvas")


class NodeData(BaseModel):
    """Node data containing label and configuration."""
    label: str = Field(..., description="Display label for the node")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node-specific configuration")


class WorkflowNode(BaseModel):
    """
    Represents a single node in the workflow graph.
    
    Each node has a unique ID, type, configuration data, and canvas position.
    """
    id: str = Field(..., description="Unique node identifier")
    type: NodeType = Field(..., description="Node type determining execution behavior")
    data: NodeData = Field(..., description="Node configuration and display data")
    position: Position = Field(..., description="Canvas position for visual rendering")

    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure node ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Node ID cannot be empty")
        return v.strip()


class WorkflowEdge(BaseModel):
    """
    Represents a directed edge connecting two nodes in the workflow.
    
    Edges define the data flow and execution order between nodes.
    """
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    sourceHandle: Optional[str] = Field(None, description="Source node handle for multi-output nodes")
    targetHandle: Optional[str] = Field(None, description="Target node handle for multi-input nodes")
    label: Optional[str] = Field(None, description="Edge label (e.g., intent name for decision routing)")

    @field_validator('id', 'source', 'target')
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Ensure IDs are not empty."""
        if not v or not v.strip():
            raise ValueError("Edge ID, source, and target cannot be empty")
        return v.strip()


class WorkflowMetadata(BaseModel):
    """Metadata describing the workflow."""
    workflow_name: str = Field(..., description="Human-readable workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    created_by: str = Field(..., description="User who created the workflow")
    updated_at: str = Field(..., description="ISO 8601 timestamp of last update")

    @field_validator('updated_at')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO 8601 timestamp format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("updated_at must be a valid ISO 8601 timestamp")
        return v


class WorkflowJSON(BaseModel):
    """
    Complete workflow configuration in JSON format.
    
    This is the root model that represents the entire workflow graph,
    including all nodes, edges, and metadata.
    
    Requirements: 19.1, 19.2, 19.3, 19.4
    """
    version: str = Field(..., description="Schema version (e.g., 1.0.0)", pattern=r"^\d+\.\d+\.\d+$")
    metadata: WorkflowMetadata = Field(..., description="Workflow metadata")
    nodes: List[WorkflowNode] = Field(..., min_length=1, description="Array of workflow nodes")
    edges: List[WorkflowEdge] = Field(default_factory=list, description="Array of workflow edges")

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        parts = v.split('.')
        if len(parts) != 3:
            raise ValueError("Version must be in format X.Y.Z")
        for part in parts:
            if not part.isdigit():
                raise ValueError("Version parts must be numeric")
        return v

    @model_validator(mode='after')
    def validate_edge_references(self) -> 'WorkflowJSON':
        """Validate that all edges reference existing nodes."""
        node_ids = {node.id for node in self.nodes}
        
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge {edge.id} references non-existent source node: {edge.source}")
            if edge.target not in node_ids:
                raise ValueError(f"Edge {edge.id} references non-existent target node: {edge.target}")
        
        return self


# Node-specific configuration schemas

class RAGNodeConfig(BaseModel):
    """Configuration schema for RAG (Retrieval-Augmented Generation) nodes."""
    collection_name: str = Field(..., description="Qdrant collection to search")
    query_template: str = Field(..., description="Query template with {{context_vars}} support")
    result_limit: int = Field(default=5, ge=1, le=20, description="Maximum number of results to retrieve")
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters for search")


class LLMNodeConfig(BaseModel):
    """Configuration schema for LLM (Language Model) nodes."""
    system_prompt: str = Field(..., description="System prompt for the LLM")
    user_prompt: str = Field(..., description="User prompt template with {{context_vars}} support")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1024, ge=1, le=8192, description="Maximum tokens to generate")
    model: Literal["gemini-2.5-flash", "gemini-2.5-pro"] = Field(
        default="gemini-2.5-flash",
        description="Model to use for generation"
    )


class ToolNodeConfig(BaseModel):
    """Configuration schema for Tool nodes (external API calls)."""
    api_endpoint: str = Field(..., description="API endpoint URL")
    http_method: Literal["GET", "POST", "PUT", "DELETE"] = Field(..., description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    request_body: Optional[str] = Field(None, description="Request body JSON template with {{context_vars}}")
    timeout_ms: int = Field(default=5000, ge=100, le=30000, description="Request timeout in milliseconds")


class GraphQueryNodeConfig(BaseModel):
    """Configuration schema for Graph Query nodes."""
    max_depth: int = Field(default=3, ge=1, le=10, description="Maximum relationship hops")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types")
    relationship_types: Optional[List[str]] = Field(None, description="Filter by relationship types")
    timeout_ms: int = Field(default=5000, ge=100, le=30000, description="Query timeout in milliseconds")


class ActionNodeConfig(BaseModel):
    """Configuration schema for Action nodes (business workflow execution)."""
    integration: Literal["hubspot", "calendly", "zendesk", "salesforce"] = Field(
        ...,
        description="Integration platform"
    )
    action_type: str = Field(..., description="Action to execute (e.g., 'create_contact')")
    parameters: Dict[str, str] = Field(..., description="Action parameters with {{context_vars}} support")
    require_confirmation: bool = Field(default=False, description="Whether to require user confirmation")


class DecisionNodeConfig(BaseModel):
    """Configuration schema for Decision nodes (intent classification and routing)."""
    classification_prompt: str = Field(..., description="Prompt for intent classification")
    intents: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of intents with name, description, and confidence_threshold"
    )
    fallback_intent: str = Field(..., description="Default intent when confidence is low")

    @field_validator('intents')
    @classmethod
    def validate_intents(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate intent structure."""
        for intent in v:
            if 'name' not in intent or 'description' not in intent:
                raise ValueError("Each intent must have 'name' and 'description' fields")
        return v


class MultiSourceRAGNodeConfig(BaseModel):
    """Configuration schema for Multi-Source RAG nodes."""
    collections: List[str] = Field(..., min_length=1, description="List of Qdrant collections to search")
    query_template: str = Field(..., description="Query template with {{context_vars}} support")
    result_limit: int = Field(default=5, ge=1, le=20, description="Maximum results per collection")
    collection_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Optional weights for prioritizing collections"
    )


class KnowledgeNodeConfig(BaseModel):
    """Configuration schema for Knowledge nodes (uploaded documents)."""
    filename: str = Field(..., description="Original filename")
    collection_name: str = Field(..., description="Qdrant collection containing the document")
    chunk_count: int = Field(..., ge=0, description="Number of chunks in the document")
    file_type: str = Field(..., description="File type (e.g., 'pdf', 'docx', 'txt')")


class FallbackNodeConfig(BaseModel):
    """Configuration schema for Fallback nodes (error handling)."""
    fallback_message: str = Field(..., description="Message to return on error")
    log_errors: bool = Field(default=True, description="Whether to log error details")


# Mapping of node types to their configuration schemas
NODE_CONFIG_SCHEMAS = {
    NodeType.RAG: RAGNodeConfig,
    NodeType.LLM: LLMNodeConfig,
    NodeType.TOOL: ToolNodeConfig,
    NodeType.GRAPH_QUERY: GraphQueryNodeConfig,
    NodeType.ACTION: ActionNodeConfig,
    NodeType.DECISION: DecisionNodeConfig,
    NodeType.MULTI_SOURCE_RAG: MultiSourceRAGNodeConfig,
    NodeType.KNOWLEDGE: KnowledgeNodeConfig,
    NodeType.FALLBACK: FallbackNodeConfig,
}
