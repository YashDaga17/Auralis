"""
Voice Builder API Routes

This module provides endpoints for voice-based workflow building using Vapi.
It parses natural language voice commands into structured workflow actions.

Requirements: 21.1, 21.2, 21.3, 21.4
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import google.generativeai as genai
import os
import json

router = APIRouter(prefix="/api/voice-builder", tags=["voice-builder"])

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class VoiceCommandRequest(BaseModel):
    """Request model for voice command parsing."""
    transcript: str = Field(..., description="User's voice command transcript")
    workflow_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Current workflow state (nodes, edges) for context"
    )
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation turns for context"
    )


class VoiceCommandResponse(BaseModel):
    """Response model for parsed voice commands."""
    action: str = Field(..., description="Action type: add_node, connect_nodes, configure_node, delete_node, save_workflow, clarify")
    parameters: Dict[str, Any] = Field(..., description="Action-specific parameters")
    confirmation_message: str = Field(..., description="Natural language confirmation to speak back to user")
    requires_clarification: bool = Field(default=False, description="Whether the command needs clarification")
    clarification_question: Optional[str] = Field(default=None, description="Question to ask user for clarification")


COMMAND_PARSING_SYSTEM_PROMPT = """You are a voice command parser for a visual workflow builder. Your job is to parse natural language commands into structured actions.

Available Actions:
1. add_node - Add a new node to the canvas
   Parameters: node_type (trigger|rag|llm|tool|action|decision|graph_query|knowledge|multi_source_rag), position (optional), label (optional)

2. connect_nodes - Connect two nodes with an edge
   Parameters: source_node_id, target_node_id, label (optional for decision nodes)

3. configure_node - Configure a node's parameters
   Parameters: node_id, config (dict with node-specific configuration)

4. delete_node - Remove a node from the canvas
   Parameters: node_id

5. save_workflow - Save the current workflow
   Parameters: workflow_name (optional), description (optional)

6. clarify - Request clarification from the user
   Parameters: clarification_question

Node Types and Their Configurations:
- trigger: Entry point (no config needed)
- rag: collection_name, query_template, result_limit
- llm: system_prompt, user_prompt, temperature, max_tokens
- tool: api_endpoint, http_method, headers, request_body
- action: integration (hubspot|calendly|zendesk|salesforce), action_type, parameters
- decision: classification_prompt, intents (array)
- graph_query: max_depth, entity_types, relationship_types
- multi_source_rag: collection_names (array), result_limit

Context Variables:
- Use {{node_id_output}} syntax to reference outputs from other nodes
- Example: "Use the RAG results" → query_template: "{{rag_1_output}}"

Response Format:
Return ONLY valid JSON with this structure:
{
  "action": "add_node|connect_nodes|configure_node|delete_node|save_workflow|clarify",
  "parameters": {
    // action-specific parameters
  },
  "confirmation_message": "Natural language confirmation",
  "requires_clarification": false,
  "clarification_question": null
}

Examples:

User: "Add a RAG node that searches the customer database"
Response:
{
  "action": "add_node",
  "parameters": {
    "node_type": "rag",
    "label": "Search Customer Database",
    "config": {
      "collection_name": "customer_database",
      "query_template": "{{trigger_1_output}}",
      "result_limit": 5
    }
  },
  "confirmation_message": "I've added a RAG node that searches the customer database",
  "requires_clarification": false
}

User: "Connect the trigger to the RAG node"
Response:
{
  "action": "connect_nodes",
  "parameters": {
    "source_node_id": "trigger_1",
    "target_node_id": "rag_1"
  },
  "confirmation_message": "I've connected the trigger to the RAG node",
  "requires_clarification": false
}

User: "Add an LLM node that generates a response"
Response:
{
  "action": "add_node",
  "parameters": {
    "node_type": "llm",
    "label": "Generate Response",
    "config": {
      "system_prompt": "You are a helpful assistant",
      "user_prompt": "Based on this information: {{rag_1_output}}, answer: {{trigger_1_output}}",
      "temperature": 0.7,
      "max_tokens": 500
    }
  },
  "confirmation_message": "I've added an LLM node that will generate a response using the RAG results",
  "requires_clarification": false
}

User: "Save the workflow"
Response:
{
  "action": "save_workflow",
  "parameters": {},
  "confirmation_message": "I've saved your workflow",
  "requires_clarification": false
}

User: "Delete that node"
Response:
{
  "action": "clarify",
  "parameters": {
    "clarification_question": "Which node would you like me to delete? Please specify the node by its label or type."
  },
  "confirmation_message": "I need clarification",
  "requires_clarification": true,
  "clarification_question": "Which node would you like me to delete? Please specify the node by its label or type."
}

Important Rules:
1. Always return valid JSON
2. Use context variables ({{node_id_output}}) when referencing other nodes
3. Request clarification if the command is ambiguous
4. Provide natural, conversational confirmation messages
5. Infer reasonable defaults when possible (e.g., temperature=0.7 for LLM nodes)
6. Use the workflow_context to understand existing nodes and their IDs
"""


@router.post("/parse-command", response_model=VoiceCommandResponse)
async def parse_voice_command(request: VoiceCommandRequest):
    """
    Parse a natural language voice command into a structured workflow action.
    
    This endpoint uses Gemini to interpret user voice commands and convert them
    into actionable workflow operations (add node, connect nodes, etc.).
    
    Requirements: 21.3, 21.4
    """
    try:
        # Build context for the LLM
        context_info = ""
        if request.workflow_context:
            nodes = request.workflow_context.get("nodes", [])
            edges = request.workflow_context.get("edges", [])
            context_info = f"\n\nCurrent Workflow Context:\n"
            context_info += f"Nodes: {json.dumps([{'id': n['id'], 'type': n['type'], 'label': n.get('data', {}).get('label', '')} for n in nodes], indent=2)}\n"
            context_info += f"Edges: {json.dumps([{'source': e['source'], 'target': e['target']} for e in edges], indent=2)}"
        
        conversation_context = ""
        if request.conversation_history:
            conversation_context = "\n\nConversation History:\n"
            for turn in request.conversation_history[-3:]:  # Last 3 turns
                conversation_context += f"User: {turn.get('user', '')}\n"
                conversation_context += f"Assistant: {turn.get('assistant', '')}\n"
        
        # Construct prompt
        user_prompt = f"""Parse this voice command:

User Command: "{request.transcript}"{context_info}{conversation_context}

Return the structured action as JSON."""
        
        # Call Gemini
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            [COMMAND_PARSING_SYSTEM_PROMPT, user_prompt],
            generation_config={
                'temperature': 0.1,  # Low temperature for structured output
                'max_output_tokens': 1024
            }
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        parsed_command = json.loads(response_text)
        
        # Validate and return
        return VoiceCommandResponse(**parsed_command)
    
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM response as JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing voice command: {str(e)}"
        )


@router.get("/node-types")
async def get_node_types():
    """
    Get available node types and their configuration schemas.
    
    This endpoint provides metadata about available node types for the voice builder.
    """
    return {
        "node_types": [
            {
                "type": "trigger",
                "label": "Trigger",
                "description": "Entry point that receives user input",
                "config_schema": {}
            },
            {
                "type": "rag",
                "label": "RAG",
                "description": "Retrieve information from vector database",
                "config_schema": {
                    "collection_name": "string",
                    "query_template": "string (supports {{variables}})",
                    "result_limit": "number"
                }
            },
            {
                "type": "llm",
                "label": "LLM",
                "description": "Generate text using language model",
                "config_schema": {
                    "system_prompt": "string",
                    "user_prompt": "string (supports {{variables}})",
                    "temperature": "number (0-1)",
                    "max_tokens": "number"
                }
            },
            {
                "type": "tool",
                "label": "Tool",
                "description": "Call external API",
                "config_schema": {
                    "api_endpoint": "string",
                    "http_method": "GET|POST|PUT|DELETE",
                    "headers": "object",
                    "request_body": "string (JSON, supports {{variables}})"
                }
            },
            {
                "type": "action",
                "label": "Action",
                "description": "Execute business workflow action",
                "config_schema": {
                    "integration": "hubspot|calendly|zendesk|salesforce",
                    "action_type": "string",
                    "parameters": "object (supports {{variables}})"
                }
            },
            {
                "type": "decision",
                "label": "Decision",
                "description": "Route based on intent classification",
                "config_schema": {
                    "classification_prompt": "string",
                    "intents": "array of {name, description, confidence_threshold}"
                }
            },
            {
                "type": "graph_query",
                "label": "Graph Query",
                "description": "Query knowledge graph",
                "config_schema": {
                    "max_depth": "number",
                    "entity_types": "array of strings",
                    "relationship_types": "array of strings"
                }
            },
            {
                "type": "multi_source_rag",
                "label": "Multi-Source RAG",
                "description": "Retrieve from multiple collections",
                "config_schema": {
                    "collection_names": "array of strings",
                    "result_limit": "number"
                }
            }
        ]
    }
