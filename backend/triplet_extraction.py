"""
Triplet Extraction Pipeline for Knowledge Graph.
Extracts entities and relationships from document chunks using LLM,
deduplicates entities with fuzzy matching, and inserts into Neo4j.

Requirements: 40.1, 40.2, 40.3, 40.4, 40.5, 40.7, 40.8, 40.9, 39.2, 39.3
"""
import asyncio
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from fuzzywuzzy import fuzz
from neo4j import GraphDatabase
from google import genai
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Triplet:
    """Represents an extracted entity-relationship-entity triplet."""
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    confidence: float


@dataclass
class CompanyOntology:
    """Defines allowed entity and relationship types for a company."""
    entity_types: List[str]
    relationship_types: List[str]


# Default ontology for companies
DEFAULT_ONTOLOGY = CompanyOntology(
    entity_types=[
        "Person",
        "Project",
        "Product",
        "Department",
        "Document",
        "Company",
        "Technology",
        "Location"
    ],
    relationship_types=[
        "MANAGES",
        "OWNS",
        "REPORTS_TO",
        "WORKS_ON",
        "CREATED",
        "USES",
        "LOCATED_IN",
        "PART_OF",
        "COLLABORATES_WITH",
        "DEPENDS_ON"
    ]
)


class TripletExtractionPipeline:
    """
    Extracts triplets from document chunks and populates Neo4j knowledge graph.
    
    Subtask 13.1: Extract triplets using LLM with company ontology
    Subtask 13.3: Deduplicate entities with fuzzy matching
    Subtask 13.5: Insert triplets into Neo4j with MERGE
    """
    
    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize triplet extraction pipeline.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            gemini_api_key: Gemini API key for LLM calls
        """
        # Neo4j connection
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        
        self.neo4j_driver = None
        
        if self.neo4j_uri and self.neo4j_password:
            try:
                self.neo4j_driver = GraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_user, self.neo4j_password),
                    max_connection_pool_size=50,
                    connection_timeout=5.0
                )
            except Exception as e:
                print(f"Warning: Could not connect to Neo4j: {e}")
                self.neo4j_driver = None
        
        # Gemini client for LLM extraction
        api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for triplet extraction")
        
        self.gemini_client = genai.Client(api_key=api_key)
        
        # Company ontologies (in production, load from database)
        self.ontologies: Dict[str, CompanyOntology] = {}
    
    def get_company_ontology(self, company_id: str) -> CompanyOntology:
        """
        Get ontology for a company (entity and relationship types).
        
        Args:
            company_id: Company identifier
            
        Returns:
            CompanyOntology with allowed types
        """
        # In production, load from database per company
        # For now, return default ontology
        if company_id not in self.ontologies:
            self.ontologies[company_id] = DEFAULT_ONTOLOGY
        
        return self.ontologies[company_id]
    
    async def process_document(
        self,
        document_id: str,
        chunks: List[str],
        company_id: str
    ) -> int:
        """
        Process document chunks and extract triplets into knowledge graph.
        
        Args:
            document_id: Unique document identifier
            chunks: List of text chunks from document
            company_id: Company identifier for multi-tenant isolation
            
        Returns:
            Number of triplets inserted
        """
        # Get company ontology
        ontology = self.get_company_ontology(company_id)
        
        # Extract triplets from chunks in parallel (Subtask 13.1)
        all_triplets = await self._extract_triplets_parallel(chunks, ontology, company_id)
        
        if not all_triplets:
            print(f"No triplets extracted from {len(chunks)} chunks")
            return 0
        
        print(f"Extracted {len(all_triplets)} triplets before deduplication")
        
        # Deduplicate entities using fuzzy matching (Subtask 13.3)
        deduplicated_triplets = self._deduplicate_entities(all_triplets)
        
        print(f"After deduplication: {len(deduplicated_triplets)} triplets")
        
        # Insert into Neo4j (Subtask 13.5)
        if self.neo4j_driver:
            inserted_count = await self._insert_triplets_neo4j(
                deduplicated_triplets,
                document_id,
                company_id
            )
            print(f"Inserted {inserted_count} triplets into Neo4j")
        else:
            print("Neo4j not configured, skipping graph insertion")
            inserted_count = len(deduplicated_triplets)
        
        return inserted_count
    
    async def _extract_triplets_parallel(
        self,
        chunks: List[str],
        ontology: CompanyOntology,
        company_id: str
    ) -> List[Triplet]:
        """
        Extract triplets from chunks in parallel using LLM.
        
        Subtask 13.1: Extract triplets from document chunks using LLM
        Requirements: 40.1, 40.2, 40.3, 40.7
        
        Args:
            chunks: Text chunks to process
            ontology: Company ontology with allowed types
            company_id: Company identifier
            
        Returns:
            List of extracted triplets
        """
        # Process chunks in parallel
        tasks = [
            self._extract_triplets_from_chunk(chunk, ontology)
            for chunk in chunks
        ]
        
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and filter out errors
        all_triplets = []
        for result in chunk_results:
            if isinstance(result, list):
                all_triplets.extend(result)
            elif isinstance(result, Exception):
                print(f"Error extracting triplets: {result}")
        
        return all_triplets
    
    async def _extract_triplets_from_chunk(
        self,
        chunk: str,
        ontology: CompanyOntology
    ) -> List[Triplet]:
        """
        Extract triplets from a single chunk using LLM.
        
        Requirements: 40.2, 40.3
        
        Args:
            chunk: Text chunk to process
            ontology: Company ontology
            
        Returns:
            List of extracted triplets
        """
        # Build extraction prompt with ontology constraints
        prompt = f"""Extract entities and relationships from this text.

Allowed entity types: {', '.join(ontology.entity_types)}
Allowed relationship types: {', '.join(ontology.relationship_types)}

Text:
{chunk}

Return a JSON array of triplets in this exact format:
[
  {{
    "subject": "entity name",
    "subject_type": "Person",
    "predicate": "MANAGES",
    "object": "entity name",
    "object_type": "Project",
    "confidence": 0.95
  }}
]

Rules:
- Only extract explicit relationships mentioned in the text
- Use only the allowed entity and relationship types listed above
- Confidence should be between 0.0 and 1.0
- Return empty array [] if no relationships found
- Return ONLY valid JSON, no other text

JSON array:"""
        
        # Retry logic for API rate limits
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                # Call Gemini with low temperature for structured extraction
                response = self.gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config={
                        'temperature': 0.1,
                        'max_output_tokens': 2048
                    }
                )
                
                # Parse JSON response
                response_text = response.text.strip()
                
                # Clean up response (remove markdown code blocks if present)
                if response_text.startswith('```'):
                    # Remove ```json and ``` markers
                    lines = response_text.split('\n')
                    response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                
                triplets_data = json.loads(response_text)
                
                # Convert to Triplet objects
                triplets = []
                for item in triplets_data:
                    try:
                        triplet = Triplet(
                            subject=item['subject'],
                            subject_type=item['subject_type'],
                            predicate=item['predicate'],
                            object=item['object'],
                            object_type=item['object_type'],
                            confidence=float(item.get('confidence', 0.8))
                        )
                        triplets.append(triplet)
                    except (KeyError, ValueError) as e:
                        print(f"Invalid triplet format: {item}, error: {e}")
                
                return triplets
            
            except json.JSONDecodeError as e:
                print(f"Failed to parse LLM JSON response: {e}")
                if 'response_text' in locals():
                    print(f"Response was: {response_text[:200]}")
                return []
            
            except Exception as e:
                error_msg = str(e)
                if '503' in error_msg or 'UNAVAILABLE' in error_msg or 'high demand' in error_msg:
                    if attempt < max_retries - 1:
                        print(f"API rate limit hit, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        print(f"Max retries reached for chunk extraction")
                        return []
                else:
                    print(f"Error extracting triplets from chunk: {e}")
                    return []
        
        return []
    
    def _deduplicate_entities(self, triplets: List[Triplet]) -> List[Triplet]:
        """
        Deduplicate entities using fuzzy string matching.
        
        Subtask 13.3: Implement entity deduplication with fuzzy matching
        Requirements: 40.8
        
        Args:
            triplets: List of triplets with potentially duplicate entities
            
        Returns:
            List of triplets with canonical entity names
        """
        # Build entity map: (entity_name, entity_type) -> canonical_name
        entity_map: Dict[Tuple[str, str], str] = {}
        
        for triplet in triplets:
            # Process subject
            self._map_entity_to_canonical(
                triplet.subject,
                triplet.subject_type,
                entity_map
            )
            
            # Process object
            self._map_entity_to_canonical(
                triplet.object,
                triplet.object_type,
                entity_map
            )
        
        # Replace entity names with canonical versions
        deduplicated = []
        for triplet in triplets:
            subject_key = (triplet.subject, triplet.subject_type)
            object_key = (triplet.object, triplet.object_type)
            
            canonical_subject = entity_map.get(subject_key, triplet.subject)
            canonical_object = entity_map.get(object_key, triplet.object)
            
            deduplicated_triplet = Triplet(
                subject=canonical_subject,
                subject_type=triplet.subject_type,
                predicate=triplet.predicate,
                object=canonical_object,
                object_type=triplet.object_type,
                confidence=triplet.confidence
            )
            deduplicated.append(deduplicated_triplet)
        
        return deduplicated
    
    def _map_entity_to_canonical(
        self,
        entity: str,
        entity_type: str,
        entity_map: Dict[Tuple[str, str], str]
    ):
        """
        Map entity to canonical name using fuzzy matching.
        
        Requirements: 40.8
        
        Args:
            entity: Entity name to map
            entity_type: Entity type
            entity_map: Dictionary to update with mapping
        """
        entity_key = (entity, entity_type)
        
        # Skip if already mapped
        if entity_key in entity_map:
            return
        
        # Find similar existing entities of same type
        canonical = None
        best_similarity = 0
        
        for (existing_entity, existing_type), canonical_name in entity_map.items():
            if existing_type == entity_type:
                # Calculate similarity using multiple methods for better matching
                ratio = fuzz.ratio(entity.lower(), existing_entity.lower())
                partial_ratio = fuzz.partial_ratio(entity.lower(), existing_entity.lower())
                token_sort_ratio = fuzz.token_sort_ratio(entity.lower(), existing_entity.lower())
                
                # Use the maximum similarity score
                similarity = max(ratio, partial_ratio, token_sort_ratio)
                
                # Threshold: 80% similarity to consider same entity (lowered from 85%)
                # This helps match "John Smith" with "J. Smith"
                if similarity > 80 and similarity > best_similarity:
                    canonical = canonical_name
                    best_similarity = similarity
        
        # If no match found, this entity becomes canonical
        if canonical is None:
            canonical = entity
        
        entity_map[entity_key] = canonical
    
    async def _insert_triplets_neo4j(
        self,
        triplets: List[Triplet],
        document_id: str,
        company_id: str
    ) -> int:
        """
        Insert triplets into Neo4j using MERGE to avoid duplicates.
        
        Subtask 13.5: Implement Neo4j triplet insertion with MERGE
        Requirements: 40.4, 40.5, 40.9, 39.2, 39.3
        
        Args:
            triplets: List of triplets to insert
            document_id: Source document identifier
            company_id: Company identifier for tenant isolation
            
        Returns:
            Number of triplets inserted
        """
        inserted_count = 0
        
        # Use async context manager to ensure proper session cleanup
        try:
            with self.neo4j_driver.session() as session:
                for triplet in triplets:
                    try:
                        # Sanitize node labels (remove spaces and special chars)
                        subject_type = triplet.subject_type.replace(" ", "_").replace("-", "_")
                        object_type = triplet.object_type.replace(" ", "_").replace("-", "_")
                        predicate = triplet.predicate.replace(" ", "_").replace("-", "_")
                        
                        # Create Cypher MERGE statement
                        # MERGE ensures nodes and relationships are created only if they don't exist
                        cypher = f"""
                        MERGE (s:{subject_type} {{name: $subject, company_id: $company_id}})
                        ON CREATE SET s.created_at = datetime()
                        MERGE (o:{object_type} {{name: $object, company_id: $company_id}})
                        ON CREATE SET o.created_at = datetime()
                        MERGE (s)-[r:{predicate}]->(o)
                        ON CREATE SET 
                            r.created_at = datetime(),
                            r.source_document_id = $document_id,
                            r.confidence = $confidence,
                            r.company_id = $company_id
                        ON MATCH SET
                            r.updated_at = datetime(),
                            r.confidence = CASE 
                                WHEN $confidence > r.confidence THEN $confidence 
                                ELSE r.confidence 
                            END
                        RETURN r
                        """
                        
                        # Execute with parameters
                        result = session.run(cypher, {
                            'subject': triplet.subject,
                            'object': triplet.object,
                            'company_id': company_id,
                            'document_id': document_id,
                            'confidence': triplet.confidence
                        })
                        
                        # Consume result to ensure execution
                        result.consume()
                        inserted_count += 1
                    
                    except Exception as e:
                        print(f"Error inserting triplet {triplet}: {e}")
                        continue
        
        except Exception as e:
            print(f"Neo4j session error: {e}")
        
        return inserted_count
    
    def close(self):
        """Close Neo4j driver connection."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global pipeline instance
default_triplet_pipeline = None

def get_triplet_pipeline() -> TripletExtractionPipeline:
    """Get or create global triplet extraction pipeline instance."""
    global default_triplet_pipeline
    
    if default_triplet_pipeline is None:
        default_triplet_pipeline = TripletExtractionPipeline()
    
    return default_triplet_pipeline
