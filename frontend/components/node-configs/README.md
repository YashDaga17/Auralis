# Node Configuration Components

This directory contains configuration form components for each node type in the visual workflow editor.

## Components

### ConfigurationPanel (Parent Component)
Located at `frontend/components/ConfigurationPanel.tsx`

Main component that:
- Displays the appropriate configuration form based on selected node type
- Manages context variable availability
- Handles configuration updates to the workflow store

### Node Type Forms

Each node type has its own configuration form component:

1. **RAGNodeConfig** - RAG (Retrieval Augmented Generation) nodes
   - Collection name (Qdrant collection)
   - Query template with variable support
   - Result limit (1-50)

2. **LLMNodeConfig** - LLM (Language Model) nodes
   - Model selection (Gemini 2.5 Flash/Pro)
   - System prompt
   - User prompt with variable support
   - Temperature (0-1)
   - Max tokens (1-8192)

3. **ToolNodeConfig** - External API call nodes
   - API endpoint with variable support
   - HTTP method (GET/POST/PUT/DELETE)
   - Headers (JSON)
   - Request body with variable support
   - Timeout (100-30000ms)

4. **GraphQueryNodeConfig** - Graph database query nodes
   - Max depth (1-10 hops)
   - Entity types filter (optional)
   - Relationship types filter (optional)
   - Timeout (100-30000ms)

5. **ActionNodeConfig** - Business workflow action nodes
   - Integration (HubSpot/Calendly/Zendesk/Salesforce)
   - Action type (integration-specific)
   - Parameters (JSON with variable support)
   - Require confirmation checkbox

6. **DecisionNodeConfig** - Intent classification and routing nodes
   - Classification prompt
   - Intent definitions (name, description, confidence threshold)
   - Fallback intent

### VariableAutocomplete Component

Shared component that provides:
- Context variable autocomplete when typing `{{`
- Visual display of available variables
- Click-to-insert functionality
- Used by all text input fields that support variable syntax

## Context Variables

Context variables use the `{{variable_name}}` syntax and are automatically resolved at runtime.

Available variables include:
- `{{trigger_output}}` - Output from the trigger node (user input)
- `{{node_id_output}}` - Output from any upstream node

The ConfigurationPanel automatically determines available variables based on the workflow graph structure.

## Validation

Each configuration form includes:
- Required field validation
- Type validation (numbers, JSON objects)
- Range validation (min/max values)
- Real-time error display
- Automatic updates to workflow store

## Usage

The ConfigurationPanel is used in the workflow editor:

```tsx
import ConfigurationPanel from '@/components/ConfigurationPanel';

<ConfigurationPanel selectedNode={selectedNode} />
```

The panel automatically:
1. Detects the node type
2. Renders the appropriate form
3. Validates input
4. Updates the workflow store
5. Provides context variable autocomplete
