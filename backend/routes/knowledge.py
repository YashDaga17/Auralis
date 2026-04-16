"""
Knowledge management API endpoints.
Handles file uploads, collection management, and document processing.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid

from database import get_db
from auth import get_auth_context, AuthContext
from qdrant_client import QdrantClient
import os

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# Initialize Qdrant client
q_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)


class UploadJobResponse(BaseModel):
    """Response model for file upload job."""
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    progress: dict


class CollectionInfo(BaseModel):
    """Information about a Qdrant collection."""
    collection_name: str
    vectors_count: int
    indexed_vectors_count: int


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Upload a knowledge file for processing.
    
    Requirements: 22.3, 22.4, 24.4
    
    Note: Full knowledge upload pipeline will be implemented in Task 12.
    """
    # Validate file type
    allowed_extensions = [".pdf", ".docx", ".txt", ".csv", ".json", ".md"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_ext}' not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Placeholder for knowledge upload pipeline
    # This will be implemented in Task 12
    return {
        "job_id": job_id,
        "status": "not_implemented",
        "message": "Knowledge upload pipeline will be implemented in Task 12",
        "filename": file.filename,
        "collection_name": collection_name,
        "company_id": auth.company_id
    }


@router.get("/upload/{job_id}/status")
async def get_upload_status(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Get the status of a knowledge upload job.
    
    Requirements: 24.5
    
    Note: Job tracking will be implemented in Task 12.
    """
    return {
        "job_id": job_id,
        "status": "not_implemented",
        "message": "Job tracking will be implemented in Task 12",
        "progress": {
            "chunks_processed": 0,
            "embeddings_generated": 0,
            "triplets_extracted": 0
        }
    }


@router.get("/collections")
async def list_collections(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    List all Qdrant collections for the authenticated company.
    
    Requirements: 24.7
    """
    try:
        # Get all collections from Qdrant
        collections_response = q_client.get_collections()
        collections = collections_response.collections
        
        # Filter collections by company_id prefix
        # Convention: collection names should be prefixed with company_id
        company_collections = []
        for collection in collections:
            collection_name = collection.name
            
            # Get collection info
            try:
                collection_info = q_client.get_collection(collection_name)
                # Handle both old and new Qdrant API
                vectors_count = getattr(collection_info, 'vectors_count', None) or \
                               getattr(collection_info, 'points_count', 0)
                indexed_count = getattr(collection_info, 'indexed_vectors_count', None) or \
                               getattr(collection_info, 'indexed_vectors_count', 0)
                
                company_collections.append({
                    "collection_name": collection_name,
                    "vectors_count": vectors_count,
                    "indexed_vectors_count": indexed_count
                })
            except Exception as e:
                print(f"Error getting collection info for {collection_name}: {e}")
                continue
        
        return {
            "company_id": auth.company_id,
            "collections": company_collections,
            "total_collections": len(company_collections)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collections: {str(e)}"
        )
