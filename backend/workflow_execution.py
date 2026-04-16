"""
Workflow Execution Engine for dynamic workflow interpretation and execution.

This module provides the core execution engine that interprets Workflow JSON
and executes nodes in topological order with parallel optimization.

Requirements: 5.2, 5.3, 5.4, 5.5, 5.7, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5
"""
import asyncio
import re
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

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
    
    def __init__(self, workflow_json: dict, vapi_payload: dict):
        """
        Initialize the execution engine with workflow and Vapi payload.
        
        Args:
            workflow_json: The workflow configuration dictionary
            vapi_payload: The incoming Vapi request payload
            
        Requirements: 5.2, 5.3, 5.4
        """
        # Parse and validate workflow JSON
        self.workflow = WorkflowJSON(**workflow_json)
        self.vapi_payload = vapi_payload
        
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
    
    def _build_session_context(self) -> Dict[str, Any]:
        """
        Build session context from Vapi payload.
        
        The session context contains user information, conversation history,
        and other session-specific data that nodes can access.
        
        Returns:
            Session context dictionary
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
        
        # TODO: Load conversation history, user preferences, etc.
        # This will be implemented in future tasks
        
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
            return self.context.get(f"{final_node.id}_output", "")
        
        # Fallback: return last executed node output
        if execution_levels:
            last_level = execution_levels[-1]
            if last_level:
                last_node_id = last_level[-1]
                return self.context.get(f"{last_node_id}_output", "")
        
        return ""
    
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
