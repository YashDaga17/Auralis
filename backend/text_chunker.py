"""
Text chunking utilities with token limits.
Uses tiktoken for accurate token counting.

Requirements: 22.5
"""
import re
import tiktoken
from typing import List


class TextChunker:
    """Chunks text into segments with token limits."""
    
    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50):
        """
        Initialize text chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of overlapping tokens between chunks
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        # Use cl100k_base encoding (used by GPT-4, GPT-3.5-turbo)
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text with token limits and overlap.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        # Encode text to tokens
        tokens = self.encoding.encode(text)
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(tokens):
            # Get chunk of max_tokens
            end_idx = start_idx + self.max_tokens
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move start index forward, accounting for overlap
            start_idx = end_idx - self.overlap_tokens
            
            # Prevent infinite loop if overlap >= max_tokens
            if start_idx <= end_idx - self.max_tokens:
                start_idx = end_idx
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Chunk text by paragraph boundaries while respecting token limits.
        Provides better semantic coherence than arbitrary token splits.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        # Split by double newlines (paragraph boundaries)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Count tokens in this paragraph
            para_tokens = len(self.encoding.encode(paragraph))
            
            # If single paragraph exceeds max_tokens, split it
            if para_tokens > self.max_tokens:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split large paragraph using token-based chunking
                para_chunks = self.chunk_text(paragraph)
                chunks.extend(para_chunks)
                continue
            
            # Check if adding this paragraph would exceed limit
            if current_tokens + para_tokens > self.max_tokens:
                # Save current chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                
                # Start new chunk with overlap from previous
                if chunks and self.overlap_tokens > 0:
                    # Get last few paragraphs for overlap
                    overlap_text = current_chunk[-1] if current_chunk else ""
                    overlap_tokens = len(self.encoding.encode(overlap_text))
                    
                    if overlap_tokens <= self.overlap_tokens:
                        current_chunk = [overlap_text, paragraph]
                        current_tokens = overlap_tokens + para_tokens
                    else:
                        current_chunk = [paragraph]
                        current_tokens = para_tokens
                else:
                    current_chunk = [paragraph]
                    current_tokens = para_tokens
            else:
                # Add paragraph to current chunk
                current_chunk.append(paragraph)
                current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Input text
            
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))


# Global chunker instance with default settings
default_chunker = TextChunker(max_tokens=512, overlap_tokens=50)
