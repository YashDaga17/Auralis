"""
Batch embedding generation with rate limiting.
Uses Gemini text-embedding-004 model.

Requirements: 22.6
"""
import asyncio
import os
from typing import List
import google.generativeai as genai


class EmbeddingGenerator:
    """Generates embeddings with rate limiting and batching."""
    
    def __init__(self, batch_size: int = 100, delay_seconds: float = 1.0):
        """
        Initialize embedding generator.
        
        Args:
            batch_size: Number of texts to process in each batch
            delay_seconds: Delay between batches for rate limiting
        """
        self.batch_size = batch_size
        self.delay_seconds = delay_seconds
        
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model = "text-embedding-004"
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for list of texts with batching and rate limiting.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            # Generate embeddings for batch
            batch_embeddings = await self._generate_batch(batch)
            all_embeddings.extend(batch_embeddings)
            
            # Rate limiting delay (except for last batch)
            if i + self.batch_size < len(texts):
                await asyncio.sleep(self.delay_seconds)
        
        return all_embeddings
    
    async def _generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a single batch.
        
        Args:
            texts: Batch of text strings
            
        Returns:
            List of embedding vectors
        """
        try:
            # Gemini embed_content can handle multiple texts
            result = genai.embed_content(
                model=self.model,
                content=texts,
                task_type="retrieval_document"
            )
            
            # Extract embedding values
            if isinstance(result['embedding'], list) and isinstance(result['embedding'][0], list):
                # Multiple embeddings returned
                return result['embedding']
            else:
                # Single embedding returned (wrap in list)
                return [result['embedding']]
        
        except Exception as e:
            # Log error and return zero vectors as fallback
            print(f"Error generating embeddings: {e}")
            # Return zero vectors with dimension 768 (text-embedding-004 dimension)
            return [[0.0] * 768 for _ in texts]
    
    async def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]


# Global embedding generator instance
default_embedding_generator = EmbeddingGenerator(batch_size=100, delay_seconds=1.0)
