"""
Qdrant storage for document chunks with multi-tenant isolation.

Requirements: 22.7
"""
import os
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class QdrantStorage:
    """Manages Qdrant collections and document storage."""
    
    def __init__(self):
        """Initialize Qdrant client."""
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url or not qdrant_api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY environment variables are required")
        
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )
        
        # text-embedding-004 produces 768-dimensional vectors
        self.vector_size = 768
    
    def create_or_get_collection(self, collection_name: str) -> bool:
        """
        Create collection if it doesn't exist, or get existing collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            True if collection was created, False if it already existed
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if collection_name in collection_names:
                return False
            
            # Create new collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            return True
        
        except Exception as e:
            print(f"Error creating/getting collection {collection_name}: {e}")
            raise
    
    async def store_document_chunks(
        self,
        collection_name: str,
        chunks: List[str],
        embeddings: List[List[float]],
        company_id: str,
        document_id: str,
        filename: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """
        Store document chunks with embeddings in Qdrant.
        
        Args:
            collection_name: Target collection name
            chunks: List of text chunks
            embeddings: List of embedding vectors (same length as chunks)
            company_id: Company identifier for multi-tenant isolation
            document_id: Unique document identifier
            filename: Original filename
            metadata: Additional metadata to store with each chunk
            
        Returns:
            Number of chunks stored
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have same length")
        
        # Ensure collection exists
        self.create_or_get_collection(collection_name)
        
        # Create points for batch upsert
        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            
            # Build payload with required fields
            payload = {
                "text": chunk,
                "company_id": company_id,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": idx,
                "total_chunks": len(chunks)
            }
            
            # Add optional metadata
            if metadata:
                payload.update(metadata)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            points.append(point)
        
        # Batch upsert to Qdrant
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            return len(points)
        
        except Exception as e:
            print(f"Error upserting points to {collection_name}: {e}")
            raise
    
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        Delete all chunks for a document.
        
        Args:
            collection_name: Collection name
            document_id: Document identifier
            
        Returns:
            True if deletion succeeded
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            return True
        
        except Exception as e:
            print(f"Error deleting document {document_id}: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Dictionary with collection info (points_count, vector_size, storage_size, etc.)
        """
        try:
            collection_info = self.client.get_collection(collection_name)
            
            # Calculate approximate storage size
            # Each point has: vector (768 floats * 4 bytes) + payload (estimate ~1KB)
            points_count = collection_info.points_count
            vector_size_bytes = collection_info.config.params.vectors.size * 4  # 4 bytes per float
            estimated_payload_size = 1024  # 1KB estimate per payload
            total_size_bytes = points_count * (vector_size_bytes + estimated_payload_size)
            
            # Convert to human-readable format
            if total_size_bytes < 1024:
                storage_size = f"{total_size_bytes} B"
            elif total_size_bytes < 1024 * 1024:
                storage_size = f"{total_size_bytes / 1024:.2f} KB"
            elif total_size_bytes < 1024 * 1024 * 1024:
                storage_size = f"{total_size_bytes / (1024 * 1024):.2f} MB"
            else:
                storage_size = f"{total_size_bytes / (1024 * 1024 * 1024):.2f} GB"
            
            return {
                "name": collection_name,
                "points_count": points_count,
                "chunk_count": points_count,  # Each point is a chunk
                "document_count": self._estimate_document_count(collection_name),
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance.name,
                "storage_size": storage_size,
                "storage_size_bytes": total_size_bytes
            }
        
        except Exception as e:
            print(f"Error getting collection info for {collection_name}: {e}")
            return {}
    
    def _estimate_document_count(self, collection_name: str) -> int:
        """
        Estimate number of unique documents in a collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Estimated document count
        """
        try:
            # Scroll through points and count unique document_ids
            # For large collections, this is an estimate based on sampling
            from qdrant_client.models import ScrollRequest
            
            scroll_result = self.client.scroll(
                collection_name=collection_name,
                limit=1000,  # Sample first 1000 points
                with_payload=True,
                with_vectors=False
            )
            
            unique_docs = set()
            for point in scroll_result[0]:
                doc_id = point.payload.get("document_id")
                if doc_id:
                    unique_docs.add(doc_id)
            
            return len(unique_docs)
        
        except Exception as e:
            print(f"Error estimating document count: {e}")
            return 0
    
    def list_collections(self) -> List[str]:
        """
        List all collection names.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections().collections
            return [c.name for c in collections]
        
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []


# Global Qdrant storage instance
default_qdrant_storage = QdrantStorage()
