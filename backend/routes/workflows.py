"""
Workflow management API endpoints.
Handles workflow creation, retrieval, versioning, and testing.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from database import get_db
from auth import get_auth_context, AuthContext, verify_tenant_access
from models import Agent, WorkflowVersion

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowCreateRequest(BaseModel):
    """Request model for creating a workflow."""
    agent_id: str
    workflow_json: dict
    workflow_name: Optional[str] = None
    description: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Response model for workflow data."""
    agent_id: str
    company_id: str
    workflow_json: dict
    current_version_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class WorkflowVersionResponse(BaseModel):
    """Response model for workflow version."""
    version_id: str
    agent_id: str
    workflow_json: dict
    created_by: Optional[str]
    created_at: datetime


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Create or update a workflow for an agent.
    
    Requirements: 3.3, 3.4, 3.5, 3.6
    """
    # Check if agent already exists
    existing_agent = db.query(Agent).filter(Agent.agent_id == request.agent_id).first()
    
    if existing_agent:
        # Verify tenant access
        verify_tenant_access(auth, str(existing_agent.company_id))
        
        # Update existing agent
        existing_agent.workflow_json = request.workflow_json
        existing_agent.updated_at = datetime.utcnow()
        
        # Create new version
        new_version = WorkflowVersion(
            version_id=uuid.uuid4(),
            agent_id=request.agent_id,
            workflow_json=request.workflow_json,
            created_by=auth.user_id
        )
        db.add(new_version)
        
        # Update current version pointer
        existing_agent.current_version_id = new_version.version_id
        
        db.commit()
        db.refresh(existing_agent)
        db.refresh(new_version)
        
        return {
            "message": "Workflow updated successfully",
            "agent_id": existing_agent.agent_id,
            "version_id": str(new_version.version_id)
        }
    else:
        # Create new agent
        new_agent = Agent(
            agent_id=request.agent_id,
            company_id=uuid.UUID(auth.company_id),
            workflow_json=request.workflow_json
        )
        db.add(new_agent)
        db.flush()  # Get the agent_id before creating version
        
        # Create initial version
        initial_version = WorkflowVersion(
            version_id=uuid.uuid4(),
            agent_id=new_agent.agent_id,
            workflow_json=request.workflow_json,
            created_by=auth.user_id
        )
        db.add(initial_version)
        
        # Set current version
        new_agent.current_version_id = initial_version.version_id
        
        db.commit()
        db.refresh(new_agent)
        db.refresh(initial_version)
        
        return {
            "message": "Workflow created successfully",
            "agent_id": new_agent.agent_id,
            "version_id": str(initial_version.version_id)
        }


@router.get("/{agent_id}")
async def get_workflow(
    agent_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Retrieve workflow configuration for an agent.
    
    Requirements: 5.2, 15.5
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found"
        )
    
    # Verify tenant access
    verify_tenant_access(auth, str(agent.company_id))
    
    return {
        "agent_id": agent.agent_id,
        "company_id": str(agent.company_id),
        "workflow_json": agent.workflow_json,
        "current_version_id": str(agent.current_version_id) if agent.current_version_id else None,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at
    }


@router.get("/{agent_id}/versions")
async def get_workflow_versions(
    agent_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    List all versions of a workflow.
    
    Requirements: 12.1, 12.2, 12.3, 12.4
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found"
        )
    
    # Verify tenant access
    verify_tenant_access(auth, str(agent.company_id))
    
    versions = db.query(WorkflowVersion).filter(
        WorkflowVersion.agent_id == agent_id
    ).order_by(WorkflowVersion.created_at.desc()).all()
    
    return {
        "agent_id": agent_id,
        "versions": [
            {
                "version_id": str(v.version_id),
                "created_by": v.created_by,
                "created_at": v.created_at,
                "is_current": v.version_id == agent.current_version_id
            }
            for v in versions
        ]
    }


@router.post("/test")
async def test_workflow(
    workflow_json: dict,
    test_input: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Test a workflow without saving it to the database.
    
    Requirements: 14.1, 14.2, 14.3, 14.4
    
    Note: Full execution engine implementation will be added in later tasks.
    """
    # Placeholder for workflow execution engine
    # This will be implemented in Task 4
    return {
        "status": "not_implemented",
        "message": "Workflow execution engine will be implemented in Task 4",
        "workflow_json": workflow_json,
        "test_input": test_input
    }
