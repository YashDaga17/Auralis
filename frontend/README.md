# Auralis Frontend

Next.js frontend for the Auralis Visual Workflow Engine. Provides a drag-and-drop interface for building, testing, and deploying AI-powered voice agent workflows.

## Overview

The frontend is a single-page application built around a ReactFlow canvas. Users drag node types onto the canvas, connect them, configure each node, upload knowledge documents, and test the workflow — all without writing code. Authentication is handled by Clerk, and all API calls go to the FastAPI backend.

## Tech Stack

- Next.js 16 (App Router)
- React 19
- TypeScript 5
- Zustand (state management)
- ReactFlow 11 (workflow canvas)
- react-force-graph-2d (knowledge graph visualization)
- Axios (HTTP client)
- Clerk (authentication)
- Vapi Web SDK (voice integration)
- Tailwind CSS 4
- Jest + React Testing Library (testing)

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx                      # Root layout with Clerk provider
│   ├── page.tsx                        # Landing page
│   ├── workflow-editor/
│   │   └── page.tsx                    # Main workflow editor page
│   ├── graph-explorer/
│   │   └── page.tsx                    # Knowledge graph explorer page
│   ├── sign-in/[[...sign-in]]/page.tsx # Clerk sign-in
│   └── sign-up/[[...sign-up]]/page.tsx # Clerk sign-up
├── components/
│   ├── WorkflowCanvas.tsx              # ReactFlow canvas with drag-and-drop
│   ├── NodePalette.tsx                 # Draggable node type selector
│   ├── CustomNode.tsx                  # Custom node renderer
│   ├── ConfigurationPanel.tsx          # Node configuration form
│   ├── TestPanel.tsx                   # Workflow test runner
│   ├── VoiceBuilder.tsx                # Voice/text command interface
│   ├── FileDropZone.tsx                # Document upload with progress
│   ├── ValidationErrorDisplay.tsx      # Inline validation error overlay
│   ├── GraphExplorer.tsx               # Force-directed graph visualization
│   ├── LinkEditorModal.tsx             # Edge label and routing editor
│   ├── NodeEditorModal.tsx             # Node creation and editing modal
│   ├── UserPreferencesPanel.tsx        # User settings panel
│   ├── ProtectedRoute.tsx              # Authentication guard
│   ├── AuralisButton.tsx               # Vapi voice call button
│   ├── UserButton.tsx                  # Clerk user menu
│   └── node-configs/
│       ├── RAGNodeConfig.tsx           # RAG node configuration form
│       ├── LLMNodeConfig.tsx           # LLM node configuration form
│       ├── ToolNodeConfig.tsx          # Tool node configuration form
│       ├── ActionNodeConfig.tsx        # Action node configuration form
│       ├── DecisionNodeConfig.tsx      # Decision node configuration form
│       ├── GraphQueryNodeConfig.tsx    # Graph query node configuration form
│       └── VariableAutocomplete.tsx    # Context variable autocomplete input
├── stores/
│   ├── workflowStore.ts                # Workflow nodes, edges, save/load/validate
│   ├── graphStore.ts                   # Knowledge graph data and path finding
│   ├── knowledgeStore.ts               # File upload jobs and collections
│   ├── historyStore.ts                 # Undo/redo state snapshots
│   ├── index.ts                        # Store exports
│   └── __tests__/
│       ├── workflowStore.test.ts       # Workflow store unit tests
│       └── importExport.test.ts        # Import/export unit tests
├── hooks/
│   └── useAuth.ts                      # Clerk authentication hook
├── lib/
│   ├── api-client.ts                   # Axios client with auth token injection
│   └── auth.ts                         # Clerk configuration
├── middleware.ts                        # Route protection middleware
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment variables

Create `.env.local`:

```env
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/workflow-editor
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/workflow-editor

# Vapi (optional — only needed for voice mode)
NEXT_PUBLIC_VAPI_PUBLIC_KEY=your_vapi_public_key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your_vapi_assistant_id
```

### 3. Start the development server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

## Authentication

Authentication is handled by Clerk. The `useAuth` hook provides:

- `isAuthenticated`: Whether the user is logged in
- `token`: JWT token for backend API requests
- `user`: User object with `id`, `email`, and `companyId`
- `getToken()`: Fetches a fresh JWT token

The `companyId` is derived from the user's Clerk organization membership. All API requests include the JWT in the `Authorization: Bearer` header via the `createApiClient(token)` factory.

Protected routes use the `ProtectedRoute` component and Next.js middleware to redirect unauthenticated users to `/sign-in`.

## Pages

### Workflow Editor (`/workflow-editor`)

The main page. Combines all components into a full workflow building experience:

- Toolbar with Save, Validate, Clear, Export, Import, Test, and Voice Builder buttons
- Node palette on the left for dragging node types onto the canvas
- ReactFlow canvas in the center
- Configuration panel on the right when a node is selected
- File upload modal for adding knowledge documents
- Test panel for running the workflow with a test input
- Voice builder for creating workflows via text or voice commands

### Graph Explorer (`/graph-explorer`)

Visualizes the Neo4j knowledge graph using a force-directed layout. Features:

- Filter nodes by entity type
- Filter relationships by type
- Search nodes by name
- Click a node to see its properties
- Activate path finder to find the shortest path between two nodes
- Add, edit, and delete nodes and relationships directly from the UI

## State Management

The app uses three independent Zustand stores.

### workflowStore

Manages the workflow canvas state.

Key state:
- `nodes`: Array of `WorkflowNode` objects (extends ReactFlow `Node`)
- `edges`: Array of `WorkflowEdge` objects
- `selectedNode`: Currently selected node

Key methods:
- `addNode(node)`: Add a node to the canvas
- `updateNode(nodeId, updates)`: Update node data or config
- `deleteNode(nodeId)`: Remove a node and its connected edges
- `addEdge(connection)`: Connect two nodes
- `deleteEdge(edgeId)`: Remove a connection
- `validateWorkflow()`: Returns `{ valid, errors, nodeErrors }`. Checks for a single trigger node, cycle detection, required fields per node type, and valid context variable references
- `compileWorkflow(metadata)`: Produces the `WorkflowJSON` object for the backend
- `saveWorkflow(token, agentId, metadata)`: POST to `/api/workflows`
- `loadWorkflow(token, agentId)`: GET from `/api/workflows/{agentId}`
- `testWorkflow(token, testInput)`: POST to `/api/workflows/test`
- `exportWorkflow(metadata)`: Downloads the workflow as a JSON file
- `importWorkflow(file)`: Loads a workflow from a JSON file, remapping node IDs

### graphStore

Manages the knowledge graph explorer state.

Key state:
- `graphData`: `{ nodes, links }` for the force graph
- `selectedNode`, `selectedLink`: Currently selected graph elements
- `entityTypeFilter`, `relationshipTypeFilter`: Active filters
- `pathFinderActive`, `pathStartNode`, `pathEndNode`, `pathResult`: Path finder state

Key methods:
- `fetchGraphData(token, companyId)`: Load graph from backend
- `fetchGraphSchema(token, companyId)`: Load available entity and relationship types
- `findShortestPath(token, startNodeId, endNodeId)`: Execute path query
- `addNode`, `updateNode`, `deleteNode`, `addLink`, `updateLink`, `deleteLink`: CRUD operations that call the backend and update local state

### knowledgeStore

Manages document upload state.

Key state:
- `uploadJobs`: Map of `job_id` to `UploadJob` (status, progress, filename, collection)
- `collections`: List of Qdrant collections
- `isPolling`: Whether a polling interval is active

Key methods:
- `uploadFile(token, file, collectionName, companyId)`: POST to `/api/knowledge/upload`, returns `job_id`
- `startPolling(token, jobId, onComplete)`: Polls `/api/knowledge/upload/{jobId}/status` every 2 seconds until completion
- `stopPolling()`: Clears the polling interval
- `listCollections(token, companyId)`: GET `/api/knowledge/collections`

### historyStore

Manages undo/redo for the workflow canvas.

Key methods:
- `recordState(nodes, edges)`: Push current state to history
- `undo()`: Returns the previous state
- `redo()`: Returns the next state
- `clearHistory()`: Reset all history

## Components

### WorkflowCanvas

Wraps ReactFlow. Handles:
- Drag-and-drop from the node palette (via `onDrop` and `onDragOver`)
- Node selection (updates `workflowStore.selectedNode`)
- Edge creation (calls `workflowStore.addEdge`)
- Keyboard deletion of selected nodes and edges
- Rendering `ValidationErrorDisplay` overlays on nodes with errors
- Mini map and zoom controls

### NodePalette

Renders a list of draggable node type cards. Each card sets `dataTransfer` with the node type on drag start, which `WorkflowCanvas` reads on drop.

Node types available: Trigger, RAG, LLM, Tool, Action, Decision, Graph Query, Multi-Source RAG, Fallback.

### ConfigurationPanel

Renders the appropriate node config component based on `selectedNode.type`. Each config component (`RAGNodeConfig`, `LLMNodeConfig`, etc.) provides a form for editing the node's `config` object. The `VariableAutocomplete` component is used in prompt fields to suggest `{{variable}}` references from the current execution context.

### TestPanel

Provides a text input for a test message and a Run button. Calls `workflowStore.testWorkflow()` and displays the returned `node_logs` array showing each node's execution time and output.

### VoiceBuilder

Provides two modes:

- Text mode (default): Type a command and press Enter. The command is sent to `POST /api/voice-builder/parse-command`. The returned action is applied to the workflow canvas.
- Voice mode (optional): Requires Vapi configuration. Initializes the Vapi SDK lazily when the user switches to voice mode. Falls back to text mode on error.

Supported commands: add node, connect nodes, configure node, delete node, save workflow. Ambiguous commands return a clarification question.

### FileDropZone

Drag-and-drop file upload component. Accepts PDF, DOCX, TXT, CSV, and Markdown files. Calls `knowledgeStore.uploadFile()` and starts polling for status. Shows a progress bar per job.

### ValidationErrorDisplay

Renders error badges on nodes that failed validation. Positioned absolutely over the canvas using node coordinates from ReactFlow.

## Node Configuration Forms

Each node type has a dedicated configuration component in `components/node-configs/`:

| Component | Node Type | Key Fields |
|-----------|-----------|------------|
| `RAGNodeConfig` | rag | collection_name, query_template, result_limit, metadata_filters |
| `LLMNodeConfig` | llm | system_prompt, user_prompt, model, temperature, max_tokens |
| `ToolNodeConfig` | tool | api_endpoint, http_method, headers, request_body, timeout_ms |
| `ActionNodeConfig` | action | integration_type, action_name, parameters |
| `DecisionNodeConfig` | decision | classification_prompt, intents (name, description, threshold), fallback_intent |
| `GraphQueryNodeConfig` | graph_query | cypher_query, parameters |

`VariableAutocomplete` wraps any text input and shows a dropdown of available `{{variable}}` references based on the nodes that precede the current node in the workflow.

## Workflow JSON Format

The workflow is serialized as:

```json
{
  "version": "1.0.0",
  "metadata": {
    "workflow_name": "Customer Support Agent",
    "description": "Handles customer inquiries",
    "created_by": "user_id",
    "updated_at": "2026-04-17T00:00:00Z"
  },
  "nodes": [
    {
      "id": "trigger-1",
      "type": "trigger",
      "data": { "label": "Trigger", "config": {} },
      "position": { "x": 0, "y": 0 }
    },
    {
      "id": "rag-1",
      "type": "rag",
      "data": {
        "label": "Search Docs",
        "config": {
          "collection_name": "company_docs",
          "query_template": "{{trigger-1_output}}",
          "result_limit": 5
        }
      },
      "position": { "x": 200, "y": 0 }
    }
  ],
  "edges": [
    { "id": "e1", "source": "trigger-1", "target": "rag-1" }
  ]
}
```

Context variables use the `{{node_id_output}}` pattern and are resolved at execution time by the backend.

## Running Tests

```bash
cd frontend
npm test -- --run
```

Tests cover:
- `workflowStore`: node and edge CRUD, validation logic, workflow compilation
- `importExport`: JSON parsing, node ID remapping, edge reference updates

## Building for Production

```bash
npm run build
npm start
```

Or deploy to Vercel by connecting the repository. Set the environment variables in the Vercel project settings.
