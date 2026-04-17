"""
Workflow management API endpoints.
Handles workflow creation, retrieval, versioning, and testing.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 5.2, 12.1, 12.2, 12.3, 12.4, 12.5, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 15.5
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid
import time
import asyncio

from database import get_db
from auth import get_auth_context, AuthContext, verify_tenant_access
from models import Agent, WorkflowVersion
from workflow_schema import WorkflowJSON
from workflow_validator import validate_workflow
from workflow_execution import WorkflowExecutionEngine

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
    
    Validates workflow JSON schema before storage and creates workflow version record.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    # Validate workflow JSON schema (Requirement 3.1, 3.4)
    try:
        workflow = WorkflowJSON(**request.workflow_json)
        is_valid, errors = validate_workflow(workflow)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Workflow validation failed",
                    "errors": errors
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid workflow JSON structure",
                "error": str(e)
            }
        )
    
    # Check if agent already exists
    existing_agent = db.query(Agent).filter(Agent.agent_id == request.agent_id).first()
    
    if existing_agent:
        # Verify tenant access (Requirement 15.5)
        verify_tenant_access(auth, str(existing_agent.company_id))
        
        # Update existing agent (Requirement 3.5)
        existing_agent.workflow_json = request.workflow_json
        existing_agent.updated_at = datetime.utcnow()
        
        # Create new version (Requirement 3.6)
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
        # Create new agent (Requirement 3.5)
        new_agent = Agent(
            agent_id=request.agent_id,
            company_id=uuid.UUID(auth.company_id),
            workflow_json=request.workflow_json
        )
        db.add(new_agent)
        db.flush()  # Get the agent_id before creating version
        
        # Create initial version (Requirement 3.6)
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


class TestWorkflowRequest(BaseModel):
    """Request model for testing a workflow."""
    workflow_json: dict
    test_input: str


class NodeExecutionLog(BaseModel):
    """Execution log for a single node."""
    node_id: str
    node_type: str
    node_label: str
    start_time: float
    end_time: float
    duration_ms: int
    output: str
    error: Optional[str] = None


class TestWorkflowResponse(BaseModel):
    """Response model for workflow test execution."""
    status: str
    final_output: str
    total_duration_ms: int
    node_logs: List[NodeExecutionLog]


@router.post("/test")
async def test_workflow(
    request: TestWorkflowRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Test a workflow without saving it to the database.
    
    Executes the workflow with test input and returns execution logs with node timings.
    
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
    """
    # Validate workflow JSON schema (Requirement 14.2)
    try:
        workflow = WorkflowJSON(**request.workflow_json)
        is_valid, errors = validate_workflow(workflow)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Workflow validation failed",
                    "errors": errors
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid workflow JSON structure",
                "error": str(e)
            }
        )
    
    # Build mock Vapi payload for testing (Requirement 14.3)
    vapi_payload = {
        "messages": [
            {
                "role": "user",
                "content": request.test_input
            }
        ],
        "metadata": {
            "company_id": auth.company_id,
            "user_id": auth.user_id
        }
    }
    
    # Track execution timing
    start_time = time.time()
    node_logs = []
    
    # Create custom execution engine that logs node executions
    class LoggingWorkflowExecutionEngine(WorkflowExecutionEngine):
        """Extended execution engine that captures node execution logs."""
        
        def __init__(self, workflow_json: dict, vapi_payload: dict):
            super().__init__(workflow_json, vapi_payload)
            self.node_logs = []
        
        async def _execute_node(self, node_id: str) -> str:
            """Override to capture execution timing and logs."""
            node = self.nodes_by_id.get(node_id)
            if not node:
                return ""
            
            node_start = time.time()
            error = None
            output = ""
            
            try:
                output = await super()._execute_node(node_id)
            except Exception as e:
                error = str(e)
                output = self.context.get(f"{node_id}_output", "")
            
            node_end = time.time()
            
            # Create execution log (Requirement 14.4)
            log = {
                "node_id": node_id,
                "node_type": node.type.value,
                "node_label": node.data.label,
                "start_time": node_start,
                "end_time": node_end,
                "duration_ms": int((node_end - node_start) * 1000),
                "output": output[:500] if output else "",  # Truncate long outputs
                "error": error
            }
            self.node_logs.append(log)
            
            if error:
                raise Exception(error)
            
            return output
    
    # Execute workflow without saving (Requirement 14.2, 14.3)
    try:
        engine = LoggingWorkflowExecutionEngine(request.workflow_json, vapi_payload)
        final_output = await engine.execute()
        
        end_time = time.time()
        total_duration_ms = int((end_time - start_time) * 1000)
        
        # Return execution logs with node timings (Requirement 14.4, 14.5)
        return {
            "status": "success",
            "final_output": final_output,
            "total_duration_ms": total_duration_ms,
            "node_logs": engine.node_logs
        }
        
    except Exception as e:
        end_time = time.time()
        total_duration_ms = int((end_time - start_time) * 1000)
        
        # Return error with partial logs (Requirement 14.6)
        return {
            "status": "error",
            "final_output": "",
            "total_duration_ms": total_duration_ms,
            "node_logs": engine.node_logs if 'engine' in locals() else [],
            "error": str(e)
        }
