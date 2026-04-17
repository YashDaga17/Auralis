"""
Complete knowledge upload pipeline orchestrating parse -> chunk -> embed -> store flow.
Supports async processing with job tracking.

Requirements: 22.3, 22.4, 24.4, 24.5
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

from file_parsers import parser_registry
from text_chunker import default_chunker
from embedding_generator import default_embedding_generator
from qdrant_storage import default_qdrant_storage


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UploadJob:
    """Represents an upload job with tracking information."""
    job_id: str
    status: JobStatus
    filename: str
    collection_name: str
    company_id: str
    document_id: str
    created_at: datetime
    updated_at: datetime
    progress: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "filename": self.filename,
            "collection_name": self.collection_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "error_message": self.error_message
        }


class KnowledgeUploadPipeline:
    """Orchestrates the complete knowledge upload workflow."""
    
    def __init__(self):
        """Initialize pipeline with default components."""
        self.parser_registry = parser_registry
        self.chunker = default_chunker
        self.embedding_generator = default_embedding_generator
        self.qdrant_storage = default_qdrant_storage
        
        # In-memory job tracking (in production, use Redis or database)
        self.jobs: Dict[str, UploadJob] = {}
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        collection_name: str,
        company_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start async document upload process.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            collection_name: Target Qdrant collection
            company_id: Company identifier for multi-tenant isolation
            metadata: Optional metadata to attach to chunks
            
        Returns:
            job_id for tracking upload progress
        """
        # Generate unique IDs
        job_id = str(uuid.uuid4())
        document_id = str(uuid.uuid4())
        
        # Create job record
        job = UploadJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            filename=filename,
            collection_name=collection_name,
            company_id=company_id,
            document_id=document_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            progress={
                "chunks": 0,
                "embeddings": 0,
                "stored": 0
            }
        )
        
        self.jobs[job_id] = job
        
        # Start async processing
        asyncio.create_task(
            self._process_upload(
                job_id=job_id,
                file_content=file_content,
                filename=filename,
                collection_name=collection_name,
                company_id=company_id,
                document_id=document_id,
                metadata=metadata
            )
        )
        
        return job_id
    
    async def _process_upload(
        self,
        job_id: str,
        file_content: bytes,
        filename: str,
        collection_name: str,
        company_id: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]]
    ):
        """
        Process document upload asynchronously.
        
        This method runs in the background and updates job status.
        """
        job = self.jobs[job_id]
        
        try:
            # Update status to processing
            job.status = JobStatus.PROCESSING
            job.updated_at = datetime.utcnow()
            
            # Step 1: Parse document
            file_extension = self._get_file_extension(filename)
            parser = self.parser_registry.get_parser(file_extension)
            
            if not parser:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            text = parser.parse(file_content, filename)
            
            # Step 2: Chunk text
            chunks = self.chunker.chunk_by_paragraphs(text)
            job.progress["chunks"] = len(chunks)
            job.updated_at = datetime.utcnow()
            
            # Step 3: Generate embeddings
            embeddings = await self.embedding_generator.generate_embeddings(chunks)
            job.progress["embeddings"] = len(embeddings)
            job.updated_at = datetime.utcnow()
            
            # Step 4: Store in Qdrant
            stored_count = await self.qdrant_storage.store_document_chunks(
                collection_name=collection_name,
                chunks=chunks,
                embeddings=embeddings,
                company_id=company_id,
                document_id=document_id,
                filename=filename,
                metadata=metadata
            )
            
            job.progress["stored"] = stored_count
            job.status = JobStatus.COMPLETED
            job.updated_at = datetime.utcnow()
        
        except Exception as e:
            # Handle failure
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            print(f"Upload job {job_id} failed: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an upload job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status dictionary or None if not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return job.to_dict()
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            return f".{parts[1].lower()}"
        return ""
    
    def list_collections(self) -> list[str]:
        """
        List all available Qdrant collections.
        
        Returns:
            List of collection names
        """
        return self.qdrant_storage.list_collections()
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Collection info dictionary
        """
        return self.qdrant_storage.get_collection_info(collection_name)


# Global pipeline instance
default_knowledge_pipeline = KnowledgeUploadPipeline()
