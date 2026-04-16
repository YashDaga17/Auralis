"""
Graph database API endpoints.
Handles Neo4j schema retrieval and Cypher query execution.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import re

from database import get_db, get_neo4j_session
from auth import get_auth_context, AuthContext

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
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Get the graph schema (ontology) for the authenticated company.
    
    Requirements: 39.4
    
    Note: Full Neo4j integration will be implemented in Task 13-14.
    """
    try:
        # Check if Neo4j is configured
        neo4j_uri = os.getenv("NEO4J_URI")
        if not neo4j_uri:
            return {
                "company_id": auth.company_id,
                "entity_types": [],
                "relationship_types": [],
                "message": "Neo4j not configured. Graph features will be available after Task 13."
            }
        
        # Placeholder for Neo4j schema retrieval
        # This will be implemented in Task 13-14
        return {
            "company_id": auth.company_id,
            "entity_types": [],
            "relationship_types": [],
            "message": "Graph schema retrieval will be implemented in Task 13-14"
        }
        
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


@router.post("/query")
async def execute_cypher_query(
    request: CypherQueryRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Execute a read-only Cypher query against the graph database.
    
    Requirements: 41.7, 41.8
    
    Note: Full Neo4j query execution will be implemented in Task 14.
    """
    # Validate read-only query
    if not is_read_only_cypher(request.query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only read-only Cypher queries are allowed (MATCH, RETURN, WHERE, etc.)"
        )
    
    try:
        # Check if Neo4j is configured
        neo4j_uri = os.getenv("NEO4J_URI")
        if not neo4j_uri:
            return {
                "results": [],
                "execution_time_ms": 0,
                "message": "Neo4j not configured. Graph features will be available after Task 13."
            }
        
        # Placeholder for Neo4j query execution
        # This will be implemented in Task 14
        return {
            "results": [],
            "execution_time_ms": 0,
            "message": "Cypher query execution will be implemented in Task 14",
            "query": request.query
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute Cypher query: {str(e)}"
        )


import os
