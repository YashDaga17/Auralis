# Auralis Backend

FastAPI backend for the Auralis Visual Workflow Engine. A multi-tenant SaaS platform that powers custom voice agents through a visual workflow system.

## Overview

The backend handles workflow execution, knowledge management, graph database operations, voice command parsing, and user preferences. It integrates with Vapi for voice calls, Qdrant for vector search, Neo4j for knowledge graphs, and Google Gemini for AI inference.

## Tech Stack

- Python 3.11+
- FastAPI with Uvicorn
- PostgreSQL via SQLAlchemy (hosted on Supabase)
- Qdrant (vector database)
- Neo4j (graph database)
- Google Gemini 2.5 Flash (LLM and embeddings)
- Clerk / JWT (authentication)
- pytest (testing)

## Project Structure

```
backend/
├── main.py                     # FastAPI app entry point, CORS, Vapi webhook
├── database.py                 # PostgreSQL, Neo4j, Qdrant connections
├── models.py                   # SQLAlchemy ORM models
├── auth.py                     # JWT authentication and tenant isolation
├── workflow_schema.py          # Pydantic models for workflow JSON
├── workflow_validator.py       # DAG validation logic
├── workflow_execution.py       # Workflow execution engine
├── node_executors.py           # Node executor implementations
├── embedding_generator.py      # Gemini embedding generation
├── text_chunker.py             # Document chunking
├── file_parsers.py             # PDF, DOCX, TXT, CSV, Markdown parsers
├── triplet_extraction.py       # Entity-relationship extraction to Neo4j
├── knowledge_upload_pipeline.py # Document upload orchestration
├── qdrant_storage.py           # Qdrant vector storage interface
├── init_db.py                  # Database schema initialization
├── init_qdrant.py              # Qdrant collection initialization
├── requirements.txt
├── .env
├── tests.py                    # Consolidated test suite
└── routes/
    ├── workflows.py            # Workflow CRUD and execution API
    ├── knowledge.py            # Document upload and collection API
    ├── graph.py                # Graph schema and Cypher query API
    ├── voice_builder.py        # Voice command parsing API
    └── preferences.py          # User preferences API
```

## Setup

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env` and fill in your credentials:

```env
# PostgreSQL (Supabase)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key

# Authentication
JWT_SECRET=your_jwt_secret

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
```

### 3. Initialize databases

```bash
python init_db.py
python init_qdrant.py
```

### 4. Start the server

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Reference

### Vapi Webhook

```
POST /chat/completions
```

The primary entry point for Vapi voice calls. Accepts an OpenAI-compatible request body, loads the agent's workflow from the database, executes it, and streams the response back as Server-Sent Events (SSE).

Request body:
```json
{
  "call": { "assistantId": "agent_123" },
  "messages": [{ "role": "user", "content": "What are your pricing plans?" }],
  "metadata": { "company_id": "acme_corp", "user_id": "user_456" }
}
```

### Workflow API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/workflows` | Create or update a workflow for an agent |
| GET | `/api/workflows/{agent_id}` | Retrieve a workflow |
| GET | `/api/workflows/{agent_id}/versions` | List workflow version history |
| POST | `/api/workflows/test` | Test a workflow without saving |

### Knowledge API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/knowledge/upload` | Upload a document (PDF, DOCX, TXT, CSV, MD) |
| GET | `/api/knowledge/upload/{job_id}/status` | Poll upload job status |
| GET | `/api/knowledge/collections` | List all Qdrant collections |
| GET | `/api/knowledge/collections/{name}` | Get collection details |

### Graph API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge/graph/schema` | Get entity and relationship types |
| POST | `/api/knowledge/graph/query` | Execute a read-only Cypher query |

### Voice Builder API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/voice-builder/parse-command` | Parse a natural language command into a workflow action |
| GET | `/api/voice-builder/node-types` | Get available node type metadata |

### Preferences API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/preferences` | Create or update user preferences |
| GET | `/api/preferences/{user_id}` | Get preferences for a user |
| DELETE | `/api/preferences/{user_id}` | Delete user preferences |
| GET | `/api/preferences` | List all preferences |

### Health Checks

```
GET /health
GET /health/postgres
GET /health/neo4j
GET /health/qdrant
```

## Database Models

### Company
Multi-tenant organization. All data is scoped to a `company_id`.

### Agent
Stores the workflow JSON for a voice agent. Maps to a Vapi `assistantId`.

### WorkflowVersion
Immutable version history for every workflow save.

### ConversationHistory
Stores each conversation turn with extracted entities, intent, and confidence score. Used to provide context in subsequent calls within a 30-minute session window.

### UserPreference
Per-user personalization settings:
- `communication_style`: `concise`, `detailed`, or `technical`
- `preferred_sources`: List of Qdrant collection names to prioritize
- `notification_preferences`: Email, SMS, and in-app notification settings
- `agent_id`: Optional — allows agent-specific preferences alongside general ones

### ExecutionMetric
Tracks node-level execution timing for performance monitoring.

## Workflow Execution Engine

The execution engine (`workflow_execution.py`) processes a workflow JSON through these steps:

1. Parse the workflow JSON and validate the schema
2. Build a directed acyclic graph (DAG) from nodes and edges
3. Topological sort with level grouping for parallel execution
4. Load conversation history from the database (30-minute window)
5. Load user preferences and inject into session context
6. Execute nodes level by level, running nodes in the same level in parallel via `asyncio.gather`
7. Resolve `{{variable}}` context references between nodes
8. On node failure, route to a connected fallback node if one exists
9. Extract entities from the user message and save the conversation turn

## Node Types

### Trigger
Entry point for every workflow. Captures the user's transcript and stores it as `{node_id}_output` in the execution context.

### RAG
Generates an embedding for the query using Gemini `text-embedding-004`, then searches a Qdrant collection. Results are concatenated and stored in context. Supports metadata filters and configurable result limits. Collection names are namespaced by `company_id` for tenant isolation.

### LLM
Calls Gemini 2.5 Flash with a system prompt and user prompt. Supports configurable temperature and max tokens. Adapts response verbosity based on the user's `communication_style` preference.

### Tool
Makes HTTP requests to external APIs. Supports GET, POST, PUT, PATCH, DELETE. Handles JSON and plain text responses. Raises typed errors for HTTP failures, timeouts, and connection errors.

### Decision
Classifies user intent using an LLM call. Returns the matched intent name and stores confidence in context. Routes to the appropriate downstream node based on the classified intent. Falls back to a configured `fallback_intent` when confidence is below threshold.

### Action
Executes business integrations: HubSpot (create/update contacts), Calendly (schedule events), Zendesk (create tickets), Salesforce (update records). Parameters are resolved from the execution context.

### Graph Query
Executes a read-only Cypher query against Neo4j. Automatically injects `company_id` as a parameter for tenant isolation. Enforces a 5-second timeout.

### Multi-Source RAG
Searches multiple Qdrant collections simultaneously. Supports per-collection weighting. Merges and re-ranks results. Boosts collections listed in the user's `preferred_sources`.

### Fallback
Error recovery node. Receives error type, message, and timestamp in context. Used to return a graceful response when an upstream node fails.

## Knowledge Upload Pipeline

When a document is uploaded:

1. File content is parsed based on type (PDF via PyMuPDF, DOCX via python-docx, CSV, TXT, Markdown)
2. Text is split into overlapping chunks
3. Each chunk is embedded using Gemini `text-embedding-004`
4. Embeddings are stored in Qdrant under a `{company_id}_{collection_name}` namespace
5. Entity-relationship triplets are extracted from the text using Gemini and inserted into Neo4j
6. Job status is tracked and available via the status polling endpoint

## Voice Builder

The voice builder endpoint accepts a natural language transcript and returns a structured workflow action. It uses Gemini to parse commands like:

- "Add a RAG node that searches the customer database" -> `add_node` action
- "Connect the trigger to the RAG node" -> `connect_nodes` action
- "Set the LLM temperature to 0.9" -> `configure_node` action
- "Save the workflow as Customer Support Agent" -> `save_workflow` action

When a command is ambiguous, the response includes `requires_clarification: true` and a `clarification_question`.

## Multi-Tenancy

Every database query, Qdrant search, and Neo4j query is scoped to the authenticated user's `company_id`. The `AuthContext` is extracted from the JWT token on every request. Qdrant collections are namespaced as `{company_id}_{collection_name}`. Neo4j nodes include a `company_id` property that is injected into all queries.

## Running Tests

```bash
cd backend
pytest tests.py -v
```

The test suite covers:
- Node executor registry and base class behavior
- RAG executor: tenant isolation, embedding generation, result formatting
- LLM executor: prompt construction, parameter defaults, error handling
- Tool executor: all HTTP methods, error types, timeout handling
- Decision executor: intent classification, confidence thresholds, JSON parsing
- Workflow schema validation: required fields, node types, DAG structure
- Workflow API: validation enforcement, execution log structure
- Knowledge API: file upload, status polling, collection listing
- Graph API: schema endpoint, read-only query enforcement, Cypher validation
- Conversation memory: storage, retrieval, time window filtering, entity aggregation
- User preferences: CRUD operations, tenant isolation, personalization logic
- Vapi integration: SSE streaming format, OpenAI-compatible response structure
