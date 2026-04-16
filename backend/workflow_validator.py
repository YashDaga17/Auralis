"""
Workflow validation logic for ensuring workflow integrity.

This module provides validation functions to ensure workflows are valid DAGs
with proper configuration and context variable references.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
import re

from workflow_schema import (
    WorkflowJSON,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
    NODE_CONFIG_SCHEMAS
)


class WorkflowValidationError(Exception):
    """Exception raised when workflow validation fails."""
    pass


class WorkflowValidator:
    """
    Validates workflow configurations for structural and semantic correctness.
    
    Performs the following validations:
    - Exactly one trigger node exists
    - No cycles in the graph (DAG structure)
    - Required configuration fields per node type
    - Context variable references are valid
    """
    
    def __init__(self, workflow: WorkflowJSON):
        """
        Initialize validator with a workflow.
        
        Args:
            workflow: The workflow JSON to validate
        """
        self.workflow = workflow
        self.nodes_by_id: Dict[str, WorkflowNode] = {node.id: node for node in workflow.nodes}
        self.adjacency_list: Dict[str, List[str]] = self._build_adjacency_list()
        self.errors: List[str] = []
    
    def _build_adjacency_list(self) -> Dict[str, List[str]]:
        """Build adjacency list representation of the workflow graph."""
        adj_list = defaultdict(list)
        for edge in self.workflow.edges:
            adj_list[edge.source].append(edge.target)
        return dict(adj_list)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Perform complete workflow validation.
        
        Returns:
            Tuple of (is_valid, error_messages)
        
        Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
        """
        self.errors = []
        
        # Requirement 13.1: Validate exactly one trigger node
        self._validate_trigger_node()
        
        # Requirement 13.3: Validate no cycles (DAG structure)
        self._validate_dag_structure()
        
        # Requirement 13.4: Validate required configuration fields
        self._validate_node_configurations()
        
        # Requirement 13.5: Validate context variable references
        self._validate_context_variables()
        
        return len(self.errors) == 0, self.errors
    
    def _validate_trigger_node(self) -> None:
        """
        Validate that exactly one trigger node exists in the workflow.
        
        Requirement: 13.1
        """
        trigger_nodes = [node for node in self.workflow.nodes if node.type == NodeType.TRIGGER]
        
        if len(trigger_nodes) == 0:
            self.errors.append("Workflow must contain exactly one trigger node, but found 0")
        elif len(trigger_nodes) > 1:
            trigger_ids = [node.id for node in trigger_nodes]
            self.errors.append(
                f"Workflow must contain exactly one trigger node, but found {len(trigger_nodes)}: {trigger_ids}"
            )
    
    def _validate_dag_structure(self) -> None:
        """
        Validate that the workflow graph is a directed acyclic graph (no cycles).
        
        Uses topological sort (Kahn's algorithm) to detect cycles.
        
        Requirement: 13.3
        """
        if not self.workflow.nodes:
            return
        
        # Calculate in-degrees
        in_degree = {node.id: 0 for node in self.workflow.nodes}
        for edge in self.workflow.edges:
            in_degree[edge.target] += 1
        
        # Initialize queue with nodes having no incoming edges
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        processed_count = 0
        
        # Process nodes in topological order
        while queue:
            node_id = queue.popleft()
            processed_count += 1
            
            # Reduce in-degree for neighbors
            for neighbor in self.adjacency_list.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If not all nodes were processed, there's a cycle
        if processed_count != len(self.workflow.nodes):
            unprocessed = [node_id for node_id, degree in in_degree.items() if degree > 0]
            self.errors.append(
                f"Workflow contains cycles. Nodes involved in cycle: {unprocessed}"
            )
    
    def _validate_node_configurations(self) -> None:
        """
        Validate that each node has required configuration fields for its type.
        
        Requirement: 13.4
        """
        for node in self.workflow.nodes:
            # Skip trigger nodes as they don't require configuration
            if node.type == NodeType.TRIGGER:
                continue
            
            # Get the configuration schema for this node type
            config_schema = NODE_CONFIG_SCHEMAS.get(node.type)
            if not config_schema:
                # Node type doesn't have a specific config schema
                continue
            
            # Validate configuration against schema
            try:
                config_schema(**node.data.config)
            except Exception as e:
                self.errors.append(
                    f"Node '{node.id}' (type: {node.type}) has invalid configuration: {str(e)}"
                )
    
    def _validate_context_variables(self) -> None:
        """
        Validate that all context variable references are valid.
        
        Context variables must:
        1. Reference existing node IDs
        2. Reference nodes that appear earlier in execution order
        
        Requirement: 13.5
        """
        # Get topological order of nodes
        execution_order = self._get_execution_order()
        if not execution_order:
            # If we can't determine execution order (due to cycles), skip this validation
            # The cycle error will be reported by _validate_dag_structure
            return
        
        # Create a mapping of node position in execution order
        node_position = {node_id: idx for idx, node_id in enumerate(execution_order)}
        
        # Pattern to match context variables: {{variable_name}}
        context_var_pattern = re.compile(r'\{\{([^}]+)\}\}')
        
        for node in self.workflow.nodes:
            # Extract all string values from node configuration
            config_strings = self._extract_config_strings(node.data.config)
            
            for config_value in config_strings:
                # Find all context variable references
                matches = context_var_pattern.findall(config_value)
                
                for var_name in matches:
                    var_name = var_name.strip()
                    
                    # Check if variable references a node output
                    if var_name.endswith('_output'):
                        referenced_node_id = var_name[:-7]  # Remove '_output' suffix
                    else:
                        referenced_node_id = var_name
                    
                    # Validate referenced node exists
                    if referenced_node_id not in self.nodes_by_id:
                        self.errors.append(
                            f"Node '{node.id}' references non-existent context variable: {{{{{var_name}}}}}"
                        )
                        continue
                    
                    # Validate referenced node appears earlier in execution order
                    if node.id in node_position and referenced_node_id in node_position:
                        if node_position[referenced_node_id] >= node_position[node.id]:
                            self.errors.append(
                                f"Node '{node.id}' references context variable '{{{{{var_name}}}}}' "
                                f"from node '{referenced_node_id}' which appears later in execution order"
                            )
    
    def _extract_config_strings(self, config: Dict) -> List[str]:
        """
        Recursively extract all string values from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of all string values found in the configuration
        """
        strings = []
        
        for value in config.values():
            if isinstance(value, str):
                strings.append(value)
            elif isinstance(value, dict):
                strings.extend(self._extract_config_strings(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        strings.append(item)
                    elif isinstance(item, dict):
                        strings.extend(self._extract_config_strings(item))
        
        return strings
    
    def _get_execution_order(self) -> Optional[List[str]]:
        """
        Get the topological execution order of nodes.
        
        Returns:
            List of node IDs in execution order, or None if graph has cycles
        """
        if not self.workflow.nodes:
            return []
        
        # Calculate in-degrees
        in_degree = {node.id: 0 for node in self.workflow.nodes}
        for edge in self.workflow.edges:
            in_degree[edge.target] += 1
        
        # Initialize queue with nodes having no incoming edges
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        execution_order = []
        
        # Process nodes in topological order
        while queue:
            node_id = queue.popleft()
            execution_order.append(node_id)
            
            # Reduce in-degree for neighbors
            for neighbor in self.adjacency_list.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If not all nodes were processed, there's a cycle
        if len(execution_order) != len(self.workflow.nodes):
            return None
        
        return execution_order


def validate_workflow(workflow: WorkflowJSON) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a workflow.
    
    Args:
        workflow: The workflow JSON to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
        
    Example:
        >>> is_valid, errors = validate_workflow(workflow_json)
        >>> if not is_valid:
        ...     print("Validation errors:", errors)
    """
    validator = WorkflowValidator(workflow)
    return validator.validate()
