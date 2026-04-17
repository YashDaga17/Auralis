"""
API routes for knowledge management.
Handles file uploads, job tracking, and collection management.

Requirements: 22.3, 22.4, 24.4, 24.5, 24.7
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from knowledge_upload_pipeline import default_knowledge_pipeline


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    company_id: str = Form(...)
):
    """
    Upload a document for knowledge extraction.
    
    Args:
        file: Uploaded file (PDF, DOCX, TXT, CSV, Markdown)
        collection_name: Target Qdrant collection name
        company_id: Company identifier for multi-tenant isolation
        
    Returns:
        job_id for tracking upload progress
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Start async upload
        job_id = await default_knowledge_pipeline.upload_document(
            file_content=file_content,
            filename=file.filename,
            collection_name=collection_name,
            company_id=company_id
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Upload started for {file.filename}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/{job_id}/status")
async def get_upload_status(job_id: str):
    """
    Get status of an upload job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job status with progress metrics
    """
    job_status = default_knowledge_pipeline.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return job_status


@router.get("/collections")
async def list_collections(company_id: str = None):
    """
    List all Qdrant collections for a company.
    
    Args:
        company_id: Optional company filter for multi-tenant isolation
    
    Returns:
        List of collection names with metadata (document count, chunk count, storage size)
        
    Requirements: 24.7
    """
    try:
        collection_names = default_knowledge_pipeline.list_collections()
        
        # Get info for each collection
        collections = []
        for name in collection_names:
            # Filter by company_id if provided (collections are named {company_id}_{collection_name})
            if company_id and not name.startswith(f"{company_id}_"):
                continue
                
            info = default_knowledge_pipeline.get_collection_info(name)
            if info:
                collections.append(info)
        
        return {
            "success": True,
            "collections": collections,
            "total": len(collections)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_name}")
async def get_collection_info(collection_name: str):
    """
    Get detailed information about a specific collection.
    
    Args:
        collection_name: Collection name
        
    Returns:
        Collection metadata (document count, chunk count, storage size)
    """
    try:
        info = default_knowledge_pipeline.get_collection_info(collection_name)
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")
        
        return {
            "success": True,
            "collection": info
        }
    
    except HTTPException:
        raise
    except Exception as e:
        # Check if it's a "not found" error from Qdrant
        if "doesn't exist" in str(e).lower() or "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")
        raise HTTPException(status_code=500, detail=str(e))
