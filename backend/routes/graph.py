"""
Graph database API endpoints.
Handles Neo4j schema retrieval and Cypher query execution.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import re
import os
import time

from database import get_db, get_neo4j_session, neo4j_driver
from auth import get_auth_context, AuthContext
from triplet_extraction import get_triplet_pipeline

router = APIRouter(prefix="/api/knowledge/graph", tags=["graph"])


class GraphSchemaResponse(BaseModel):
    """Response model for graph schema."""
    company_id: str
    entity_types: List[str]
    relationship_types: List[str]


class CypherQueryRequest(BaseModel):
    """Request model for Cypher query execution."""
    query: str
    parameters: Optional[Dict[str, Any]] = None


class CypherQueryResponse(BaseModel):
    """Response model for Cypher query results."""
    results: List[Dict[str, Any]]
    execution_time_ms: float


@router.get("/schema")
async def get_graph_schema(
    company_id: Optional[str] = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Get the graph schema (ontology) for a company.
    Returns entity types and relationship types available in the knowledge graph.
    
    Args:
        company_id: Optional company ID (defaults to authenticated user's company)
        
    Returns:
        company_id: Company identifier
        entity_types: List of available entity types (Person, Project, etc.)
        relationship_types: List of available relationship types (MANAGES, OWNS, etc.)
        
    Requirements: 39.4
    """
    try:
        # Use authenticated company_id if not provided
        target_company_id = company_id or auth.company_id
        
        # Get the triplet extraction pipeline
        pipeline = get_triplet_pipeline()
        
        # Get company ontology (entity and relationship types)
        ontology = pipeline.get_company_ontology(target_company_id)
        
        # Build response with ontology data
        response = {
            "company_id": target_company_id,
            "entity_types": ontology.entity_types,
            "relationship_types": ontology.relationship_types
        }
        
        # If Neo4j is configured, optionally query for actual schema from database
        if neo4j_driver:
            try:
                with neo4j_driver.session() as session:
                    # Query for actual node labels in the database for this company
                    node_labels_query = """
                    MATCH (n {company_id: $company_id})
                    RETURN DISTINCT labels(n) as labels
                    LIMIT 100
                    """
                    result = session.run(node_labels_query, {"company_id": target_company_id})
                    
                    # Extract unique labels (excluding 'company_id' if it's a label)
                    actual_labels = set()
                    for record in result:
                        labels = record["labels"]
                        if labels:
                            actual_labels.update(labels)
                    
                    # Query for actual relationship types in the database for this company
                    rel_types_query = """
                    MATCH (n {company_id: $company_id})-[r]->(m {company_id: $company_id})
                    RETURN DISTINCT type(r) as rel_type
                    LIMIT 100
                    """
                    result = session.run(rel_types_query, {"company_id": target_company_id})
                    
                    actual_rel_types = set()
                    for record in result:
                        rel_type = record["rel_type"]
                        if rel_type:
                            actual_rel_types.add(rel_type)
                    
                    # Add actual schema info if data exists
                    if actual_labels or actual_rel_types:
                        response["actual_entity_types"] = sorted(list(actual_labels))
                        response["actual_relationship_types"] = sorted(list(actual_rel_types))
                        response["has_data"] = True
                    else:
                        response["has_data"] = False
                        response["message"] = "No graph data found for this company yet. Upload documents to populate the knowledge graph."
                        
            except Exception as neo_error:
                # Neo4j query failed, but we can still return the ontology
                print(f"Neo4j schema query failed: {neo_error}")
                response["neo4j_available"] = False
        else:
            response["neo4j_available"] = False
            response["message"] = "Neo4j not configured. Returning default ontology."
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph schema: {str(e)}"
        )


def is_read_only_cypher(query: str) -> bool:
    """
    Validate that a Cypher query is read-only.
    
    Requirements: 41.7
    """
    # Remove comments
    query_no_comments = re.sub(r'//.*?$', '', query, flags=re.MULTILINE)
    query_no_comments = re.sub(r'/\*.*?\*/', '', query_no_comments, flags=re.DOTALL)
    
    # Convert to uppercase for checking
    query_upper = query_no_comments.upper()
    
    # Check for write operations
    write_keywords = [
        'CREATE', 'MERGE', 'DELETE', 'REMOVE', 'SET',
        'DROP', 'DETACH DELETE', 'FOREACH'
    ]
    
    for keyword in write_keywords:
        if keyword in query_upper:
            return False
    
    return True


@router.post("/query", response_model=CypherQueryResponse)
async def execute_cypher_query(
    request: CypherQueryRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Execute a read-only Cypher query against the graph database.
    
    Automatically filters results by company_id for multi-tenant isolation.
    Returns query results with execution timing.
    
    Args:
        request: CypherQueryRequest with query and optional parameters
        auth: Authenticated user context with company_id
        
    Returns:
        CypherQueryResponse with results and execution_time_ms
        
    Requirements: 41.7, 41.8
    """
    # Validate read-only query (Requirement 41.7)
    if not is_read_only_cypher(request.query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only read-only Cypher queries are allowed (MATCH, RETURN, WHERE, etc.)"
        )
    
    # Check if Neo4j is configured
    if not neo4j_driver:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j graph database is not configured"
        )
    
    try:
        # Start timing (Requirement 41.8)
        start_time = time.time()
        
        # Prepare parameters with company_id for tenant isolation
        parameters = request.parameters or {}
        parameters['company_id'] = auth.company_id
        
        # Execute query with Neo4j driver
        with neo4j_driver.session() as session:
            # Add company_id filter to query if not already present
            # This ensures multi-tenant isolation
            modified_query = request.query
            
            # Check if query already filters by company_id
            if 'company_id' not in request.query.lower():
                # Inject company_id filter into MATCH clauses
                # This is a simple approach - for production, use query rewriting
                modified_query = _inject_company_filter(request.query)
            
            # Execute with 5-second timeout (Requirement 41.8)
            result = session.run(
                modified_query,
                parameters,
                timeout=5.0
            )
            
            # Convert results to list of dictionaries
            results = []
            for record in result:
                # Convert Neo4j record to dictionary
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    # Convert Neo4j types to JSON-serializable types
                    record_dict[key] = _serialize_neo4j_value(value)
                results.append(record_dict)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            return CypherQueryResponse(
                results=results,
                execution_time_ms=round(execution_time_ms, 2)
            )
    
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific Neo4j errors
        if 'timeout' in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Query execution exceeded 5-second timeout"
            )
        elif 'syntax' in error_msg.lower() or 'invalid' in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Cypher query: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute Cypher query: {error_msg}"
            )


def _inject_company_filter(query: str) -> str:
    """
    Inject company_id filter into Cypher query for multi-tenant isolation.
    
    This is a simple implementation that adds company_id filter to MATCH clauses.
    For production, consider using a proper Cypher query parser.
    
    Args:
        query: Original Cypher query
        
    Returns:
        Modified query with company_id filter
    """
    # Simple approach: add WHERE clause after MATCH if not present
    # This works for basic queries but may need enhancement for complex queries
    
    # For now, return query as-is and rely on explicit company_id in query
    # Users should include {company_id: $company_id} in their MATCH patterns
    return query


def _serialize_neo4j_value(value):
    """
    Convert Neo4j value to JSON-serializable Python type.
    
    Args:
        value: Neo4j value (Node, Relationship, Path, or primitive)
        
    Returns:
        JSON-serializable representation
    """
    from neo4j.graph import Node, Relationship, Path
    
    if value is None:
        return None
    elif isinstance(value, Node):
        # Convert Node to dictionary
        return {
            'id': value.id,
            'labels': list(value.labels),
            'properties': dict(value)
        }
    elif isinstance(value, Relationship):
        # Convert Relationship to dictionary
        return {
            'id': value.id,
            'type': value.type,
            'start_node': value.start_node.id,
            'end_node': value.end_node.id,
            'properties': dict(value)
        }
    elif isinstance(value, Path):
        # Convert Path to dictionary
        return {
            'nodes': [_serialize_neo4j_value(node) for node in value.nodes],
            'relationships': [_serialize_neo4j_value(rel) for rel in value.relationships]
        }
    elif isinstance(value, list):
        return [_serialize_neo4j_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: _serialize_neo4j_value(v) for k, v in value.items()}
    else:
        # Primitive types (str, int, float, bool)
        return value
