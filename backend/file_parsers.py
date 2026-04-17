"""
File parsers for knowledge upload pipeline.
Uses Mistral OCR for complex documents (PDF, DOCX) and direct parsing for simple text files.

Requirements: 22.2
"""
import io
import os
import base64
from abc import ABC, abstractmethod
from typing import Optional
import csv
from mistralai.client import Mistral


class FileParser(ABC):
    """Abstract base class for file parsers."""
    
    @abstractmethod
    def parse(self, file_content: bytes, filename: str) -> str:
        """
        Parse file content and extract text.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename for context
            
        Returns:
            Extracted text content
        """
        pass


class MistralOCRParser(FileParser):
    """Parser for complex documents using Mistral OCR/Vision API."""
    
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is required")
        self.client = Mistral(api_key=api_key)
    
    def parse(self, file_content: bytes, filename: str) -> str:
        """Extract text from document using Mistral OCR."""
        # Encode file content to base64
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Determine MIME type from filename
        mime_type = self._get_mime_type(filename)
        
        # Create data URL
        data_url = f"data:{mime_type};base64,{base64_content}"
        
        # Call Mistral vision API
        try:
            response = self.client.chat.complete(
                model="pixtral-12b-2409",  # Mistral's vision model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text content from this document. Preserve structure, headings, and paragraphs. Return only the extracted text without any additional commentary."
                            },
                            {
                                "type": "image_url",
                                "image_url": data_url
                            }
                        ]
                    }
                ]
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Mistral OCR failed for {filename}: {str(e)}")
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename extension."""
        ext = filename.lower().split('.')[-1]
        mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
        }
        return mime_types.get(ext, 'application/octet-stream')


class PDFParser(FileParser):
    """Parser for PDF files using Mistral OCR."""
    
    def __init__(self):
        self.mistral_parser = MistralOCRParser()
    
    def parse(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF using Mistral OCR."""
        return self.mistral_parser.parse(file_content, filename)


class DOCXParser(FileParser):
    """Parser for DOCX files using Mistral OCR."""
    
    def __init__(self):
        self.mistral_parser = MistralOCRParser()
    
    def parse(self, file_content: bytes, filename: str) -> str:
        """Extract text from DOCX using Mistral OCR."""
        return self.mistral_parser.parse(file_content, filename)


class TXTParser(FileParser):
    """Parser for plain text files."""
    
    def parse(self, file_content: bytes, filename: str) -> str:
        """Extract text from TXT file."""
        # Try UTF-8 first, fall back to latin-1
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            return file_content.decode('latin-1', errors='ignore')


class CSVParser(FileParser):
    """Parser for CSV files."""
    
    def parse(self, file_content: bytes, filename: str) -> str:
        """Extract text from CSV file, converting to readable format."""
        # Decode bytes to string
        try:
            text = file_content.decode('utf-8')
        except UnicodeDecodeError:
            text = file_content.decode('latin-1', errors='ignore')
        
        # Parse CSV
        csv_file = io.StringIO(text)
        reader = csv.reader(csv_file)
        
        rows = []
        for row in reader:
            # Join row cells with tabs for readability
            rows.append("\t".join(row))
        
        return "\n".join(rows)


class MarkdownParser(FileParser):
    """Parser for Markdown files."""
    
    def parse(self, file_content: bytes, filename: str) -> str:
        """Extract text from Markdown file."""
        # Markdown is plain text, just decode
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            return file_content.decode('latin-1', errors='ignore')


class ParserRegistry:
    """Registry for file parsers by extension."""
    
    def __init__(self):
        # Lazy initialization - parsers created on first access
        self._parsers = None
    
    def _initialize_parsers(self):
        """Initialize parsers lazily to allow environment variables to be loaded first."""
        if self._parsers is None:
            # Use Mistral OCR for complex documents, direct parsing for simple text
            self._parsers = {
                '.pdf': PDFParser(),
                '.docx': DOCXParser(),
                '.txt': TXTParser(),
                '.csv': CSVParser(),
                '.md': MarkdownParser(),
                '.markdown': MarkdownParser(),
                '.json': TXTParser(),  # JSON is text-based
            }
    
    def get_parser(self, file_extension: str) -> Optional[FileParser]:
        """
        Get parser for file extension.
        
        Args:
            file_extension: File extension (e.g., '.pdf', '.docx')
            
        Returns:
            FileParser instance or None if not supported
        """
        self._initialize_parsers()
        return self._parsers.get(file_extension.lower())
    
    def is_supported(self, file_extension: str) -> bool:
        """Check if file extension is supported."""
        self._initialize_parsers()
        return file_extension.lower() in self._parsers
    
    def supported_extensions(self) -> list[str]:
        """Get list of supported file extensions."""
        self._initialize_parsers()
        return list(self._parsers.keys())


# Global parser registry instance
parser_registry = ParserRegistry()

