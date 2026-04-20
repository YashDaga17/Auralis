"""
Workflow Execution Engine for dynamic workflow interpretation and execution.

This module provides the core execution engine that interprets Workflow JSON
and executes nodes in topological order with parallel optimization.

Requirements: 5.2, 5.3, 5.4, 5.5, 5.7, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5
Requirements: 29.1, 29.2, 29.3, 29.4, 29.5, 29.6, 32.1, 32.2, 32.3
"""
import asyncio
import re
import logging
import json
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from workflow_schema import WorkflowJSON, WorkflowNode, NodeType
from node_executors import (
    NodeExecutor,
    NodeExecutorRegistry,
    FallbackHandler,
    NodeExecutionError,
    get_registry
)

logger = logging.getLogger(__name__)


class WorkflowExecutionEngine:
    """
    Dynamic execution engine that interprets and executes workflow graphs.
    
    The engine:
    - Parses Workflow JSON and builds DAG structure
    - Performs topological sort with level grouping for parallel execution
    - Manages runtime context for node outputs
    - Resolves context variables in node configurations
    - Executes nodes in parallel when possible
    
    Requirements: 5.2, 5.3, 5.4, 5.5, 5.7, 10.1, 10.2, 10.3, 10.4
    """
    
    def __init__(self, workflow_json: dict, vapi_payload: dict, db_session: Optional[Session] = None):
        """
        Initialize the execution engine with workflow and Vapi payload.
        
        Args:
            workflow_json: The workflow configuration dictionary
            vapi_payload: The incoming Vapi request payload
            db_session: Optional database session for conversation history
            
        Requirements: 5.2, 5.3, 5.4, 29.2, 29.3
        """
        # Parse and validate workflow JSON
        self.workflow = WorkflowJSON(**workflow_json)
        self.vapi_payload = vapi_payload
        self.db_session = db_session
        
        # Build node lookup dictionary
        self.nodes_by_id: Dict[str, WorkflowNode] = {
            node.id: node for node in self.workflow.nodes
        }
        
        # Build adjacency list for DAG traversal
        self.adjacency_list: Dict[str, List[str]] = self._build_adjacency_list()
        
        # Runtime context dictionary stores node outputs
        # Key format: "{node_id}_output"
        self.context: Dict[str, Any] = {}
        
        # Extract user transcript from Vapi payload
        self.user_transcript = self._extract_user_transcript()
        
        # Initialize context with trigger output
        trigger_node = self._find_trigger_node()
        if trigger_node:
            self.context[f"{trigger_node.id}_output"] = self.user_transcript
        
        # Initialize node executor registry and fallback handler
        self.executor_registry = get_registry()
        self.fallback_handler = FallbackHandler(self.adjacency_list, self.nodes_by_id)
        
        # Session context (will be populated with user info, conversation history, etc.)
        self.session_context: Dict[str, Any] = self._build_session_context()
    
    def _build_adjacency_list(self) -> Dict[str, List[str]]:
        """
        Build adjacency list representation of the workflow graph.
        
        Returns:
            Dictionary mapping node_id to list of target node_ids
            
        Requirement: 5.4
        """
        adj_list = defaultdict(list)
        for edge in self.workflow.edges:
            adj_list[edge.source].append(edge.target)
        return dict(adj_list)
    
    def _extract_user_transcript(self) -> str:
        """
        Extract user transcript from Vapi payload.
        
        The Vapi payload contains messages in OpenAI format.
        We extract the latest user message content.
        
        Returns:
            User transcript string
            
        Requirement: 5.4
        """
        messages = self.vapi_payload.get('messages', [])
        
        # Find the last user message
        for message in reversed(messages):
            if message.get('role') == 'user':
                return message.get('content', '')
        
        # Fallback: check for direct transcript field
        return self.vapi_payload.get('transcript', '')
    
    def _find_trigger_node(self) -> Optional[WorkflowNode]:
        """
        Find the trigger node in the workflow.
        
        Returns:
            The trigger node, or None if not found
            
        Requirement: 5.3
        """
        for node in self.workflow.nodes:
            if node.type == NodeType.TRIGGER:
                return node
        return None
    
    def _load_conversation_history(
        self, 
        user_id: str, 
        agent_id: str, 
        limit: int = 10,
        time_window_minutes: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Load conversation history from database.
        
        Retrieves the last N conversation turns for the user and agent
        within the specified time window.
        
        Args:
            user_id: User identifier
            agent_id: Agent identifier
            limit: Maximum number of conversation turns to retrieve
            time_window_minutes: Time window in minutes for session continuity
            
        Returns:
            List of conversation turn dictionaries
            
        Requirements: 29.2, 29.6
        """
        if not self.db_session:
            return []
        
        try:
            from models import ConversationHistory
            from sqlalchemy import and_
            
            # Calculate time threshold for session window
            time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            
            # Query conversation history
            conversations = self.db_session.query(ConversationHistory).filter(
                and_(
                    ConversationHistory.user_id == user_id,
                    ConversationHistory.agent_id == agent_id,
                    ConversationHistory.timestamp >= time_threshold
                )
            ).order_by(
                ConversationHistory.timestamp.desc()
            ).limit(limit).all()
            
            # Convert to dictionaries and reverse to chronological order
            history = []
            for conv in reversed(conversations):
                history.append({
                    'session_id': str(conv.session_id),
                    'timestamp': conv.timestamp.isoformat() if conv.timestamp else None,
                    'user_message': conv.user_message,
                    'agent_response': conv.agent_response,
                    'extracted_entities': conv.extracted_entities or {},
                    'intent': conv.intent,
                    'confidence': conv.confidence
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}", exc_info=True)
            return []
    
    def _load_user_preferences(
        self,
        user_id: str,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load user preferences from database.
        
        Retrieves user-specific preferences for personalization including
        communication style, preferred sources, and notification settings.
        
        Args:
            user_id: User identifier
            agent_id: Optional agent identifier for agent-specific preferences
            
        Returns:
            Dictionary containing user preferences
            
        Requirement: 37.2
        """
        if not self.db_session:
            return {}
        
        try:
            from models import UserPreference
            
            # Query user preferences
            query = self.db_session.query(UserPreference).filter(
                UserPreference.user_id == user_id
            )
            
            # If agent_id is provided, try to get agent-specific preferences first
            if agent_id:
                agent_prefs = query.filter(UserPreference.agent_id == agent_id).first()
                if agent_prefs:
                    return {
                        'communication_style': agent_prefs.communication_style,
                        'preferred_sources': agent_prefs.preferred_sources or [],
                        'notification_preferences': agent_prefs.notification_preferences or {}
                    }
            
            # Fall back to general user preferences (agent_id is NULL)
            general_prefs = query.filter(UserPreference.agent_id.is_(None)).first()
            if general_prefs:
                return {
                    'communication_style': general_prefs.communication_style,
                    'preferred_sources': general_prefs.preferred_sources or [],
                    'notification_preferences': general_prefs.notification_preferences or {}
                }
            
            # No preferences found - return defaults
            return {
                'communication_style': 'detailed',  # Default style
                'preferred_sources': [],
                'notification_preferences': {}
            }
            
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}", exc_info=True)
            return {
                'communication_style': 'detailed',
                'preferred_sources': [],
                'notification_preferences': {}
            }
    
    def _format_conversation_history(self, conversation_history: List[Dict[str, Any]]) -> str:
        """
        Format conversation history for use in {{conversation_history}} context variable.
        
        Args:
            conversation_history: List of conversation turn dictionaries
            
        Returns:
            Formatted conversation history string
            
        Requirement: 29.4
        """
        if not conversation_history:
            return ""
        
        formatted_lines = []
        for turn in conversation_history:
            user_msg = turn.get('user_message', '')
            agent_msg = turn.get('agent_response', '')
            
            if user_msg:
                formatted_lines.append(f"User: {user_msg}")
            if agent_msg:
                formatted_lines.append(f"Agent: {agent_msg}")
        
        return "\n".join(formatted_lines)
    
    def _aggregate_entities(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Aggregate extracted entities from conversation history.
        
        Combines entities from all conversation turns into a single dictionary
        organized by entity type.
        
        Args:
            conversation_history: List of conversation turn dictionaries
            
        Returns:
            Dictionary mapping entity types to lists of entity values
            
        Requirement: 29.5
        """
        aggregated = defaultdict(list)
        
        for turn in conversation_history:
            entities = turn.get('extracted_entities', {})
            if isinstance(entities, dict):
                for entity_type, entity_values in entities.items():
                    if isinstance(entity_values, list):
                        aggregated[entity_type].extend(entity_values)
                    else:
                        aggregated[entity_type].append(entity_values)
        
        # Remove duplicates while preserving order
        for entity_type in aggregated:
            seen = set()
            unique_values = []
            for value in aggregated[entity_type]:
                # Convert to string for comparison
                value_str = str(value)
                if value_str not in seen:
                    seen.add(value_str)
                    unique_values.append(value)
            aggregated[entity_type] = unique_values
        
        return dict(aggregated)
    
    def _build_session_context(self) -> Dict[str, Any]:
        """
        Build session context from Vapi payload and load conversation history.
        
        The session context contains user information, conversation history,
        and other session-specific data that nodes can access.
        
        Returns:
            Session context dictionary
            
        Requirements: 29.2, 29.3, 29.4, 37.2
        """
        # Extract basic session information from Vapi payload
        session_context = {
            'user_transcript': self.user_transcript,
            'vapi_payload': self.vapi_payload,
        }
        
        # Extract call metadata if available
        call_data = self.vapi_payload.get('call', {})
        if call_data:
            session_context['call_id'] = call_data.get('id')
            session_context['assistant_id'] = call_data.get('assistantId')
        
        # Extract metadata (including company_id for tenant isolation)
        metadata = self.vapi_payload.get('metadata', {})
        if metadata:
            session_context['company_id'] = metadata.get('company_id')
            session_context['user_id'] = metadata.get('user_id')
        
        # Load user preferences if database session is available
        # Requirement 37.2: Load user preferences into Session_Context
        if self.db_session and metadata.get('user_id'):
            user_preferences = self._load_user_preferences(
                user_id=metadata.get('user_id'),
                agent_id=call_data.get('assistantId')
            )
            session_context['user_preferences'] = user_preferences
        else:
            session_context['user_preferences'] = {}
        
        # Load conversation history if database session is available
        # Requirements: 29.2, 29.3, 29.4
        if self.db_session and metadata.get('user_id') and call_data.get('assistantId'):
            conversation_history = self._load_conversation_history(
                user_id=metadata.get('user_id'),
                agent_id=call_data.get('assistantId'),
                limit=10  # Last 10 conversation turns
            )
            session_context['conversation_history'] = conversation_history
            
            # Format conversation history for {{conversation_history}} context variable
            # Requirement 29.4
            formatted_history = self._format_conversation_history(conversation_history)
            self.context['conversation_history'] = formatted_history
            
            # Extract and aggregate entities from conversation history
            # Requirement 29.5
            aggregated_entities = self._aggregate_entities(conversation_history)
            session_context['extracted_entities'] = aggregated_entities
        else:
            session_context['conversation_history'] = []
            session_context['extracted_entities'] = {}
            self.context['conversation_history'] = ""
        
        return session_context
    
    def _topological_sort_with_levels(self) -> List[List[str]]:
        """
        Perform topological sort with level grouping for parallel execution.
        
        Uses Kahn's algorithm to compute topological order, grouping nodes
        by execution level. Nodes at the same level have no dependencies
        between them and can execute in parallel.
        
        Returns:
            List of levels, where each level is a list of node_ids that
            can execute in parallel
            
        Requirements: 5.5, 10.1, 10.2
        """
        if not self.workflow.nodes:
            return []
        
        # Calculate in-degrees for all nodes
        in_degree = {node.id: 0 for node in self.workflow.nodes}
        for edge in self.workflow.edges:
            in_degree[edge.target] += 1
        
        # Initialize queue with nodes having no incoming edges
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        levels = []
        
        # Process nodes level by level
        while queue:
            # All nodes in current queue are at the same level
            current_level = list(queue)
            levels.append(current_level)
            queue.clear()
            
            # Process all nodes in current level
            for node_id in current_level:
                # Reduce in-degree for all neighbors
                for neighbor in self.adjacency_list.get(node_id, []):
                    in_degree[neighbor] -= 1
                    # Add to queue if all dependencies satisfied
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return levels
    
    def resolve_context_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve context variables in node configuration.
        
        Recursively traverses the configuration dictionary and replaces
        {{variable}} placeholders with actual values from runtime context.
        
        Context variable format: {{variable_name}}
        Missing variables are replaced with empty string.
        
        Args:
            config: Node configuration dictionary
            
        Returns:
            Configuration with resolved context variables
            
        Requirements: 5.7, 11.1, 11.2, 11.3, 11.4, 11.5
        """
        # Pattern to match {{variable_name}}
        context_var_pattern = re.compile(r'\{\{([^}]+)\}\}')
        
        def resolve_value(value: Any) -> Any:
            """Recursively resolve context variables in a value."""
            if isinstance(value, str):
                # Replace all {{variable}} patterns in the string
                def replacer(match):
                    var_name = match.group(1).strip()
                    
                    # Look up variable in context
                    if var_name in self.context:
                        return str(self.context[var_name])
                    else:
                        # Missing variable: replace with empty string and log warning
                        logger.warning(
                            f"Context variable '{{{{{var_name}}}}}' not found in runtime context. "
                            f"Replacing with empty string."
                        )
                        return ''
                
                return context_var_pattern.sub(replacer, value)
            
            elif isinstance(value, dict):
                # Recursively resolve dictionary values
                return {k: resolve_value(v) for k, v in value.items()}
            
            elif isinstance(value, list):
                # Recursively resolve list items
                return [resolve_value(item) for item in value]
            
            else:
                # Non-string, non-dict, non-list values pass through unchanged
                return value
        
        return resolve_value(config)
    
    async def execute(self) -> str:
        """
        Execute the workflow and return the final output.
        
        This is the main entry point for workflow execution. It:
        1. Computes topological execution order with level grouping
        2. Executes nodes level by level
        3. Executes nodes at the same level in parallel
        4. Resolves context variables before each node execution
        5. Handles errors and executes fallback nodes when available
        6. Returns the final node output
        
        Returns:
            Final node output as a string
            
        Requirements: 5.5, 10.1, 10.2, 10.3, 10.4, 9.1, 9.2, 9.3, 9.4, 9.5
        """
        # Get execution order grouped by levels
        execution_levels = self._topological_sort_with_levels()
        
        if not execution_levels:
            logger.error("No nodes to execute in workflow")
            return ""
        
        # Execute nodes level by level
        for level_index, level_nodes in enumerate(execution_levels):
            logger.info(f"Executing level {level_index} with {len(level_nodes)} nodes: {level_nodes}")
            
            # Execute all nodes in this level in parallel
            tasks = [self._execute_node(node_id) for node_id in level_nodes]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and failures
            for node_id, result in zip(level_nodes, results):
                if isinstance(result, Exception):
                    # Node execution failed
                    await self._handle_node_failure(node_id, result)
                else:
                    logger.info(f"Node {node_id} completed successfully")
                    self.context[f"{node_id}_output"] = result
        
        # Find the final node (node with no outgoing edges)
        final_node = self._find_final_node()
        if final_node:
            final_output = self.context.get(f"{final_node.id}_output", "")
        else:
            # Fallback: return last executed node output
            if execution_levels:
                last_level = execution_levels[-1]
                if last_level:
                    last_node_id = last_level[-1]
                    final_output = self.context.get(f"{last_node_id}_output", "")
                else:
                    final_output = ""
            else:
                final_output = ""
        
        # Extract entities from user message and store conversation turn
        # Requirements: 29.1, 29.5, 32.1, 32.2, 32.3
        if self.db_session:
            await self._save_conversation_turn(
                user_message=self.user_transcript,
                agent_response=final_output
            )
        
        return final_output
    
    async def _execute_node(self, node_id: str) -> str:
        """
        Execute a single node using the registered executor.
        
        This method:
        1. Looks up the node configuration
        2. Resolves context variables in the configuration
        3. Gets the appropriate executor from the registry
        4. Executes the node with the resolved configuration
        
        Args:
            node_id: ID of the node to execute
            
        Returns:
            Node output as a string
            
        Raises:
            NodeExecutionError: If the node execution fails
            
        Requirements: 5.7, 17.2, 17.3, 17.5
        """
        node = self.nodes_by_id.get(node_id)
        if not node:
            raise NodeExecutionError(
                node_id=node_id,
                error_type="NodeNotFound",
                error_message=f"Node {node_id} not found in workflow"
            )
        
        # Resolve context variables in node configuration
        resolved_config = self.resolve_context_variables(node.data.config)
        
        logger.info(f"Executing node {node_id} of type {node.type}")
        logger.debug(f"Resolved config: {resolved_config}")
        
        # Trigger nodes just pass through their input
        if node.type == NodeType.TRIGGER:
            return self.context.get(f"{node_id}_output", "")
        
        # Get executor for this node type
        executor_class = self.executor_registry.get_executor(node.type.value)
        
        if executor_class is None:
            raise NodeExecutionError(
                node_id=node_id,
                error_type="ExecutorNotFound",
                error_message=f"No executor registered for node type '{node.type.value}'"
            )
        
        # Instantiate and execute the executor
        # Note: Executors may need dependencies (Qdrant client, Gemini client, etc.)
        # For now, we'll instantiate without dependencies
        # Future tasks will implement specific executors with proper dependency injection
        executor = executor_class()
        
        try:
            result = await executor.execute(resolved_config, self.context, self.session_context)
            return result
        except Exception as e:
            # Wrap any exception in NodeExecutionError for consistent handling
            if isinstance(e, NodeExecutionError):
                raise
            else:
                raise NodeExecutionError(
                    node_id=node_id,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
    
    def _find_final_node(self) -> Optional[WorkflowNode]:
        """
        Find the final node in the workflow (node with no outgoing edges).
        
        Returns:
            The final node, or None if not found
        """
        # Build set of nodes that have outgoing edges
        nodes_with_outgoing = set(self.adjacency_list.keys())
        
        # Find nodes with no outgoing edges
        for node in self.workflow.nodes:
            if node.id not in nodes_with_outgoing:
                return node
        
        # If all nodes have outgoing edges, return the last node
        if self.workflow.nodes:
            return self.workflow.nodes[-1]
        
        return None
    
    async def _handle_node_failure(self, node_id: str, error: Exception) -> None:
        """
        Handle node execution failure with fallback logic.
        
        This method:
        1. Logs the failure with detailed information
        2. Checks for a connected fallback node
        3. If fallback exists, executes it with error details
        4. If no fallback, stores a generic error message
        
        Args:
            node_id: The ID of the node that failed
            error: The exception that was raised
            
        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
        """
        # Find fallback node
        fallback_node_id = self.fallback_handler.find_fallback_node(node_id)
        
        # Log the failure
        self.fallback_handler.log_failure(node_id, error, has_fallback=fallback_node_id is not None)
        
        if fallback_node_id:
            # Prepare error context for fallback node
            error_context = self.fallback_handler.prepare_error_context(
                node_id, error, self.context
            )
            
            # Update context with error details
            self.context.update(error_context)
            
            try:
                # Execute fallback node
                logger.info(f"Executing fallback node {fallback_node_id} for failed node {node_id}")
                fallback_result = await self._execute_node(fallback_node_id)
                
                # Store fallback result as the failed node's output
                self.context[f"{node_id}_output"] = fallback_result
                logger.info(f"Fallback node {fallback_node_id} executed successfully")
                
            except Exception as fallback_error:
                # Fallback node also failed
                logger.error(
                    f"Fallback node {fallback_node_id} also failed: {fallback_error}"
                )
                # Store generic error message
                self.context[f"{node_id}_output"] = self.fallback_handler.get_generic_error_message()
        else:
            # No fallback node - store generic error message
            self.context[f"{node_id}_output"] = self.fallback_handler.get_generic_error_message()
            
        # Always store error information for debugging
        self.context[f"{node_id}_error"] = str(error)
        self.context[f"{node_id}_error_type"] = type(error).__name__
    
    async def _extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entities from text using Gemini LLM.
        
        Extracts common entity types: person_name, company_name, date, time,
        email, phone_number, product_name, dollar_amount.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Dictionary mapping entity types to lists of extracted entities
            with confidence scores
            
        Requirements: 32.1, 32.2, 32.3
        """
        if not text or not text.strip():
            return {}
        
        try:
            import os
            from google import genai
            
            # Initialize Gemini client
            genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            
            # Prompt for entity extraction
            prompt = f"""Extract entities from the following text. Return a JSON object with entity types as keys and arrays of entities as values.

Entity types to extract:
- person_name: Names of people
- company_name: Names of companies or organizations
- date: Dates (e.g., "tomorrow", "next Tuesday", "March 15")
- time: Times (e.g., "2pm", "3:30", "morning")
- email: Email addresses
- phone_number: Phone numbers
- product_name: Product or service names
- dollar_amount: Monetary amounts (e.g., "$100", "fifty dollars")

For each entity, include:
- value: The extracted text
- confidence: A confidence score between 0.0 and 1.0

Text: {text}

Return ONLY valid JSON in this format:
{{
  "person_name": [{{"value": "John Smith", "confidence": 0.95}}],
  "date": [{{"value": "tomorrow", "confidence": 0.9}}]
}}

If no entities are found for a type, omit that key. Return an empty object {{}} if no entities are found at all."""

            # Call Gemini with JSON mode
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            
            # Parse JSON response
            entities_json = response.text.strip()
            entities = json.loads(entities_json)
            
            # Validate structure
            if not isinstance(entities, dict):
                logger.warning(f"Entity extraction returned non-dict: {type(entities)}")
                return {}
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}", exc_info=True)
            return {}
    
    async def _save_conversation_turn(
        self, 
        user_message: str, 
        agent_response: str
    ) -> None:
        """
        Save conversation turn to database with entity extraction.
        
        Extracts entities from the user message and stores the complete
        conversation turn in the database.
        
        Args:
            user_message: User's message
            agent_response: Agent's response
            
        Requirements: 29.1, 29.5, 32.1, 32.2, 32.3
        """
        if not self.db_session:
            return
        
        try:
            from models import ConversationHistory
            import uuid
            
            # Extract metadata from session context
            user_id = self.session_context.get('user_id')
            agent_id = self.session_context.get('assistant_id')
            company_id_str = self.session_context.get('company_id')
            
            # Convert company_id string to UUID if needed
            if company_id_str:
                if isinstance(company_id_str, str):
                    company_id = uuid.UUID(company_id_str)
                else:
                    company_id = company_id_str
            else:
                company_id = None
            
            # Skip if required fields are missing
            if not user_id or not agent_id or not company_id:
                logger.warning(
                    f"Skipping conversation storage: missing required fields "
                    f"(user_id={user_id}, agent_id={agent_id}, company_id={company_id})"
                )
                return
            
            # Extract entities from user message
            extracted_entities = await self._extract_entities(user_message)
            
            # Create conversation history record
            conversation = ConversationHistory(
                session_id=uuid.uuid4(),
                user_id=user_id,
                agent_id=agent_id,
                company_id=company_id,
                timestamp=datetime.utcnow(),
                user_message=user_message,
                agent_response=agent_response,
                extracted_entities=extracted_entities,
                intent=None,  # TODO: Implement intent classification in future task
                confidence=None
            )
            
            self.db_session.add(conversation)
            self.db_session.commit()
            
            logger.info(
                f"Saved conversation turn for user {user_id}, agent {agent_id}. "
                f"Extracted {sum(len(v) for v in extracted_entities.values())} entities."
            )
            
        except Exception as e:
            logger.error(f"Error saving conversation turn: {e}", exc_info=True)
            if self.db_session:
                self.db_session.rollback()
