"""
Node Executor Registry and Base Classes for dynamic workflow node execution.

This module provides the abstract base class for all node executors and a registry
system for dynamic node type registration and lookup. It also implements error
handling and fallback logic for graceful degradation when nodes fail.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 9.1, 9.2, 9.3, 9.4, 9.5
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
import logging
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class NodeExecutionError(Exception):
    """Exception raised when a node execution fails."""
    
    def __init__(self, node_id: str, error_type: str, error_message: str):
        self.node_id = node_id
        self.error_type = error_type
        self.error_message = error_message
        super().__init__(f"Node {node_id} failed: {error_type} - {error_message}")


class NodeExecutor(ABC):
    """
    Abstract base class for all node executors.
    
    Each node type (RAG, LLM, Tool, Action, Decision, Graph Query) must implement
    this interface to be executable by the WorkflowExecutionEngine.
    
    Requirements: 17.1, 17.2, 17.3
    """
    
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute the node with the given configuration and context.
        
        Args:
            config: Node-specific configuration dictionary with resolved context variables
            context: Runtime context dictionary containing outputs from previous nodes
            session: Session context containing user information, conversation history,
                    and extracted entities
        
        Returns:
            String output to be stored in the runtime context as {node_id}_output
        
        Raises:
            NodeExecutionError: If the node execution fails
            
        Requirements: 17.2, 17.3
        """
        pass


class NodeExecutorRegistry:
    """
    Registry for mapping node types to executor classes.
    
    Provides a plugin architecture where new node types can be registered
    dynamically without modifying core execution logic.
    
    Requirements: 17.4, 17.5
    """
    
    def __init__(self):
        """Initialize the registry with an empty executor mapping."""
        self._executors: Dict[str, Type[NodeExecutor]] = {}
        logger.info("NodeExecutorRegistry initialized")
    
    def register(self, node_type: str, executor_class: Type[NodeExecutor]) -> None:
        """
        Register a node executor class for a specific node type.
        
        Args:
            node_type: The node type identifier (e.g., 'rag', 'llm', 'tool')
            executor_class: The executor class that implements NodeExecutor
        
        Raises:
            ValueError: If the executor_class does not inherit from NodeExecutor
            
        Requirement: 17.4
        """
        if not issubclass(executor_class, NodeExecutor):
            raise ValueError(
                f"Executor class {executor_class.__name__} must inherit from NodeExecutor"
            )
        
        self._executors[node_type] = executor_class
        logger.info(f"Registered executor for node type '{node_type}': {executor_class.__name__}")
    
    def get_executor(self, node_type: str) -> Optional[Type[NodeExecutor]]:
        """
        Look up the executor class for a given node type.
        
        Args:
            node_type: The node type identifier
        
        Returns:
            The executor class for the node type, or None if not registered
            
        Requirement: 17.5
        """
        executor_class = self._executors.get(node_type)
        
        if executor_class is None:
            logger.warning(f"No executor registered for node type '{node_type}'")
        
        return executor_class
    
    def list_registered_types(self) -> list[str]:
        """
        Get a list of all registered node types.
        
        Returns:
            List of registered node type identifiers
        """
        return list(self._executors.keys())


class FallbackHandler:
    """
    Handles node execution failures and fallback logic.
    
    When a node fails, this handler checks for connected fallback nodes
    and executes them with error details passed as context variables.
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    
    def __init__(self, adjacency_list: Dict[str, list[str]], nodes_by_id: Dict[str, Any]):
        """
        Initialize the fallback handler.
        
        Args:
            adjacency_list: Dictionary mapping node_id to list of connected node_ids
            nodes_by_id: Dictionary mapping node_id to node configuration
        """
        self.adjacency_list = adjacency_list
        self.nodes_by_id = nodes_by_id
    
    def find_fallback_node(self, failed_node_id: str) -> Optional[str]:
        """
        Find the fallback node connected to a failed node.
        
        Args:
            failed_node_id: The ID of the node that failed
        
        Returns:
            The ID of the connected fallback node, or None if no fallback exists
            
        Requirement: 9.2
        """
        # Get nodes connected to the failed node
        connected_nodes = self.adjacency_list.get(failed_node_id, [])
        
        # Look for a node with type 'fallback'
        for node_id in connected_nodes:
            node = self.nodes_by_id.get(node_id)
            if node and node.type == 'fallback':
                logger.info(f"Found fallback node '{node_id}' for failed node '{failed_node_id}'")
                return node_id
        
        logger.info(f"No fallback node found for failed node '{failed_node_id}'")
        return None
    
    def prepare_error_context(
        self,
        failed_node_id: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare error details to pass to the fallback node.
        
        Args:
            failed_node_id: The ID of the node that failed
            error: The exception that was raised
            context: The current runtime context
        
        Returns:
            Updated context dictionary with error details
            
        Requirement: 9.3
        """
        # Extract error information
        error_type = type(error).__name__
        error_message = str(error)
        
        # Add error details to context
        error_context = context.copy()
        error_context[f"{failed_node_id}_error_type"] = error_type
        error_context[f"{failed_node_id}_error_message"] = error_message
        error_context[f"{failed_node_id}_error_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        logger.debug(
            f"Prepared error context for fallback: "
            f"node={failed_node_id}, type={error_type}, message={error_message}"
        )
        
        return error_context
    
    def log_failure(
        self,
        node_id: str,
        error: Exception,
        has_fallback: bool
    ) -> None:
        """
        Log node failure with detailed information for debugging.
        
        Args:
            node_id: The ID of the node that failed
            error: The exception that was raised
            has_fallback: Whether a fallback node was found
            
        Requirement: 9.5
        """
        error_type = type(error).__name__
        error_message = str(error)
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_message = (
            f"Node execution failed - "
            f"node_id={node_id}, "
            f"error_type={error_type}, "
            f"error_message={error_message}, "
            f"timestamp={timestamp}, "
            f"has_fallback={has_fallback}"
        )
        
        logger.error(log_message)
    
    def get_generic_error_message(self) -> str:
        """
        Get a generic error message to return when no fallback exists.
        
        Returns:
            A user-friendly error message
            
        Requirement: 9.4
        """
        return "I apologize, but I encountered an error processing your request. Please try again."


# Global registry instance
_global_registry = NodeExecutorRegistry()


def get_registry() -> NodeExecutorRegistry:
    """
    Get the global node executor registry instance.
    
    Returns:
        The global NodeExecutorRegistry instance
    """
    return _global_registry


def register_executor(node_type: str, executor_class: Type[NodeExecutor]) -> None:
    """
    Convenience function to register an executor with the global registry.
    
    Args:
        node_type: The node type identifier
        executor_class: The executor class that implements NodeExecutor
    """
    _global_registry.register(node_type, executor_class)


# ============================================================================
# Node Executor Implementations
# ============================================================================


class RAGNodeExecutor(NodeExecutor):
    """
    Executor for RAG (Retrieval-Augmented Generation) nodes.
    
    Performs vector search against Qdrant collections to retrieve relevant
    enterprise knowledge based on the user query. Supports multi-tenant
    isolation through company_id filtering.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
    """
    
    def __init__(self, qdrant_client, gemini_client):
        """
        Initialize the RAG node executor.
        
        Args:
            qdrant_client: QdrantClient instance for vector search
            gemini_client: Gemini client for embedding generation
        """
        self.qdrant = qdrant_client
        self.gemini = gemini_client
        logger.info("RAGNodeExecutor initialized")
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute RAG node to retrieve relevant documents from vector database.
        
        Args:
            config: Node configuration containing:
                - collection_name: Name of the Qdrant collection to search
                - query_template: Query string (with resolved context variables)
                - result_limit: Maximum number of results to retrieve
                - metadata_filters: Optional additional filters
            context: Runtime context with outputs from previous nodes
            session: Session context containing company_id for tenant isolation
        
        Returns:
            Concatenated text from retrieved documents
        
        Raises:
            NodeExecutionError: If embedding generation or vector search fails
            
        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
        """
        try:
            # Extract configuration parameters
            collection_name = config.get('collection_name')
            query_template = config.get('query_template', '')
            result_limit = config.get('result_limit', 5)
            metadata_filters = config.get('metadata_filters', {})
            company_id = session.get('company_id')
            
            if not collection_name:
                raise ValueError("collection_name is required in RAG node configuration")
            
            if not company_id:
                raise ValueError("company_id is required in session context for tenant isolation")
            
            logger.info(
                f"Executing RAG node - collection={collection_name}, "
                f"query_length={len(query_template)}, limit={result_limit}"
            )
            
            # Requirement 6.1: Generate embeddings using Gemini text-embedding-004
            embedding_result = self.gemini.models.embed_content(
                model="text-embedding-004",
                contents=query_template
            )
            
            # Extract the embedding vector
            query_vector = embedding_result.embeddings[0].values
            logger.debug(f"Generated embedding vector with dimension {len(query_vector)}")
            
            # Requirement 6.3: Apply company_id filter for tenant isolation
            # Build the filter for Qdrant search
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Start with company_id filter
            filter_conditions = [
                FieldCondition(
                    key="company_id",
                    match=MatchValue(value=company_id)
                )
            ]
            
            # Add any additional metadata filters from config
            for key, value in metadata_filters.items():
                filter_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Requirement 6.2, 6.4: Perform vector search against Qdrant collection
            # Namespace collection by company_id for additional isolation
            namespaced_collection = f"{company_id}_{collection_name}"
            
            logger.debug(
                f"Searching collection '{namespaced_collection}' with "
                f"{len(filter_conditions)} filters"
            )
            
            # Requirement 6.5: Retrieve top N results based on result_limit
            search_results = self.qdrant.search(
                collection_name=namespaced_collection,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=result_limit
            )
            
            logger.info(f"Retrieved {len(search_results)} documents from Qdrant")
            
            # Requirement 6.6: Concatenate retrieved document texts
            retrieved_texts = []
            for result in search_results:
                # Extract text from payload
                text = result.payload.get('text', '')
                if text:
                    retrieved_texts.append(text)
                    logger.debug(
                        f"Retrieved document: score={result.score:.4f}, "
                        f"text_length={len(text)}"
                    )
            
            # Concatenate with double newlines for readability
            concatenated_output = "\n\n".join(retrieved_texts)
            
            if not concatenated_output:
                logger.warning(
                    f"No documents retrieved from collection '{namespaced_collection}'. "
                    f"Returning empty string."
                )
                concatenated_output = ""
            
            logger.info(
                f"RAG node execution complete - "
                f"retrieved {len(retrieved_texts)} documents, "
                f"total_length={len(concatenated_output)}"
            )
            
            # Requirement 6.7: Store output in runtime context (handled by execution engine)
            return concatenated_output
            
        except Exception as e:
            logger.error(f"RAG node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="rag_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )


# Register the RAG executor with the global registry
register_executor('rag', RAGNodeExecutor)


class LLMNodeExecutor(NodeExecutor):
    """
    Executor for LLM (Large Language Model) nodes.
    
    Sends prompts to Gemini 2.5 Flash to generate natural language responses.
    Supports context variable resolution in prompts and configurable generation
    parameters like temperature and max_tokens.
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """
    
    def __init__(self, gemini_client):
        """
        Initialize the LLM node executor.
        
        Args:
            gemini_client: Gemini client for LLM generation
        """
        self.gemini = gemini_client
        logger.info("LLMNodeExecutor initialized")
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute LLM node to generate text using Gemini 2.5 Flash.
        
        Args:
            config: Node configuration containing:
                - system_prompt: System-level instructions for the LLM
                - user_prompt: User message or query (with resolved context variables)
                - temperature: Sampling temperature (0.0-1.0, default 0.7)
                - max_tokens: Maximum tokens to generate (default 1024)
                - model: Model to use (default 'gemini-2.5-flash')
            context: Runtime context with outputs from previous nodes
            session: Session context containing user information
        
        Returns:
            Generated text from the LLM
        
        Raises:
            NodeExecutionError: If LLM generation fails
            
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
        """
        try:
            # Requirement 7.1: Extract system_prompt and user_prompt from config
            system_prompt = config.get('system_prompt', '')
            user_prompt = config.get('user_prompt', '')
            
            # Requirement 7.4: Apply temperature and max_tokens parameters
            temperature = config.get('temperature', 0.7)
            max_tokens = config.get('max_tokens', 1024)
            model = config.get('model', 'gemini-2.5-flash')
            
            if not user_prompt:
                raise ValueError("user_prompt is required in LLM node configuration")
            
            logger.info(
                f"Executing LLM node - model={model}, "
                f"temperature={temperature}, max_tokens={max_tokens}, "
                f"system_prompt_length={len(system_prompt)}, "
                f"user_prompt_length={len(user_prompt)}"
            )
            
            # Requirement 7.2: Context variables are already resolved by the execution engine
            # before this method is called, so prompts contain actual values
            
            # Construct the full prompt
            # If system_prompt exists, prepend it to the user_prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
            else:
                full_prompt = user_prompt
            
            logger.debug(f"Full prompt length: {len(full_prompt)} characters")
            
            # Requirement 7.3: Call Gemini 2.5 Flash with configured parameters
            response = self.gemini.models.generate_content(
                model=model,
                contents=full_prompt,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_tokens
                }
            )
            
            # Requirement 7.5: Extract generated text from response
            generated_text = response.text
            
            if not generated_text:
                logger.warning("LLM returned empty response")
                generated_text = ""
            
            logger.info(
                f"LLM node execution complete - "
                f"generated_length={len(generated_text)}"
            )
            
            # Requirement 7.6: Store output in runtime context (handled by execution engine)
            return generated_text
            
        except Exception as e:
            logger.error(f"LLM node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="llm_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )


# Register the LLM executor with the global registry
register_executor('llm', LLMNodeExecutor)


class DecisionNodeExecutor(NodeExecutor):
    """
    Executor for Decision nodes.
    
    Performs intent classification using Gemini LLM to route conversations
    based on user intent. Supports multiple output edges labeled with intents
    and fallback routing when confidence is below threshold.
    
    Requirements: 30.1, 30.2, 30.3, 30.4, 30.5, 30.6
    """
    
    def __init__(self, gemini_client):
        """
        Initialize the Decision node executor.
        
        Args:
            gemini_client: Gemini client for LLM-based intent classification
        """
        self.gemini = gemini_client
        logger.info("DecisionNodeExecutor initialized")
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute Decision node to classify user intent and route conversation.
        
        Args:
            config: Node configuration containing:
                - classification_prompt: Base prompt for intent classification
                - intents: List of intent objects with name, description, confidence_threshold
                - fallback_intent: Intent to use when confidence is too low
            context: Runtime context with outputs from previous nodes
            session: Session context containing user information
        
        Returns:
            Classified intent name as a string
        
        Raises:
            NodeExecutionError: If intent classification fails
            
        Requirements: 30.1, 30.2, 30.3, 30.4, 30.5, 30.6
        """
        try:
            # Requirement 30.1, 30.2: Extract configuration parameters
            classification_prompt = config.get('classification_prompt', '')
            intents = config.get('intents', [])
            fallback_intent = config.get('fallback_intent', 'general_question')
            
            if not intents:
                raise ValueError("intents list is required in Decision node configuration")
            
            # Get user input from context (typically from trigger node)
            user_input = context.get('trigger_output', '')
            if not user_input:
                # Try to get from the most recent context variable
                user_input = session.get('user_transcript', '')
            
            logger.info(
                f"Executing Decision node - "
                f"user_input_length={len(user_input)}, "
                f"num_intents={len(intents)}"
            )
            
            # Requirement 30.3: Build intent classification prompt with available intents
            intent_descriptions = []
            for intent in intents:
                intent_name = intent.get('name', '')
                intent_desc = intent.get('description', '')
                intent_threshold = intent.get('confidence_threshold', 0.7)
                intent_descriptions.append(
                    f"- {intent_name}: {intent_desc} (threshold: {intent_threshold})"
                )
            
            intents_text = "\n".join(intent_descriptions)
            
            # Build the full classification prompt
            full_prompt = f"""{classification_prompt}

Available intents:
{intents_text}

User input: {user_input}

Classify the user's intent and respond with ONLY a JSON object in this exact format:
{{
  "intent": "intent_name",
  "confidence": 0.95
}}

The intent must be one of the available intents listed above. The confidence should be a number between 0 and 1."""
            
            logger.debug(f"Classification prompt length: {len(full_prompt)} characters")
            
            # Requirement 30.3: Call Gemini LLM to classify user intent
            response = self.gemini.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt,
                generation_config={
                    'temperature': 0.1,  # Low temperature for consistent classification
                    'max_output_tokens': 256
                }
            )
            
            response_text = response.text.strip()
            logger.debug(f"LLM response: {response_text}")
            
            # Requirement 30.4: Parse JSON response with intent and confidence
            import json
            
            # Extract JSON from response (handle markdown code blocks if present)
            if '```json' in response_text:
                # Extract JSON from markdown code block
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                # Extract JSON from generic code block
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text
            
            try:
                classification_result = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {json_text}")
                raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
            
            classified_intent = classification_result.get('intent', fallback_intent)
            intent_confidence = classification_result.get('confidence', 0.0)
            
            # Requirement 30.5: Check confidence threshold and apply fallback if needed
            # Find the intent configuration to get its threshold
            intent_config = next(
                (i for i in intents if i.get('name') == classified_intent),
                None
            )
            
            if intent_config:
                threshold = intent_config.get('confidence_threshold', 0.7)
                if intent_confidence < threshold:
                    logger.info(
                        f"Intent confidence {intent_confidence:.2f} below threshold {threshold:.2f}, "
                        f"using fallback intent '{fallback_intent}'"
                    )
                    classified_intent = fallback_intent
            else:
                # Intent not found in configuration, use fallback
                logger.warning(
                    f"Classified intent '{classified_intent}' not found in configuration, "
                    f"using fallback intent '{fallback_intent}'"
                )
                classified_intent = fallback_intent
            
            # Requirement 30.4: Store classified intent and confidence in context
            context['classified_intent'] = classified_intent
            context['intent_confidence'] = intent_confidence
            
            # Requirement 30.6: Log intent classification results for analytics
            logger.info(
                f"Intent classification complete - "
                f"intent={classified_intent}, "
                f"confidence={intent_confidence:.2f}, "
                f"user_input='{user_input[:50]}...'"
            )
            
            # Return the classified intent name for routing
            return classified_intent
            
        except Exception as e:
            logger.error(f"Decision node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="decision_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )


# Register the Decision executor with the global registry
register_executor('decision', DecisionNodeExecutor)


# ============================================================================
# Integration Client Base Classes
# ============================================================================


class IntegrationClient(ABC):
    """
    Abstract base class for integration clients.
    
    Each integration (HubSpot, Calendly, Zendesk, Salesforce) must implement
    this interface to be executable by the ActionNodeExecutor.
    """
    
    @abstractmethod
    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an integration-specific action.
        
        Args:
            action_type: The type of action to execute (e.g., 'create_contact', 'book_appointment')
            parameters: Action parameters with resolved context variables
        
        Returns:
            Dictionary containing action result with status and data
        
        Raises:
            Exception: If the action execution fails
        """
        pass


class HubSpotClient(IntegrationClient):
    """
    HubSpot CRM integration client.
    
    Supports actions: create_contact, log_call, update_deal, get_contact
    """
    
    def __init__(self, api_key: str):
        """
        Initialize HubSpot client.
        
        Args:
            api_key: HubSpot API key for authentication
        """
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
        logger.info("HubSpotClient initialized")
    
    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HubSpot-specific action."""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if action_type == "create_contact":
            # Create a new contact in HubSpot
            endpoint = f"{self.base_url}/crm/v3/objects/contacts"
            payload = {
                "properties": {
                    "email": parameters.get("email"),
                    "firstname": parameters.get("firstname"),
                    "lastname": parameters.get("lastname"),
                    "phone": parameters.get("phone"),
                    "company": parameters.get("company")
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "create_contact",
                    "contact_id": result.get("id"),
                    "data": result
                }
        
        elif action_type == "log_call":
            # Log a call engagement in HubSpot
            endpoint = f"{self.base_url}/crm/v3/objects/calls"
            payload = {
                "properties": {
                    "hs_timestamp": parameters.get("timestamp"),
                    "hs_call_title": parameters.get("title"),
                    "hs_call_body": parameters.get("notes"),
                    "hs_call_duration": parameters.get("duration_seconds"),
                    "hs_call_status": parameters.get("status", "COMPLETED")
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "log_call",
                    "call_id": result.get("id"),
                    "data": result
                }
        
        elif action_type == "update_deal":
            # Update a deal in HubSpot
            deal_id = parameters.get("deal_id")
            if not deal_id:
                raise ValueError("deal_id is required for update_deal action")
            
            endpoint = f"{self.base_url}/crm/v3/objects/deals/{deal_id}"
            payload = {
                "properties": {
                    "dealstage": parameters.get("stage"),
                    "amount": parameters.get("amount"),
                    "closedate": parameters.get("close_date")
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "update_deal",
                    "deal_id": deal_id,
                    "data": result
                }
        
        else:
            raise ValueError(f"Unknown HubSpot action type: {action_type}")


class CalendlyClient(IntegrationClient):
    """
    Calendly scheduling integration client.
    
    Supports actions: book_appointment, cancel_appointment, get_availability
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Calendly client.
        
        Args:
            api_key: Calendly API key for authentication
        """
        self.api_key = api_key
        self.base_url = "https://api.calendly.com"
        logger.info("CalendlyClient initialized")
    
    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Calendly-specific action."""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if action_type == "book_appointment":
            # Create a scheduling link or book an appointment
            endpoint = f"{self.base_url}/scheduling_links"
            payload = {
                "max_event_count": 1,
                "owner": parameters.get("owner_uri"),
                "owner_type": "EventType"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "book_appointment",
                    "booking_url": result.get("resource", {}).get("booking_url"),
                    "data": result
                }
        
        elif action_type == "cancel_appointment":
            # Cancel an existing appointment
            event_uri = parameters.get("event_uri")
            if not event_uri:
                raise ValueError("event_uri is required for cancel_appointment action")
            
            endpoint = f"{self.base_url}/scheduled_events/{event_uri}/cancellation"
            payload = {
                "reason": parameters.get("reason", "Cancelled by user")
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                
                return {
                    "status": "success",
                    "action": "cancel_appointment",
                    "event_uri": event_uri
                }
        
        else:
            raise ValueError(f"Unknown Calendly action type: {action_type}")


class ZendeskClient(IntegrationClient):
    """
    Zendesk support ticket integration client.
    
    Supports actions: create_ticket, update_ticket, add_comment, get_ticket
    """
    
    def __init__(self, subdomain: str, api_token: str, email: str):
        """
        Initialize Zendesk client.
        
        Args:
            subdomain: Zendesk subdomain (e.g., 'mycompany' for mycompany.zendesk.com)
            api_token: Zendesk API token for authentication
            email: Email address associated with the API token
        """
        self.subdomain = subdomain
        self.api_token = api_token
        self.email = email
        self.base_url = f"https://{subdomain}.zendesk.com/api/v2"
        logger.info(f"ZendeskClient initialized for subdomain: {subdomain}")
    
    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Zendesk-specific action."""
        import httpx
        import base64
        
        # Zendesk uses basic auth with email/token
        credentials = f"{self.email}/token:{self.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        if action_type == "create_ticket":
            # Create a new support ticket
            endpoint = f"{self.base_url}/tickets.json"
            payload = {
                "ticket": {
                    "subject": parameters.get("subject"),
                    "comment": {
                        "body": parameters.get("description")
                    },
                    "priority": parameters.get("priority", "normal"),
                    "status": parameters.get("status", "open"),
                    "requester": {
                        "name": parameters.get("requester_name"),
                        "email": parameters.get("requester_email")
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "create_ticket",
                    "ticket_id": result.get("ticket", {}).get("id"),
                    "data": result
                }
        
        elif action_type == "update_ticket":
            # Update an existing ticket
            ticket_id = parameters.get("ticket_id")
            if not ticket_id:
                raise ValueError("ticket_id is required for update_ticket action")
            
            endpoint = f"{self.base_url}/tickets/{ticket_id}.json"
            payload = {
                "ticket": {
                    "status": parameters.get("status"),
                    "priority": parameters.get("priority")
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "update_ticket",
                    "ticket_id": ticket_id,
                    "data": result
                }
        
        elif action_type == "add_comment":
            # Add a comment to an existing ticket
            ticket_id = parameters.get("ticket_id")
            if not ticket_id:
                raise ValueError("ticket_id is required for add_comment action")
            
            endpoint = f"{self.base_url}/tickets/{ticket_id}.json"
            payload = {
                "ticket": {
                    "comment": {
                        "body": parameters.get("comment"),
                        "public": parameters.get("public", True)
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "add_comment",
                    "ticket_id": ticket_id,
                    "data": result
                }
        
        else:
            raise ValueError(f"Unknown Zendesk action type: {action_type}")


class SalesforceClient(IntegrationClient):
    """
    Salesforce CRM integration client.
    
    Supports actions: create_lead, update_opportunity, create_task, get_account
    """
    
    def __init__(self, instance_url: str, access_token: str):
        """
        Initialize Salesforce client.
        
        Args:
            instance_url: Salesforce instance URL (e.g., 'https://mycompany.salesforce.com')
            access_token: Salesforce OAuth access token
        """
        self.instance_url = instance_url
        self.access_token = access_token
        self.base_url = f"{instance_url}/services/data/v57.0"
        logger.info(f"SalesforceClient initialized for instance: {instance_url}")
    
    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Salesforce-specific action."""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        if action_type == "create_lead":
            # Create a new lead in Salesforce
            endpoint = f"{self.base_url}/sobjects/Lead"
            payload = {
                "FirstName": parameters.get("first_name"),
                "LastName": parameters.get("last_name"),
                "Company": parameters.get("company"),
                "Email": parameters.get("email"),
                "Phone": parameters.get("phone"),
                "Status": parameters.get("status", "Open - Not Contacted")
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "create_lead",
                    "lead_id": result.get("id"),
                    "data": result
                }
        
        elif action_type == "update_opportunity":
            # Update an existing opportunity
            opportunity_id = parameters.get("opportunity_id")
            if not opportunity_id:
                raise ValueError("opportunity_id is required for update_opportunity action")
            
            endpoint = f"{self.base_url}/sobjects/Opportunity/{opportunity_id}"
            payload = {
                "StageName": parameters.get("stage"),
                "Amount": parameters.get("amount"),
                "CloseDate": parameters.get("close_date")
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                
                return {
                    "status": "success",
                    "action": "update_opportunity",
                    "opportunity_id": opportunity_id
                }
        
        elif action_type == "create_task":
            # Create a new task in Salesforce
            endpoint = f"{self.base_url}/sobjects/Task"
            payload = {
                "Subject": parameters.get("subject"),
                "Description": parameters.get("description"),
                "Status": parameters.get("status", "Not Started"),
                "Priority": parameters.get("priority", "Normal"),
                "ActivityDate": parameters.get("due_date")
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "status": "success",
                    "action": "create_task",
                    "task_id": result.get("id"),
                    "data": result
                }
        
        else:
            raise ValueError(f"Unknown Salesforce action type: {action_type}")


# ============================================================================
# Tool Node Executor
# ============================================================================


class ToolNodeExecutor(NodeExecutor):
    """
    Executor for Tool nodes.
    
    Executes HTTP requests to external APIs with support for all HTTP methods,
    custom headers, request bodies, and context variable resolution.
    Handles successful responses and triggers fallback on errors.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
    """
    
    def __init__(self):
        """
        Initialize the Tool node executor.
        
        No external dependencies required - uses httpx for HTTP requests.
        """
        pass
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute Tool node to make HTTP requests to external APIs.
        
        Args:
            config: Node configuration containing:
                - api_endpoint: The URL to call
                - http_method: HTTP method (GET, POST, PUT, DELETE)
                - headers: Dictionary of HTTP headers
                - request_body: JSON string for request body (optional)
                - timeout_ms: Request timeout in milliseconds (default: 5000)
            context: Runtime context with outputs from previous nodes
            session: Session context containing user information
        
        Returns:
            JSON string of the API response
        
        Raises:
            NodeExecutionError: If the HTTP request fails
        
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
        """
        import httpx
        import json
        
        try:
            # Requirement 8.1: Extract API endpoint, method, headers, and body from config
            api_endpoint = config.get('api_endpoint', '')
            http_method = config.get('http_method', 'GET').upper()
            headers = config.get('headers', {})
            request_body = config.get('request_body', None)
            timeout_ms = config.get('timeout_ms', 5000)
            
            if not api_endpoint:
                raise ValueError("api_endpoint is required in Tool node configuration")
            
            if http_method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                raise ValueError(f"Invalid HTTP method: {http_method}")
            
            logger.info(
                f"Executing Tool node - "
                f"method={http_method}, "
                f"endpoint={api_endpoint[:50]}..."
            )
            
            # Requirement 8.2: Context variables are already resolved by execution engine
            # The api_endpoint, headers, and request_body should already have {{variables}} replaced
            
            # Parse request body if provided
            body_data = None
            if request_body:
                try:
                    body_data = json.loads(request_body) if isinstance(request_body, str) else request_body
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in request_body: {request_body}")
                    raise ValueError(f"Invalid JSON in request_body: {str(e)}")
            
            # Requirement 8.3: Execute HTTP request with specified method
            timeout_seconds = timeout_ms / 1000.0
            
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                logger.debug(
                    f"Making {http_method} request to {api_endpoint} "
                    f"with headers={headers}, body={body_data}"
                )
                
                # Execute the appropriate HTTP method
                if http_method == 'GET':
                    response = await client.get(api_endpoint, headers=headers)
                elif http_method == 'POST':
                    response = await client.post(api_endpoint, headers=headers, json=body_data)
                elif http_method == 'PUT':
                    response = await client.put(api_endpoint, headers=headers, json=body_data)
                elif http_method == 'DELETE':
                    response = await client.delete(api_endpoint, headers=headers)
                elif http_method == 'PATCH':
                    response = await client.patch(api_endpoint, headers=headers, json=body_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {http_method}")
                
                logger.info(
                    f"Tool node HTTP request completed - "
                    f"status_code={response.status_code}, "
                    f"response_length={len(response.text)}"
                )
                
                # Requirement 8.4, 8.5: Check response status and parse JSON on success
                if 200 <= response.status_code < 300:
                    # Requirement 8.5: Parse JSON response on success
                    try:
                        response_data = response.json()
                        result = json.dumps(response_data, indent=2)
                        
                        logger.debug(f"Tool node successful response: {result[:200]}...")
                        
                        # Requirement 8.6: Return parsed response
                        return result
                    
                    except Exception:
                        # Response is not JSON, return as plain text
                        logger.warning("Tool node response is not JSON, returning as plain text")
                        return response.text
                
                else:
                    # Requirement 8.7: Trigger fallback on HTTP errors
                    error_message = (
                        f"HTTP {response.status_code} error from {api_endpoint}: "
                        f"{response.text[:200]}"
                    )
                    logger.error(error_message)
                    raise ValueError(error_message)
        
        except httpx.TimeoutException as e:
            error_message = f"HTTP request timeout after {timeout_ms}ms: {str(e)}"
            logger.error(error_message)
            raise NodeExecutionError(
                node_id="tool_node",
                error_type="TimeoutError",
                error_message=error_message
            )
        
        except httpx.RequestError as e:
            error_message = f"HTTP request failed: {str(e)}"
            logger.error(error_message)
            raise NodeExecutionError(
                node_id="tool_node",
                error_type="RequestError",
                error_message=error_message
            )
        
        except Exception as e:
            logger.error(f"Tool node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="tool_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )


# Register the Tool executor with the global registry
register_executor('tool', ToolNodeExecutor)


# ============================================================================
# Action Node Executor
# ============================================================================


class ActionNodeExecutor(NodeExecutor):
    """
    Executor for Action nodes.
    
    Executes business workflow actions through pre-built integrations with
    external systems like HubSpot, Calendly, Zendesk, and Salesforce.
    Supports parameter extraction from context, validation, and result handling.
    
    Requirements: 31.1, 31.2, 31.3, 31.4, 31.6, 31.7
    """
    
    def __init__(self, integration_clients: Dict[str, IntegrationClient]):
        """
        Initialize the Action node executor.
        
        Args:
            integration_clients: Dictionary mapping integration names to client instances
                                Example: {'hubspot': HubSpotClient(...), 'calendly': CalendlyClient(...)}
        
        Requirement: 31.2
        """
        self.clients = integration_clients
        logger.info(f"ActionNodeExecutor initialized with {len(integration_clients)} integrations")
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute Action node to perform business workflow automation.
        
        Args:
            config: Node configuration containing:
                - integration: Integration name ('hubspot', 'calendly', 'zendesk', 'salesforce')
                - action_type: Specific action to execute (e.g., 'create_contact', 'book_appointment')
                - parameters: Dictionary of action parameters (with resolved context variables)
                - require_confirmation: Whether to require user confirmation before executing
            context: Runtime context with outputs from previous nodes
            session: Session context containing user information
        
        Returns:
            JSON string containing action result with status and data
        
        Raises:
            NodeExecutionError: If action execution fails
            
        Requirements: 31.1, 31.2, 31.3, 31.4, 31.6, 31.7
        """
        try:
            # Requirement 31.2: Extract integration and action type from config
            integration = config.get('integration')
            action_type = config.get('action_type')
            parameters = config.get('parameters', {})
            require_confirmation = config.get('require_confirmation', False)
            
            if not integration:
                raise ValueError("integration is required in Action node configuration")
            
            if not action_type:
                raise ValueError("action_type is required in Action node configuration")
            
            logger.info(
                f"Executing Action node - integration={integration}, "
                f"action_type={action_type}, "
                f"require_confirmation={require_confirmation}"
            )
            
            # Requirement 31.3: Parameters already have context variables resolved by execution engine
            # Validate that all required parameters are present
            if not parameters:
                logger.warning("No parameters provided for action execution")
            
            # Requirement 31.4: Validate required parameters are present
            # This is a basic check - integration-specific validation happens in the client
            logger.debug(f"Action parameters: {list(parameters.keys())}")
            
            # Get the integration client
            client = self.clients.get(integration)
            if not client:
                raise ValueError(
                    f"Unknown integration: {integration}. "
                    f"Available integrations: {list(self.clients.keys())}"
                )
            
            # Check if confirmation is required
            if require_confirmation:
                # In a real implementation, this would check if user has confirmed
                # For now, we'll log and proceed
                logger.info("Action requires confirmation - proceeding with execution")
            
            # Requirement 31.6: Execute integration-specific action
            logger.debug(f"Calling {integration}.{action_type} with parameters")
            result = await client.execute_action(action_type, parameters)
            
            # Requirement 31.7: Return success/failure status and result data
            import json
            result_json = json.dumps(result, indent=2)
            
            logger.info(
                f"Action node execution complete - "
                f"integration={integration}, "
                f"action_type={action_type}, "
                f"status={result.get('status')}"
            )
            
            # Store action result in context for downstream nodes
            context[f"action_{integration}_{action_type}_result"] = result
            
            return result_json
            
        except Exception as e:
            logger.error(f"Action node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="action_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )


# Register the Action executor with the global registry
register_executor('action', ActionNodeExecutor)


# ============================================================================
# Graph Query Node Executor
# ============================================================================


class GraphQueryNodeExecutor(NodeExecutor):
    """
    Executor for Graph Query nodes.
    
    Queries the Neo4j knowledge graph using natural language questions.
    Generates Cypher queries via LLM based on graph schema and user question.
    Enforces read-only queries and supports self-correction on failure.
    
    Requirements: 41.1, 41.2, 41.3, 41.4, 41.5, 41.6, 41.7, 41.8, 41.9
    """
    
    def __init__(self, neo4j_driver, gemini_client):
        """
        Initialize the Graph Query node executor.
        
        Args:
            neo4j_driver: Neo4j driver instance for graph queries
            gemini_client: Gemini client for Cypher generation
        """
        self.neo4j = neo4j_driver
        self.gemini = gemini_client
        logger.info("GraphQueryNodeExecutor initialized")
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute Graph Query node to query Neo4j knowledge graph.
        
        Args:
            config: Node configuration containing:
                - max_depth: Maximum relationship hops (default: 3)
                - entity_types: Optional list of entity types to filter
                - relationship_types: Optional list of relationship types to filter
                - timeout_ms: Query timeout in milliseconds (default: 5000)
            context: Runtime context with outputs from previous nodes
            session: Session context containing company_id and user information
        
        Returns:
            JSON string containing graph query results
        
        Raises:
            NodeExecutionError: If graph query fails
            
        Requirements: 41.1, 41.2, 41.3, 41.4, 41.5, 41.6, 41.7, 41.8, 41.9
        """
        try:
            # Extract configuration parameters
            max_depth = config.get('max_depth', 3)
            entity_types = config.get('entity_types', [])
            relationship_types = config.get('relationship_types', [])
            timeout_ms = config.get('timeout_ms', 5000)
            company_id = session.get('company_id')
            
            if not company_id:
                raise ValueError("company_id is required in session context for tenant isolation")
            
            if not self.neo4j:
                raise ValueError("Neo4j driver not initialized. Check NEO4J_URI and NEO4J_PASSWORD.")
            
            # Requirement 41.2: Get user's question from context
            user_query = context.get('trigger_output', '')
            if not user_query:
                user_query = session.get('user_transcript', '')
            
            if not user_query:
                raise ValueError("No user query found in context or session")
            
            logger.info(
                f"Executing Graph Query node - "
                f"company_id={company_id}, "
                f"max_depth={max_depth}, "
                f"query_length={len(user_query)}"
            )
            
            # Requirement 41.2: Get graph schema for company
            schema = await self._get_graph_schema(company_id)
            
            # Requirement 41.3: Generate Cypher query using LLM
            cypher_query = await self._generate_cypher_query(
                user_query,
                schema,
                company_id,
                max_depth,
                entity_types,
                relationship_types
            )
            
            logger.debug(f"Generated Cypher query: {cypher_query}")
            
            # Requirement 41.7: Validate read-only query
            if not self._is_read_only_query(cypher_query):
                raise SecurityError(
                    "Only read-only Cypher queries are allowed. "
                    "Queries with CREATE, DELETE, SET, or MERGE are forbidden."
                )
            
            # Requirement 41.4, 41.8: Execute query with timeout
            try:
                results = await self._execute_cypher_query(
                    cypher_query,
                    company_id,
                    timeout_ms
                )
                
                # Requirement 41.6: Format results as JSON
                import json
                results_json = json.dumps(results, indent=2, default=str)
                
                logger.info(
                    f"Graph Query node execution complete - "
                    f"returned {len(results)} results, "
                    f"json_length={len(results_json)}"
                )
                
                return results_json
                
            except Exception as e:
                # Requirement 41.5: Attempt self-correction on failure
                logger.warning(f"Initial Cypher query failed: {str(e)}")
                logger.info("Attempting self-correction...")
                
                corrected_results = await self._retry_with_correction(
                    cypher_query,
                    str(e),
                    user_query,
                    schema,
                    company_id,
                    max_depth,
                    timeout_ms
                )
                
                return corrected_results
        
        except Exception as e:
            logger.error(f"Graph Query node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="graph_query_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )
    
    async def _get_graph_schema(self, company_id: str) -> str:
        """
        Get graph schema (ontology) for company from Neo4j.
        
        Requirement: 41.2
        
        Args:
            company_id: Company identifier
            
        Returns:
            String representation of graph schema
        """
        try:
            with self.neo4j.session() as neo_session:
                # Get all node labels for this company
                node_labels_query = """
                MATCH (n)
                WHERE n.company_id = $company_id
                RETURN DISTINCT labels(n) as labels
                LIMIT 100
                """
                
                node_results = neo_session.run(node_labels_query, company_id=company_id)
                
                # Extract unique labels
                all_labels = set()
                for record in node_results:
                    labels = record['labels']
                    for label in labels:
                        if label != 'Node':  # Skip generic Node label
                            all_labels.add(label)
                
                # Get all relationship types for this company
                rel_types_query = """
                MATCH (a)-[r]->(b)
                WHERE a.company_id = $company_id
                RETURN DISTINCT type(r) as rel_type
                LIMIT 100
                """
                
                rel_results = neo_session.run(rel_types_query, company_id=company_id)
                
                # Extract unique relationship types
                all_rel_types = set()
                for record in rel_results:
                    all_rel_types.add(record['rel_type'])
                
                # Format schema as string
                schema = f"""Graph Schema for company {company_id}:

Node Types (Labels):
{', '.join(sorted(all_labels)) if all_labels else 'No nodes found'}

Relationship Types:
{', '.join(sorted(all_rel_types)) if all_rel_types else 'No relationships found'}

All nodes have a 'company_id' property that must be filtered on.
Common node properties: name, created_at, updated_at
Relationship properties: confidence, source_document_id, created_at"""
                
                logger.debug(f"Retrieved graph schema: {len(all_labels)} node types, {len(all_rel_types)} relationship types")
                
                return schema
        
        except Exception as e:
            logger.error(f"Failed to retrieve graph schema: {str(e)}")
            # Return a minimal schema if retrieval fails
            return f"""Graph Schema for company {company_id}:

Node Types: Person, Project, Product, Department, Document, Company, Technology, Location
Relationship Types: MANAGES, OWNS, REPORTS_TO, WORKS_ON, CREATED, USES, LOCATED_IN, PART_OF

All nodes have a 'company_id' property that must be filtered on."""
    
    async def _generate_cypher_query(
        self,
        user_query: str,
        schema: str,
        company_id: str,
        max_depth: int,
        entity_types: list,
        relationship_types: list
    ) -> str:
        """
        Generate Cypher query using LLM based on user question and schema.
        
        Requirement: 41.3
        
        Args:
            user_query: User's natural language question
            schema: Graph schema string
            company_id: Company identifier
            max_depth: Maximum relationship hops
            entity_types: Optional entity type filters
            relationship_types: Optional relationship type filters
            
        Returns:
            Generated Cypher query string
        """
        # Build filter hints
        filter_hints = ""
        if entity_types:
            filter_hints += f"\n- Focus on these node types: {', '.join(entity_types)}"
        if relationship_types:
            filter_hints += f"\n- Focus on these relationship types: {', '.join(relationship_types)}"
        
        prompt = f"""You are a Cypher query expert. Generate a READ-ONLY Cypher query to answer the user's question.

{schema}

User Question: {user_query}

Requirements:
- Use MATCH and RETURN only (NO CREATE, DELETE, SET, MERGE, REMOVE)
- ALWAYS filter by company_id: '{company_id}' on ALL nodes
- Limit relationship traversal depth to {max_depth} hops maximum
- Return results as a list of records with meaningful field names
- Use LIMIT 50 to prevent large result sets
- Handle cases where entities might not exist{filter_hints}

Example format:
MATCH (p:Person {{company_id: '{company_id}'}})-[r:MANAGES*1..{max_depth}]->(proj:Project {{company_id: '{company_id}'}})
WHERE p.name CONTAINS 'John'
RETURN p.name as person_name, type(r) as relationship, proj.name as project_name
LIMIT 50

Generate ONLY the Cypher query, no explanations or markdown:"""
        
        # Call Gemini to generate Cypher
        response = self.gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'temperature': 0.1,  # Low temperature for consistent query generation
                'max_output_tokens': 512
            }
        )
        
        cypher_query = response.text.strip()
        
        # Clean up response (remove markdown code blocks if present)
        if cypher_query.startswith('```'):
            lines = cypher_query.split('\n')
            # Remove first and last lines (``` markers)
            cypher_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else cypher_query
            # Remove 'cypher' language identifier if present
            if cypher_query.startswith('cypher'):
                cypher_query = cypher_query[6:].strip()
        
        return cypher_query
    
    def _is_read_only_query(self, cypher_query: str) -> bool:
        """
        Validate that Cypher query is read-only.
        
        Requirement: 41.7
        
        Args:
            cypher_query: Cypher query to validate
            
        Returns:
            True if query is read-only, False otherwise
        """
        # Convert to uppercase for case-insensitive matching
        query_upper = cypher_query.upper()
        
        # List of forbidden write operations
        forbidden_keywords = [
            'CREATE',
            'DELETE',
            'SET',
            'MERGE',
            'REMOVE',
            'DROP',
            'DETACH'
        ]
        
        # Check if any forbidden keyword is present
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                logger.warning(f"Query contains forbidden keyword: {keyword}")
                return False
        
        return True
    
    async def _execute_cypher_query(
        self,
        cypher_query: str,
        company_id: str,
        timeout_ms: int
    ) -> list:
        """
        Execute Cypher query against Neo4j with timeout.
        
        Requirements: 41.4, 41.8
        
        Args:
            cypher_query: Cypher query to execute
            company_id: Company identifier for logging
            timeout_ms: Query timeout in milliseconds
            
        Returns:
            List of result records as dictionaries
        """
        import asyncio
        
        def run_query():
            """Synchronous query execution."""
            with self.neo4j.session() as neo_session:
                result = neo_session.run(cypher_query)
                records = [record.data() for record in result]
                return records
        
        # Requirement 41.8: Apply 5-second timeout (or configured timeout)
        timeout_seconds = timeout_ms / 1000.0
        
        try:
            # Run query in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            records = await asyncio.wait_for(
                loop.run_in_executor(None, run_query),
                timeout=timeout_seconds
            )
            
            logger.info(f"Cypher query executed successfully, returned {len(records)} records")
            return records
            
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Cypher query exceeded timeout of {timeout_ms}ms. "
                f"Consider reducing max_depth or adding more specific filters."
            )
    
    async def _retry_with_correction(
        self,
        original_query: str,
        error_message: str,
        user_query: str,
        schema: str,
        company_id: str,
        max_depth: int,
        timeout_ms: int
    ) -> str:
        """
        Attempt to correct failed Cypher query using LLM.
        
        Requirement: 41.5
        
        Args:
            original_query: The Cypher query that failed
            error_message: Error message from Neo4j
            user_query: Original user question
            schema: Graph schema
            company_id: Company identifier
            max_depth: Maximum relationship hops
            timeout_ms: Query timeout
            
        Returns:
            JSON string of corrected query results
            
        Raises:
            Exception: If correction also fails
        """
        logger.info("Attempting Cypher query self-correction")
        
        correction_prompt = f"""The following Cypher query failed with an error. Generate a corrected version.

Original User Question: {user_query}

{schema}

Failed Cypher Query:
{original_query}

Error Message:
{error_message}

Generate a corrected READ-ONLY Cypher query that:
- Fixes the syntax or logic error
- Still answers the user's question
- Uses MATCH and RETURN only (NO CREATE, DELETE, SET, MERGE)
- Filters by company_id: '{company_id}' on ALL nodes
- Limits depth to {max_depth} hops
- Uses LIMIT 50

Generate ONLY the corrected Cypher query, no explanations:"""
        
        # Call Gemini for correction
        response = self.gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=correction_prompt,
            config={
                'temperature': 0.1,
                'max_output_tokens': 512
            }
        )
        
        corrected_query = response.text.strip()
        
        # Clean up response
        if corrected_query.startswith('```'):
            lines = corrected_query.split('\n')
            corrected_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else corrected_query
            if corrected_query.startswith('cypher'):
                corrected_query = corrected_query[6:].strip()
        
        logger.debug(f"Corrected Cypher query: {corrected_query}")
        
        # Validate corrected query is read-only
        if not self._is_read_only_query(corrected_query):
            raise SecurityError("Corrected query is not read-only")
        
        # Execute corrected query
        try:
            results = await self._execute_cypher_query(
                corrected_query,
                company_id,
                timeout_ms
            )
            
            import json
            results_json = json.dumps(results, indent=2, default=str)
            
            logger.info(
                f"Corrected query executed successfully - "
                f"returned {len(results)} results"
            )
            
            return results_json
            
        except Exception as e:
            # Requirement 41.5: Only one retry attempt
            logger.error(f"Corrected query also failed: {str(e)}")
            raise Exception(
                f"Graph query failed after correction attempt. "
                f"Original error: {error_message}. "
                f"Correction error: {str(e)}"
            )


# Custom exception for security violations
class SecurityError(Exception):
    """Raised when a security constraint is violated."""
    pass


# Register the Graph Query executor with the global registry
register_executor('graph_query', GraphQueryNodeExecutor)


# ============================================================================
# Multi-Source RAG Node Executor
# ============================================================================


class MultiSourceRAGExecutor(NodeExecutor):
    """
    Executor for Multi-Source RAG nodes.
    
    Performs parallel vector searches across multiple Qdrant collections
    to retrieve comprehensive information from diverse knowledge sources.
    Supports weighted scoring for collection prioritization and includes
    source metadata in results.
    
    Requirements: 28.1, 28.2, 28.3, 28.4, 28.5, 28.6, 28.7
    """
    
    def __init__(self, qdrant_client, gemini_client):
        """
        Initialize the Multi-Source RAG node executor.
        
        Args:
            qdrant_client: QdrantClient instance for vector search
            gemini_client: Gemini client for embedding generation
        """
        self.qdrant = qdrant_client
        self.gemini = gemini_client
        logger.info("MultiSourceRAGExecutor initialized")
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute Multi-Source RAG node to retrieve from multiple collections.
        
        Args:
            config: Node configuration containing:
                - collection_names: List of Qdrant collection names to search
                - query_template: Query string (with resolved context variables)
                - result_limit: Maximum total results to return (default: 10)
                - collection_weights: Optional dict mapping collection names to weights
                - metadata_filters: Optional additional filters
            context: Runtime context with outputs from previous nodes
            session: Session context containing company_id for tenant isolation
        
        Returns:
            Concatenated text from retrieved documents with source metadata
        
        Raises:
            NodeExecutionError: If embedding generation or vector search fails
            
        Requirements: 28.1, 28.2, 28.3, 28.4, 28.5, 28.6, 28.7
        """
        try:
            # Requirement 28.1: Accept multiple Qdrant collection names in config
            collection_names = config.get('collection_names', [])
            query_template = config.get('query_template', '')
            result_limit = config.get('result_limit', 10)
            collection_weights = config.get('collection_weights', {})
            metadata_filters = config.get('metadata_filters', {})
            company_id = session.get('company_id')
            
            if not collection_names:
                raise ValueError("collection_names list is required in Multi-Source RAG node configuration")
            
            if not isinstance(collection_names, list):
                raise ValueError("collection_names must be a list of collection names")
            
            if not company_id:
                raise ValueError("company_id is required in session context for tenant isolation")
            
            logger.info(
                f"Executing Multi-Source RAG node - "
                f"collections={len(collection_names)}, "
                f"query_length={len(query_template)}, "
                f"total_limit={result_limit}"
            )
            
            # Generate embeddings using Gemini text-embedding-004
            embedding_result = self.gemini.models.embed_content(
                model="text-embedding-004",
                contents=query_template
            )
            
            query_vector = embedding_result.embeddings[0].values
            logger.debug(f"Generated embedding vector with dimension {len(query_vector)}")
            
            # Requirement 28.2: Perform parallel vector searches using asyncio.gather
            search_tasks = []
            for collection_name in collection_names:
                task = self._search_collection(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    company_id=company_id,
                    metadata_filters=metadata_filters,
                    # Request more results per collection to allow for ranking
                    limit=result_limit * 2
                )
                search_tasks.append(task)
            
            logger.debug(f"Launching {len(search_tasks)} parallel searches")
            
            # Execute all searches in parallel
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Collect all results and handle exceptions
            all_results = []
            for idx, result in enumerate(search_results):
                collection_name = collection_names[idx]
                
                if isinstance(result, Exception):
                    logger.warning(
                        f"Search failed for collection '{collection_name}': {str(result)}"
                    )
                    # Continue with other collections
                    continue
                
                # Add collection name to each result for tracking
                for search_result in result:
                    all_results.append({
                        'collection': collection_name,
                        'score': search_result.score,
                        'payload': search_result.payload,
                        'id': search_result.id
                    })
            
            logger.info(
                f"Retrieved {len(all_results)} total results from "
                f"{len(collection_names)} collections"
            )
            
            # Requirement 28.3, 28.4: Rank results by relevance score with weighted scoring
            ranked_results = self._rank_and_weight_results(
                all_results,
                collection_weights,
                result_limit
            )
            
            logger.info(
                f"After ranking and weighting: {len(ranked_results)} results "
                f"(limit: {result_limit})"
            )
            
            # Requirement 28.5, 28.6, 28.7: Format results with source metadata
            formatted_output = self._format_results_with_metadata(ranked_results)
            
            if not formatted_output:
                logger.warning(
                    f"No documents retrieved from any collection. Returning empty string."
                )
                formatted_output = ""
            
            logger.info(
                f"Multi-Source RAG node execution complete - "
                f"retrieved {len(ranked_results)} documents, "
                f"total_length={len(formatted_output)}"
            )
            
            return formatted_output
            
        except Exception as e:
            logger.error(f"Multi-Source RAG node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="multi_source_rag_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )
    
    async def _search_collection(
        self,
        collection_name: str,
        query_vector: list,
        company_id: str,
        metadata_filters: Dict[str, Any],
        limit: int
    ) -> list:
        """
        Search a single Qdrant collection.
        
        Requirement: 28.2
        
        Args:
            collection_name: Name of the collection to search
            query_vector: Embedding vector for the query
            company_id: Company identifier for tenant isolation
            metadata_filters: Additional metadata filters
            limit: Maximum results to retrieve from this collection
            
        Returns:
            List of search results from Qdrant
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # Build filter with company_id for tenant isolation
        filter_conditions = [
            FieldCondition(
                key="company_id",
                match=MatchValue(value=company_id)
            )
        ]
        
        # Add any additional metadata filters
        for key, value in metadata_filters.items():
            filter_conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        # Namespace collection by company_id
        namespaced_collection = f"{company_id}_{collection_name}"
        
        logger.debug(
            f"Searching collection '{namespaced_collection}' with "
            f"{len(filter_conditions)} filters, limit={limit}"
        )
        
        try:
            # Perform vector search
            search_results = self.qdrant.search(
                collection_name=namespaced_collection,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit
            )
            
            logger.debug(
                f"Collection '{collection_name}' returned {len(search_results)} results"
            )
            
            return search_results
            
        except Exception as e:
            logger.error(
                f"Failed to search collection '{namespaced_collection}': {str(e)}"
            )
            # Re-raise to be caught by gather
            raise
    
    def _rank_and_weight_results(
        self,
        all_results: list,
        collection_weights: Dict[str, float],
        limit: int
    ) -> list:
        """
        Rank results by relevance score with optional collection weighting.
        
        Requirements: 28.3, 28.4
        
        Args:
            all_results: List of all search results from all collections
            collection_weights: Dictionary mapping collection names to weight multipliers
            limit: Maximum number of results to return
            
        Returns:
            Top N ranked results after applying weights
        """
        # Requirement 28.4: Apply weighted scoring for collection prioritization
        for result in all_results:
            collection_name = result['collection']
            weight = collection_weights.get(collection_name, 1.0)
            
            # Apply weight to score
            result['weighted_score'] = result['score'] * weight
            result['weight'] = weight
        
        # Requirement 28.3: Rank results by weighted relevance score
        ranked_results = sorted(
            all_results,
            key=lambda x: x['weighted_score'],
            reverse=True  # Higher scores first
        )
        
        # Return top N results
        top_results = ranked_results[:limit]
        
        logger.debug(
            f"Ranked {len(all_results)} results, returning top {len(top_results)}"
        )
        
        return top_results
    
    def _format_results_with_metadata(self, results: list) -> str:
        """
        Format results with source metadata for LLM consumption.
        
        Requirements: 28.5, 28.6, 28.7
        
        Args:
            results: List of ranked search results
            
        Returns:
            Formatted string with documents and source metadata
        """
        formatted_chunks = []
        
        for idx, result in enumerate(results, 1):
            # Extract information
            collection = result['collection']
            score = result['score']
            weighted_score = result['weighted_score']
            weight = result['weight']
            payload = result['payload']
            
            # Requirement 28.6: Include source metadata
            text = payload.get('text', '')
            document_name = payload.get('filename', 'Unknown')
            chunk_index = payload.get('chunk_index', 0)
            
            # Format with clear source attribution
            # Requirement 28.7: Include collection_name and document_name in results
            chunk_header = (
                f"[Source {idx}: {collection} - {document_name} "
                f"(chunk {chunk_index}, score: {score:.3f}"
            )
            
            # Add weight info if weighted scoring was used
            if weight != 1.0:
                chunk_header += f", weight: {weight:.2f}, weighted_score: {weighted_score:.3f}"
            
            chunk_header += ")]"
            
            formatted_chunk = f"{chunk_header}\n{text}"
            formatted_chunks.append(formatted_chunk)
        
        # Requirement 28.5: Concatenate all results with clear separation
        formatted_output = "\n\n---\n\n".join(formatted_chunks)
        
        return formatted_output


# Register the Multi-Source RAG executor with the global registry
register_executor('multi_source_rag', MultiSourceRAGExecutor)



# ============================================================================
# Hybrid GraphRAG Executor
# ============================================================================


class HybridGraphRAGExecutor(NodeExecutor):
    """
    Executor for Hybrid GraphRAG nodes.
    
    Combines vector search (RAG) and graph traversal (Graph Query) to provide
    comprehensive retrieval that includes both semantic similarity and explicit
    entity relationships. Executes both retrieval methods in parallel and merges
    results into a hybrid context for LLM consumption.
    
    Requirements: 42.1, 42.2, 42.3, 42.6
    """
    
    def __init__(self, qdrant_client, gemini_client, neo4j_driver):
        """
        Initialize the Hybrid GraphRAG node executor.
        
        Args:
            qdrant_client: QdrantClient instance for vector search
            gemini_client: Gemini client for embedding generation and Cypher generation
            neo4j_driver: Neo4j driver instance for graph queries
        """
        self.qdrant = qdrant_client
        self.gemini = gemini_client
        self.neo4j = neo4j_driver
        
        # Initialize component executors for reuse
        self.rag_executor = RAGNodeExecutor(qdrant_client, gemini_client)
        self.graph_executor = GraphQueryNodeExecutor(neo4j_driver, gemini_client)
        
        logger.info("HybridGraphRAGExecutor initialized")
    
    async def execute(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Execute Hybrid GraphRAG node to retrieve from both vector and graph sources.
        
        This method:
        1. Executes vector search and graph query in parallel
        2. Tracks retrieval latency separately for each source
        3. Merges results from both sources into a hybrid context
        4. Formats the hybrid context for LLM consumption
        
        Args:
            config: Node configuration containing:
                - rag_config: Configuration for RAG node (collection_name, query_template, result_limit)
                - graph_config: Configuration for Graph Query node (max_depth, entity_types, relationship_types)
                - merge_strategy: How to combine results ('sequential', 'interleaved', 'weighted')
                - include_latency_metadata: Whether to include timing info in output (default: False)
            context: Runtime context with outputs from previous nodes
            session: Session context containing company_id and user information
        
        Returns:
            Formatted hybrid context string containing both vector and graph results
        
        Raises:
            NodeExecutionError: If both retrieval methods fail
            
        Requirements: 42.1, 42.2, 42.3, 42.6
        """
        import time
        
        try:
            # Extract configuration
            rag_config = config.get('rag_config', {})
            graph_config = config.get('graph_config', {})
            merge_strategy = config.get('merge_strategy', 'sequential')
            include_latency_metadata = config.get('include_latency_metadata', False)
            
            if not rag_config and not graph_config:
                raise ValueError(
                    "At least one of rag_config or graph_config must be provided "
                    "in Hybrid GraphRAG node configuration"
                )
            
            company_id = session.get('company_id')
            if not company_id:
                raise ValueError("company_id is required in session context for tenant isolation")
            
            logger.info(
                f"Executing Hybrid GraphRAG node - "
                f"has_rag={bool(rag_config)}, "
                f"has_graph={bool(graph_config)}, "
                f"merge_strategy={merge_strategy}"
            )
            
            # Requirement 42.2: Execute both retrieval nodes in parallel using asyncio.gather
            tasks = []
            task_names = []
            
            # Prepare vector search task if configured
            if rag_config:
                vector_start_time = time.time()
                vector_task = self._execute_vector_search(rag_config, context, session)
                tasks.append(vector_task)
                task_names.append('vector')
            
            # Prepare graph query task if configured
            if graph_config:
                graph_start_time = time.time()
                graph_task = self._execute_graph_query(graph_config, context, session)
                tasks.append(graph_task)
                task_names.append('graph')
            
            # Execute both tasks in parallel
            logger.debug(f"Launching {len(tasks)} parallel retrieval tasks: {task_names}")
            
            overall_start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            overall_duration = time.time() - overall_start_time
            
            # Process results and track latency
            vector_result = None
            vector_latency = 0.0
            graph_result = None
            graph_latency = 0.0
            
            for idx, result in enumerate(results):
                task_name = task_names[idx]
                
                if isinstance(result, Exception):
                    logger.warning(
                        f"{task_name.capitalize()} retrieval failed: {str(result)}"
                    )
                    # Store None for failed retrieval
                    if task_name == 'vector':
                        vector_result = None
                    else:
                        graph_result = None
                else:
                    # Successful retrieval
                    if task_name == 'vector':
                        vector_result = result['content']
                        vector_latency = result['latency']
                        logger.info(
                            f"Vector search completed in {vector_latency:.3f}s, "
                            f"content_length={len(vector_result)}"
                        )
                    else:
                        graph_result = result['content']
                        graph_latency = result['latency']
                        logger.info(
                            f"Graph query completed in {graph_latency:.3f}s, "
                            f"content_length={len(graph_result)}"
                        )
            
            # Check if at least one retrieval succeeded
            if vector_result is None and graph_result is None:
                raise NodeExecutionError(
                    node_id="hybrid_graphrag_node",
                    error_type="AllRetrievalsFailed",
                    error_message="Both vector search and graph query failed"
                )
            
            # Requirement 42.6: Track retrieval latency separately
            latency_metadata = {
                'vector_latency_ms': round(vector_latency * 1000, 2),
                'graph_latency_ms': round(graph_latency * 1000, 2),
                'total_latency_ms': round(overall_duration * 1000, 2),
                'parallel_speedup': round(
                    (vector_latency + graph_latency) / overall_duration, 2
                ) if overall_duration > 0 else 0
            }
            
            logger.info(
                f"Hybrid retrieval latency - "
                f"vector: {latency_metadata['vector_latency_ms']}ms, "
                f"graph: {latency_metadata['graph_latency_ms']}ms, "
                f"total: {latency_metadata['total_latency_ms']}ms, "
                f"speedup: {latency_metadata['parallel_speedup']}x"
            )
            
            # Store latency metadata in context for monitoring
            context['hybrid_graphrag_latency'] = latency_metadata
            
            # Requirement 42.3: Merge results from both sources and format for LLM
            hybrid_context = self._format_hybrid_context(
                vector_result=vector_result,
                graph_result=graph_result,
                merge_strategy=merge_strategy,
                latency_metadata=latency_metadata if include_latency_metadata else None
            )
            
            logger.info(
                f"Hybrid GraphRAG node execution complete - "
                f"hybrid_context_length={len(hybrid_context)}"
            )
            
            return hybrid_context
            
        except Exception as e:
            logger.error(f"Hybrid GraphRAG node execution failed: {type(e).__name__} - {str(e)}")
            raise NodeExecutionError(
                node_id="hybrid_graphrag_node",
                error_type=type(e).__name__,
                error_message=str(e)
            )
    
    async def _execute_vector_search(
        self,
        rag_config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute vector search using RAG executor.
        
        Requirement: 42.2
        
        Args:
            rag_config: RAG node configuration
            context: Runtime context
            session: Session context
            
        Returns:
            Dictionary with 'content' and 'latency' keys
        """
        import time
        
        start_time = time.time()
        
        try:
            # Execute RAG node
            vector_content = await self.rag_executor.execute(
                config=rag_config,
                context=context,
                session=session
            )
            
            latency = time.time() - start_time
            
            return {
                'content': vector_content,
                'latency': latency
            }
            
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Vector search failed after {latency:.3f}s: {str(e)}")
            raise
    
    async def _execute_graph_query(
        self,
        graph_config: Dict[str, Any],
        context: Dict[str, Any],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute graph query using Graph Query executor.
        
        Requirement: 42.2
        
        Args:
            graph_config: Graph Query node configuration
            context: Runtime context
            session: Session context
            
        Returns:
            Dictionary with 'content' and 'latency' keys
        """
        import time
        
        start_time = time.time()
        
        try:
            # Execute Graph Query node
            graph_content = await self.graph_executor.execute(
                config=graph_config,
                context=context,
                session=session
            )
            
            latency = time.time() - start_time
            
            return {
                'content': graph_content,
                'latency': latency
            }
            
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Graph query failed after {latency:.3f}s: {str(e)}")
            raise
    
    def _format_hybrid_context(
        self,
        vector_result: Optional[str],
        graph_result: Optional[str],
        merge_strategy: str,
        latency_metadata: Optional[Dict[str, Any]]
    ) -> str:
        """
        Format hybrid context for LLM consumption.
        
        Combines vector search results and graph query results into a single
        formatted string that the LLM can use to generate comprehensive responses.
        
        Requirement: 42.3
        
        Args:
            vector_result: Vector search results (or None if failed)
            graph_result: Graph query results (or None if failed)
            merge_strategy: How to combine results ('sequential', 'interleaved', 'weighted')
            latency_metadata: Optional latency information to include
            
        Returns:
            Formatted hybrid context string
        """
        sections = []
        
        # Add header
        sections.append("=== HYBRID CONTEXT (Vector + Graph) ===\n")
        
        # Add latency metadata if requested
        if latency_metadata:
            sections.append(f"Retrieval Performance:")
            sections.append(f"- Vector Search: {latency_metadata['vector_latency_ms']}ms")
            sections.append(f"- Graph Query: {latency_metadata['graph_latency_ms']}ms")
            sections.append(f"- Total (Parallel): {latency_metadata['total_latency_ms']}ms")
            sections.append(f"- Speedup: {latency_metadata['parallel_speedup']}x\n")
        
        # Format based on merge strategy
        if merge_strategy == 'sequential':
            # Vector results first, then graph results
            if vector_result:
                sections.append("--- VECTOR CONTEXT (Semantic Similarity) ---")
                sections.append(vector_result)
                sections.append("")
            
            if graph_result:
                sections.append("--- GRAPH CONTEXT (Entity Relationships) ---")
                sections.append(graph_result)
                sections.append("")
        
        elif merge_strategy == 'interleaved':
            # Alternate between vector and graph sections
            if vector_result and graph_result:
                sections.append("--- COMBINED CONTEXT ---")
                sections.append("\n[Vector Context - Semantic Similarity]")
                sections.append(vector_result)
                sections.append("\n[Graph Context - Entity Relationships]")
                sections.append(graph_result)
                sections.append("")
            elif vector_result:
                sections.append("--- VECTOR CONTEXT ONLY ---")
                sections.append(vector_result)
                sections.append("")
            elif graph_result:
                sections.append("--- GRAPH CONTEXT ONLY ---")
                sections.append(graph_result)
                sections.append("")
        
        elif merge_strategy == 'weighted':
            # Prioritize one source over the other based on configuration
            # For now, treat equally - future enhancement could add weights
            if vector_result and graph_result:
                sections.append("--- PRIMARY CONTEXT (Vector) ---")
                sections.append(vector_result)
                sections.append("\n--- SUPPORTING CONTEXT (Graph) ---")
                sections.append(graph_result)
                sections.append("")
            elif vector_result:
                sections.append("--- VECTOR CONTEXT ---")
                sections.append(vector_result)
                sections.append("")
            elif graph_result:
                sections.append("--- GRAPH CONTEXT ---")
                sections.append(graph_result)
                sections.append("")
        
        else:
            # Default: sequential
            logger.warning(f"Unknown merge_strategy '{merge_strategy}', using sequential")
            if vector_result:
                sections.append("--- VECTOR CONTEXT ---")
                sections.append(vector_result)
                sections.append("")
            if graph_result:
                sections.append("--- GRAPH CONTEXT ---")
                sections.append(graph_result)
                sections.append("")
        
        # Add instruction for LLM
        sections.append("=== INSTRUCTIONS ===")
        sections.append(
            "Cross-reference the vector context (semantic text excerpts) with the "
            "graph context (entity relationships) to provide a comprehensive answer. "
            "Cite both document sources and relationship paths when relevant."
        )
        
        # Join all sections
        hybrid_context = "\n".join(sections)
        
        return hybrid_context


# Register the Hybrid GraphRAG executor with the global registry
register_executor('hybrid_graphrag', HybridGraphRAGExecutor)
