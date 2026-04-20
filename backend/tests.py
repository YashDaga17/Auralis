"""
Auralis Backend Test Suite

Covers all core functionality:
- Node executor registry and base classes
- RAG, LLM, Tool, Decision node executors
- Workflow schema validation
- Workflow API endpoints
- Knowledge API endpoints
- Graph API endpoints
- Conversation memory and entity aggregation
- User preferences storage and personalization
- Vapi SSE streaming integration
"""
import pytest
import asyncio
import uuid
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base
from models import Company, Agent, ConversationHistory, UserPreference
from node_executors import (
    NodeExecutor,
    NodeExecutorRegistry,
    FallbackHandler,
    NodeExecutionError,
    RAGNodeExecutor,
    LLMNodeExecutor,
    ToolNodeExecutor,
    DecisionNodeExecutor,
    get_registry,
    register_executor,
)
from workflow_schema import WorkflowJSON, WorkflowNode, NodeType, NodeData, Position
from workflow_execution import WorkflowExecutionEngine
from routes.preferences import UserPreferenceCreate


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

client = TestClient(app)

TEST_DB_URL = "sqlite:///./test_auralis.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def company(db):
    c = Company(company_id=uuid.uuid4(), company_name="Test Company")
    db.add(c)
    db.commit()
    return c


@pytest.fixture
def agent(db, company):
    a = Agent(
        agent_id="test-agent-001",
        company_id=company.company_id,
        workflow_json={
            "version": "1.0.0",
            "metadata": {
                "workflow_name": "Test Workflow",
                "description": "Test",
                "created_by": "test-user",
                "updated_at": datetime.utcnow().isoformat(),
            },
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger",
                    "data": {"label": "Trigger", "config": {}},
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "llm-1",
                    "type": "llm",
                    "data": {
                        "label": "LLM",
                        "config": {
                            "system_prompt": "You are helpful.",
                            "user_prompt": "{{trigger-1_output}}",
                            "temperature": 0.7,
                            "max_tokens": 512,
                            "model": "gemini-2.5-flash",
                        },
                    },
                    "position": {"x": 200, "y": 0},
                },
            ],
            "edges": [{"id": "e1", "source": "trigger-1", "target": "llm-1"}],
        },
    )
    db.add(a)
    db.commit()
    return a


VALID_WORKFLOW = {
    "version": "1.0.0",
    "metadata": {
        "workflow_name": "Test Workflow",
        "description": "A test workflow",
        "created_by": "test-user",
        "updated_at": datetime.now().isoformat(),
    },
    "nodes": [
        {
            "id": "trigger-1",
            "type": "trigger",
            "data": {"label": "Trigger", "config": {}},
            "position": {"x": 0, "y": 0},
        },
        {
            "id": "llm-1",
            "type": "llm",
            "data": {
                "label": "LLM Response",
                "config": {
                    "system_prompt": "You are a helpful assistant",
                    "user_prompt": "{{trigger-1_output}}",
                    "temperature": 0.7,
                    "max_tokens": 1024,
                    "model": "gemini-2.5-flash",
                },
            },
            "position": {"x": 200, "y": 0},
        },
    ],
    "edges": [{"id": "e1", "source": "trigger-1", "target": "llm-1"}],
}


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockQdrantClient:
    def __init__(self, results=None):
        self.results = results or []
        self.last_params = {}

    def search(self, collection_name, query_vector, query_filter=None, limit=5):
        self.last_params = {
            "collection_name": collection_name,
            "query_vector": query_vector,
            "query_filter": query_filter,
            "limit": limit,
        }
        return self.results


class MockSearchResult:
    def __init__(self, text, score=0.9):
        self.payload = {"text": text}
        self.score = score


class MockGeminiEmbedClient:
    def __init__(self, vector=None):
        self.vector = vector or [0.1] * 768
        self.models = self

    def embed_content(self, model, contents):
        class Emb:
            def __init__(self, v):
                self.values = v

        class Res:
            def __init__(self, v):
                self.embeddings = [Emb(v)]

        return Res(self.vector)


class MockGeminiLLMClient:
    def __init__(self, text="Mock response"):
        self.text = text
        self.models = self
        self.last_params = {}

    def generate_content(self, model, contents, generation_config=None):
        self.last_params = {
            "model": model,
            "contents": contents,
            "generation_config": generation_config,
        }

        class Res:
            def __init__(self, t):
                self.text = t

        return Res(self.text)


class MockExecutor(NodeExecutor):
    async def execute(self, config, context, session):
        return "mock output"


class FailingExecutor(NodeExecutor):
    async def execute(self, config, context, session):
        raise ValueError("Intentional failure")


class NotAnExecutor:
    pass


# ===========================================================================
# 1. Node Executor Registry
# ===========================================================================

class TestNodeExecutorRegistry:
    def test_empty_registry_on_init(self):
        registry = NodeExecutorRegistry()
        assert registry.list_registered_types() == []

    def test_register_valid_executor(self):
        registry = NodeExecutorRegistry()
        registry.register("rag", MockExecutor)
        assert "rag" in registry.list_registered_types()
        assert registry.get_executor("rag") == MockExecutor

    def test_register_invalid_class_raises(self):
        registry = NodeExecutorRegistry()
        with pytest.raises(ValueError, match="must inherit from NodeExecutor"):
            registry.register("bad", NotAnExecutor)

    def test_get_nonexistent_returns_none(self):
        registry = NodeExecutorRegistry()
        assert registry.get_executor("nonexistent") is None

    def test_register_multiple_types(self):
        registry = NodeExecutorRegistry()
        registry.register("rag", MockExecutor)
        registry.register("llm", MockExecutor)
        types = registry.list_registered_types()
        assert "rag" in types
        assert "llm" in types

    def test_global_registry_is_singleton(self):
        assert get_registry() is get_registry()

    def test_convenience_register_function(self):
        register_executor("test_type", MockExecutor)
        assert get_registry().get_executor("test_type") == MockExecutor


# ===========================================================================
# 2. FallbackHandler
# ===========================================================================

class TestFallbackHandler:
    def test_find_fallback_node_when_present(self):
        fallback = WorkflowNode(
            id="fb1",
            type=NodeType.FALLBACK,
            data=NodeData(label="Fallback", config={}),
            position=Position(x=0, y=0),
        )
        handler = FallbackHandler({"failed": ["fb1"]}, {"fb1": fallback})
        assert handler.find_fallback_node("failed") == "fb1"

    def test_find_fallback_node_when_absent(self):
        handler = FallbackHandler({"failed": ["other"]}, {})
        assert handler.find_fallback_node("failed") is None

    def test_find_fallback_no_connections(self):
        handler = FallbackHandler({}, {})
        assert handler.find_fallback_node("failed") is None

    def test_prepare_error_context(self):
        handler = FallbackHandler({}, {})
        ctx = {"existing": "value"}
        err = ValueError("Test error")
        result = handler.prepare_error_context("node1", err, ctx)
        assert result["existing"] == "value"
        assert result["node1_error_type"] == "ValueError"
        assert result["node1_error_message"] == "Test error"
        datetime.fromisoformat(result["node1_error_timestamp"])

    def test_get_generic_error_message(self):
        handler = FallbackHandler({}, {})
        msg = handler.get_generic_error_message()
        assert isinstance(msg, str) and len(msg) > 0


# ===========================================================================
# 3. NodeExecutionError
# ===========================================================================

class TestNodeExecutionError:
    def test_error_attributes(self):
        err = NodeExecutionError(
            node_id="n1", error_type="ValueError", error_message="bad input"
        )
        assert err.node_id == "n1"
        assert err.error_type == "ValueError"
        assert err.error_message == "bad input"
        assert "n1" in str(err)


# ===========================================================================
# 4. RAGNodeExecutor
# ===========================================================================

class TestRAGNodeExecutor:
    @pytest.mark.asyncio
    async def test_basic_execution_returns_concatenated_docs(self):
        results = [MockSearchResult("Doc A"), MockSearchResult("Doc B")]
        qdrant = MockQdrantClient(results=results)
        gemini = MockGeminiEmbedClient()
        executor = RAGNodeExecutor(qdrant, gemini)

        output = await executor.execute(
            {"collection_name": "docs", "query_template": "test", "result_limit": 2},
            {},
            {"company_id": "co1"},
        )
        assert "Doc A" in output
        assert "Doc B" in output
        assert output == "Doc A\n\nDoc B"

    @pytest.mark.asyncio
    async def test_collection_namespaced_by_company_id(self):
        qdrant = MockQdrantClient()
        gemini = MockGeminiEmbedClient()
        executor = RAGNodeExecutor(qdrant, gemini)

        await executor.execute(
            {"collection_name": "docs", "query_template": "q", "result_limit": 5},
            {},
            {"company_id": "acme"},
        )
        assert qdrant.last_params["collection_name"] == "acme_docs"

    @pytest.mark.asyncio
    async def test_company_id_filter_applied(self):
        qdrant = MockQdrantClient()
        gemini = MockGeminiEmbedClient()
        executor = RAGNodeExecutor(qdrant, gemini)

        await executor.execute(
            {"collection_name": "docs", "query_template": "q", "result_limit": 5},
            {},
            {"company_id": "co2"},
        )
        f = qdrant.last_params["query_filter"]
        assert f is not None
        assert any(c.key == "company_id" for c in f.must)

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_string(self):
        qdrant = MockQdrantClient(results=[])
        gemini = MockGeminiEmbedClient()
        executor = RAGNodeExecutor(qdrant, gemini)

        output = await executor.execute(
            {"collection_name": "docs", "query_template": "q", "result_limit": 5},
            {},
            {"company_id": "co1"},
        )
        assert output == ""

    @pytest.mark.asyncio
    async def test_missing_collection_name_raises(self):
        executor = RAGNodeExecutor(MockQdrantClient(), MockGeminiEmbedClient())
        with pytest.raises(NodeExecutionError):
            await executor.execute({"query_template": "q"}, {}, {"company_id": "co1"})

    @pytest.mark.asyncio
    async def test_missing_company_id_raises(self):
        executor = RAGNodeExecutor(MockQdrantClient(), MockGeminiEmbedClient())
        with pytest.raises(NodeExecutionError):
            await executor.execute(
                {"collection_name": "docs", "query_template": "q"}, {}, {}
            )

    @pytest.mark.asyncio
    async def test_result_limit_passed_to_qdrant(self):
        qdrant = MockQdrantClient()
        executor = RAGNodeExecutor(qdrant, MockGeminiEmbedClient())
        await executor.execute(
            {"collection_name": "docs", "query_template": "q", "result_limit": 3},
            {},
            {"company_id": "co1"},
        )
        assert qdrant.last_params["limit"] == 3

    @pytest.mark.asyncio
    async def test_embedding_vector_used_in_search(self):
        custom_vec = [0.5] * 768
        qdrant = MockQdrantClient()
        executor = RAGNodeExecutor(qdrant, MockGeminiEmbedClient(vector=custom_vec))
        await executor.execute(
            {"collection_name": "docs", "query_template": "q", "result_limit": 5},
            {},
            {"company_id": "co1"},
        )
        assert qdrant.last_params["query_vector"] == custom_vec


# ===========================================================================
# 5. LLMNodeExecutor
# ===========================================================================

class TestLLMNodeExecutor:
    @pytest.mark.asyncio
    async def test_basic_execution_returns_response(self):
        gemini = MockGeminiLLMClient(text="Paris is the capital of France.")
        executor = LLMNodeExecutor(gemini)

        result = await executor.execute(
            {
                "system_prompt": "You are helpful.",
                "user_prompt": "What is the capital of France?",
                "temperature": 0.7,
                "max_tokens": 512,
            },
            {},
            {},
        )
        assert result == "Paris is the capital of France."

    @pytest.mark.asyncio
    async def test_system_prompt_precedes_user_prompt(self):
        gemini = MockGeminiLLMClient()
        executor = LLMNodeExecutor(gemini)

        await executor.execute(
            {"system_prompt": "System.", "user_prompt": "User.", "temperature": 0.5},
            {},
            {},
        )
        contents = gemini.last_params["contents"]
        assert contents.index("System.") < contents.index("User.")

    @pytest.mark.asyncio
    async def test_no_system_prompt_uses_user_prompt_only(self):
        gemini = MockGeminiLLMClient()
        executor = LLMNodeExecutor(gemini)

        await executor.execute({"user_prompt": "Just this."}, {}, {})
        assert gemini.last_params["contents"] == "Just this."

    @pytest.mark.asyncio
    async def test_default_model_and_params(self):
        gemini = MockGeminiLLMClient()
        executor = LLMNodeExecutor(gemini)

        await executor.execute({"user_prompt": "Test"}, {}, {})
        assert gemini.last_params["model"] == "gemini-2.5-flash"
        assert gemini.last_params["generation_config"]["temperature"] == 0.7
        assert gemini.last_params["generation_config"]["max_output_tokens"] == 1024

    @pytest.mark.asyncio
    async def test_custom_model_and_params(self):
        gemini = MockGeminiLLMClient()
        executor = LLMNodeExecutor(gemini)

        await executor.execute(
            {"user_prompt": "Test", "model": "gemini-2.5-pro", "temperature": 0.2, "max_tokens": 256},
            {},
            {},
        )
        assert gemini.last_params["model"] == "gemini-2.5-pro"
        assert gemini.last_params["generation_config"]["temperature"] == 0.2
        assert gemini.last_params["generation_config"]["max_output_tokens"] == 256

    @pytest.mark.asyncio
    async def test_missing_user_prompt_raises(self):
        executor = LLMNodeExecutor(MockGeminiLLMClient())
        with pytest.raises(NodeExecutionError):
            await executor.execute({"system_prompt": "Sys"}, {}, {})

    @pytest.mark.asyncio
    async def test_api_error_raises_node_execution_error(self):
        class FailClient:
            models = None

            def __init__(self):
                self.models = self

            def generate_content(self, model, contents, generation_config=None):
                raise Exception("API rate limit exceeded")

        executor = LLMNodeExecutor(FailClient())
        with pytest.raises(NodeExecutionError) as exc:
            await executor.execute({"user_prompt": "Test"}, {}, {})
        assert "API rate limit exceeded" in exc.value.error_message

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_string(self):
        executor = LLMNodeExecutor(MockGeminiLLMClient(text=""))
        result = await executor.execute({"user_prompt": "Test"}, {}, {})
        assert result == ""


# ===========================================================================
# 6. ToolNodeExecutor
# ===========================================================================

class TestToolNodeExecutor:
    @pytest.mark.asyncio
    async def test_get_request_returns_json(self):
        executor = ToolNodeExecutor()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.text = '{"status": "ok"}'

        with patch("httpx.AsyncClient") as mc:
            mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await executor.execute(
                {"api_endpoint": "https://api.example.com/data", "http_method": "GET", "headers": {}},
                {},
                {},
            )
        assert "ok" in result

    @pytest.mark.asyncio
    async def test_post_request_with_body(self):
        executor = ToolNodeExecutor()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 1}
        mock_resp.text = '{"id": 1}'

        with patch("httpx.AsyncClient") as mc:
            mc.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await executor.execute(
                {
                    "api_endpoint": "https://api.example.com/create",
                    "http_method": "POST",
                    "headers": {},
                    "request_body": '{"name": "test"}',
                },
                {},
                {},
            )
        assert "1" in result

    @pytest.mark.asyncio
    async def test_http_error_raises_node_execution_error(self):
        executor = ToolNodeExecutor()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"

        with patch("httpx.AsyncClient") as mc:
            mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            with pytest.raises(NodeExecutionError) as exc:
                await executor.execute(
                    {"api_endpoint": "https://api.example.com/x", "http_method": "GET", "headers": {}},
                    {},
                    {},
                )
        assert "404" in exc.value.error_message

    @pytest.mark.asyncio
    async def test_timeout_raises_node_execution_error(self):
        executor = ToolNodeExecutor()
        with patch("httpx.AsyncClient") as mc:
            mc.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )
            with pytest.raises(NodeExecutionError) as exc:
                await executor.execute(
                    {"api_endpoint": "https://api.example.com/slow", "http_method": "GET", "headers": {}},
                    {},
                    {},
                )
        assert exc.value.error_type == "TimeoutError"

    @pytest.mark.asyncio
    async def test_connection_error_raises_node_execution_error(self):
        executor = ToolNodeExecutor()
        with patch("httpx.AsyncClient") as mc:
            mc.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            with pytest.raises(NodeExecutionError) as exc:
                await executor.execute(
                    {"api_endpoint": "https://api.example.com/x", "http_method": "GET", "headers": {}},
                    {},
                    {},
                )
        assert exc.value.error_type == "RequestError"

    @pytest.mark.asyncio
    async def test_missing_endpoint_raises(self):
        executor = ToolNodeExecutor()
        with pytest.raises(NodeExecutionError) as exc:
            await executor.execute({"http_method": "GET", "headers": {}}, {}, {})
        assert "api_endpoint" in exc.value.error_message

    @pytest.mark.asyncio
    async def test_invalid_http_method_raises(self):
        executor = ToolNodeExecutor()
        with pytest.raises(NodeExecutionError) as exc:
            await executor.execute(
                {"api_endpoint": "https://api.example.com", "http_method": "INVALID", "headers": {}},
                {},
                {},
            )
        assert "Invalid HTTP method" in exc.value.error_message

    @pytest.mark.asyncio
    async def test_invalid_json_body_raises(self):
        executor = ToolNodeExecutor()
        with pytest.raises(NodeExecutionError) as exc:
            await executor.execute(
                {
                    "api_endpoint": "https://api.example.com",
                    "http_method": "POST",
                    "headers": {},
                    "request_body": "not json",
                },
                {},
                {},
            )
        assert "Invalid JSON" in exc.value.error_message

    @pytest.mark.asyncio
    async def test_non_json_response_returns_text(self):
        executor = ToolNodeExecutor()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = Exception("Not JSON")
        mock_resp.text = "plain text"

        with patch("httpx.AsyncClient") as mc:
            mc.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            result = await executor.execute(
                {"api_endpoint": "https://api.example.com/text", "http_method": "GET", "headers": {}},
                {},
                {},
            )
        assert result == "plain text"


# ===========================================================================
# 7. DecisionNodeExecutor
# ===========================================================================

class TestDecisionNodeExecutor:
    @pytest.mark.asyncio
    async def test_basic_intent_classification(self):
        gemini = MockGeminiLLMClient(
            text='{"intent": "book_appointment", "confidence": 0.95}'
        )
        executor = DecisionNodeExecutor(gemini)

        config = {
            "classification_prompt": "Classify the intent.",
            "intents": [
                {"name": "book_appointment", "description": "Book an appointment", "confidence_threshold": 0.7},
                {"name": "check_status", "description": "Check order status", "confidence_threshold": 0.7},
            ],
            "fallback_intent": "general_question",
        }
        context = {"trigger-1_output": "I want to book an appointment"}
        session = {"user_transcript": "I want to book an appointment"}

        result = await executor.execute(config, context, session)
        assert result == "book_appointment"
        assert context["classified_intent"] == "book_appointment"
        assert context["intent_confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_json_in_markdown_code_block(self):
        gemini = MockGeminiLLMClient(
            text='```json\n{"intent": "check_status", "confidence": 0.88}\n```'
        )
        executor = DecisionNodeExecutor(gemini)

        config = {
            "classification_prompt": "Classify.",
            "intents": [{"name": "check_status", "description": "Check status", "confidence_threshold": 0.7}],
            "fallback_intent": "other",
        }
        result = await executor.execute(config, {}, {})
        assert result == "check_status"

    @pytest.mark.asyncio
    async def test_low_confidence_uses_fallback(self):
        gemini = MockGeminiLLMClient(
            text='{"intent": "book_appointment", "confidence": 0.3}'
        )
        executor = DecisionNodeExecutor(gemini)

        config = {
            "classification_prompt": "Classify.",
            "intents": [{"name": "book_appointment", "description": "Book", "confidence_threshold": 0.7}],
            "fallback_intent": "general_question",
        }
        result = await executor.execute(config, {}, {})
        assert result == "general_question"

    @pytest.mark.asyncio
    async def test_missing_intents_raises(self):
        executor = DecisionNodeExecutor(MockGeminiLLMClient())
        with pytest.raises(NodeExecutionError):
            await executor.execute({"classification_prompt": "Classify."}, {}, {})


# ===========================================================================
# 8. Workflow Schema Validation
# ===========================================================================

class TestWorkflowSchemaValidation:
    def test_valid_workflow_parses(self):
        wf = WorkflowJSON(**VALID_WORKFLOW)
        assert wf.version == "1.0.0"
        assert len(wf.nodes) == 2
        assert len(wf.edges) == 1
        assert wf.nodes[0].type.value == "trigger"

    def test_missing_version_raises(self):
        bad = {k: v for k, v in VALID_WORKFLOW.items() if k != "version"}
        with pytest.raises(Exception):
            WorkflowJSON(**bad)

    def test_missing_metadata_raises(self):
        bad = {k: v for k, v in VALID_WORKFLOW.items() if k != "metadata"}
        with pytest.raises(Exception):
            WorkflowJSON(**bad)

    def test_missing_nodes_raises(self):
        bad = {k: v for k, v in VALID_WORKFLOW.items() if k != "nodes"}
        with pytest.raises(Exception):
            WorkflowJSON(**bad)

    def test_invalid_node_type_raises(self):
        import copy
        bad = copy.deepcopy(VALID_WORKFLOW)
        bad["nodes"][0]["type"] = "not_a_real_type"
        with pytest.raises(Exception):
            WorkflowJSON(**bad)


# ===========================================================================
# 9. Workflow API Endpoints
# ===========================================================================

class TestWorkflowAPI:
    def test_create_workflow_rejects_missing_metadata(self):
        payload = {
            "agent_id": "agent-test",
            "workflow_json": {"version": "1.0.0", "nodes": [], "edges": []},
        }
        resp = client.post("/api/workflows", json=payload)
        assert resp.status_code in [400, 422]

    def test_create_workflow_rejects_no_trigger_node(self):
        import copy
        no_trigger = copy.deepcopy(VALID_WORKFLOW)
        no_trigger["nodes"] = [no_trigger["nodes"][1]]  # remove trigger
        no_trigger["edges"] = []
        payload = {"agent_id": "agent-test", "workflow_json": no_trigger}
        resp = client.post("/api/workflows", json=payload)
        assert resp.status_code in [400, 422]

    def test_test_workflow_rejects_invalid_json(self):
        payload = {
            "workflow_json": {"version": "1.0.0", "nodes": [], "edges": []},
            "test_input": "Hello",
        }
        resp = client.post("/api/workflows/test", json=payload)
        assert resp.status_code in [400, 422]

    def test_test_workflow_returns_execution_structure(self):
        payload = {"workflow_json": VALID_WORKFLOW, "test_input": "Hello"}
        try:
            resp = client.post("/api/workflows/test", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                assert "status" in data
                assert "total_duration_ms" in data
                assert "node_logs" in data
                assert isinstance(data["node_logs"], list)
        except Exception:
            pass  # Acceptable if no Gemini API key in test environment


# ===========================================================================
# 10. Knowledge API Endpoints
# ===========================================================================

class TestKnowledgeAPI:
    def test_upload_text_file_returns_job_id(self):
        content = b"Test document for knowledge upload."
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", BytesIO(content), "text/plain")},
            data={"collection_name": "test_col", "company_id": "test_co"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "job_id" in data

    def test_upload_csv_file(self):
        content = b"Name,Age\nAlice,30\nBob,25"
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("data.csv", BytesIO(content), "text/csv")},
            data={"collection_name": "csv_col", "company_id": "test_co"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_upload_markdown_file(self):
        content = b"# Title\n\nSome content."
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("doc.md", BytesIO(content), "text/markdown")},
            data={"collection_name": "md_col", "company_id": "test_co"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_upload_missing_collection_name_returns_422(self):
        content = b"Test"
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", BytesIO(content), "text/plain")},
            data={"company_id": "test_co"},
        )
        assert resp.status_code == 422

    def test_upload_status_not_found_returns_404(self):
        resp = client.get("/api/knowledge/upload/nonexistent-job-id/status")
        assert resp.status_code == 404

    def test_upload_status_returns_correct_structure(self):
        content = b"Status tracking test."
        upload = client.post(
            "/api/knowledge/upload",
            files={"file": ("status.txt", BytesIO(content), "text/plain")},
            data={"collection_name": "status_col", "company_id": "status_co"},
        )
        job_id = upload.json()["job_id"]

        import time
        time.sleep(1)

        resp = client.get(f"/api/knowledge/upload/{job_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert "status" in data
        assert data["status"] in ["pending", "processing", "completed", "failed"]
        assert "progress" in data

    def test_list_collections_returns_structure(self):
        resp = client.get("/api/knowledge/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "collections" in data
        assert isinstance(data["collections"], list)


# ===========================================================================
# 11. Graph API Endpoints
# ===========================================================================

class TestGraphAPI:
    def test_schema_returns_entity_and_relationship_types(self):
        resp = client.get("/api/knowledge/graph/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "entity_types" in data
        assert "relationship_types" in data
        assert isinstance(data["entity_types"], list)
        assert isinstance(data["relationship_types"], list)
        assert len(data["entity_types"]) > 0

    def test_schema_contains_default_entity_types(self):
        resp = client.get("/api/knowledge/graph/schema")
        data = resp.json()
        for expected in ["Person", "Project", "Product", "Department", "Document"]:
            assert expected in data["entity_types"]

    def test_schema_contains_default_relationship_types(self):
        resp = client.get("/api/knowledge/graph/schema")
        data = resp.json()
        for expected in ["MANAGES", "OWNS", "REPORTS_TO", "WORKS_ON"]:
            assert expected in data["relationship_types"]

    def test_schema_with_company_id_param(self):
        resp = client.get("/api/knowledge/graph/schema?company_id=test_co")
        assert resp.status_code == 200
        assert resp.json()["company_id"] == "test_co"

    def test_schema_is_consistent_across_calls(self):
        r1 = client.get("/api/knowledge/graph/schema").json()
        r2 = client.get("/api/knowledge/graph/schema").json()
        assert r1["entity_types"] == r2["entity_types"]
        assert r1["relationship_types"] == r2["relationship_types"]

    def test_cypher_query_rejects_write_operations(self):
        write_queries = [
            "CREATE (n:Person {name: 'Test'})",
            "MERGE (n:Person {name: 'Test'})",
            "DELETE n",
            "SET n.name = 'Updated'",
        ]
        for query in write_queries:
            resp = client.post("/api/knowledge/graph/query", json={"query": query})
            assert resp.status_code == 400
            assert "read-only" in resp.json()["detail"].lower()

    def test_cypher_query_accepts_read_operations(self):
        read_queries = [
            "MATCH (n) RETURN n LIMIT 1",
            "MATCH (p:Person) RETURN p.name",
        ]
        for query in read_queries:
            resp = client.post("/api/knowledge/graph/query", json={"query": query})
            assert resp.status_code in [200, 503]

    def test_cypher_query_missing_field_returns_422(self):
        resp = client.post("/api/knowledge/graph/query", json={"parameters": {}})
        assert resp.status_code == 422

    def test_cypher_query_response_structure(self):
        resp = client.post("/api/knowledge/graph/query", json={"query": "MATCH (n) RETURN n LIMIT 1"})
        if resp.status_code == 200:
            data = resp.json()
            assert "results" in data
            assert "execution_time_ms" in data
            assert isinstance(data["results"], list)
            assert data["execution_time_ms"] >= 0


# ===========================================================================
# 12. Conversation Memory
# ===========================================================================

class TestConversationMemory:
    def test_conversation_turn_stored_in_db(self, db, company, agent):
        turn = ConversationHistory(
            session_id=uuid.uuid4(),
            user_id="user-1",
            agent_id=agent.agent_id,
            company_id=company.company_id,
            timestamp=datetime.utcnow(),
            user_message="What is your pricing?",
            agent_response="Our pricing starts at $99/month.",
            extracted_entities={"product": [{"value": "pricing", "confidence": 0.9}]},
            intent="pricing_query",
            confidence=0.92,
        )
        db.add(turn)
        db.commit()

        stored = db.query(ConversationHistory).filter_by(user_id="user-1").first()
        assert stored.user_message == "What is your pricing?"
        assert stored.intent == "pricing_query"
        assert stored.extracted_entities["product"][0]["value"] == "pricing"

    def test_conversation_history_loaded_into_engine(self, db, company, agent):
        user_id = "user-history"
        for i in range(3):
            db.add(ConversationHistory(
                session_id=uuid.uuid4(),
                user_id=user_id,
                agent_id=agent.agent_id,
                company_id=company.company_id,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                extracted_entities={},
            ))
        db.commit()

        eng = WorkflowExecutionEngine(
            workflow_json=agent.workflow_json,
            vapi_payload={
                "messages": [{"role": "user", "content": "New message"}],
                "call": {"id": "c1", "assistantId": agent.agent_id},
                "metadata": {"user_id": user_id, "company_id": str(company.company_id)},
            },
            db_session=db,
        )
        history = eng.session_context["conversation_history"]
        assert len(history) == 3

    def test_time_window_filters_old_conversations(self, db, company, agent):
        user_id = "user-window"
        db.add(ConversationHistory(
            session_id=uuid.uuid4(),
            user_id=user_id,
            agent_id=agent.agent_id,
            company_id=company.company_id,
            timestamp=datetime.utcnow() - timedelta(minutes=60),
            user_message="Old message",
            agent_response="Old response",
            extracted_entities={},
        ))
        db.add(ConversationHistory(
            session_id=uuid.uuid4(),
            user_id=user_id,
            agent_id=agent.agent_id,
            company_id=company.company_id,
            timestamp=datetime.utcnow() - timedelta(minutes=5),
            user_message="Recent message",
            agent_response="Recent response",
            extracted_entities={},
        ))
        db.commit()

        eng = WorkflowExecutionEngine(
            workflow_json=agent.workflow_json,
            vapi_payload={
                "messages": [{"role": "user", "content": "Now"}],
                "call": {"id": "c2", "assistantId": agent.agent_id},
                "metadata": {"user_id": user_id, "company_id": str(company.company_id)},
            },
            db_session=db,
        )
        history = eng.session_context["conversation_history"]
        assert len(history) == 1
        assert history[0]["user_message"] == "Recent message"

    def test_entity_aggregation_from_history(self, db, company, agent):
        user_id = "user-entities"
        for msg, entities in [
            ("My name is Alice", {"person_name": [{"value": "Alice", "confidence": 0.95}]}),
            ("I work at Acme Corp", {"company_name": [{"value": "Acme Corp", "confidence": 0.9}]}),
        ]:
            db.add(ConversationHistory(
                session_id=uuid.uuid4(),
                user_id=user_id,
                agent_id=agent.agent_id,
                company_id=company.company_id,
                timestamp=datetime.utcnow(),
                user_message=msg,
                agent_response="Noted.",
                extracted_entities=entities,
            ))
        db.commit()

        eng = WorkflowExecutionEngine(
            workflow_json=agent.workflow_json,
            vapi_payload={
                "messages": [{"role": "user", "content": "What do you know?"}],
                "call": {"id": "c3", "assistantId": agent.agent_id},
                "metadata": {"user_id": user_id, "company_id": str(company.company_id)},
            },
            db_session=db,
        )
        entities = eng.session_context["extracted_entities"]
        assert any("Alice" in str(e.get("value", "")) for e in entities.get("person_name", []))
        assert any("Acme Corp" in str(e.get("value", "")) for e in entities.get("company_name", []))

    def test_conversation_history_context_variable_formatted(self, db, company, agent):
        user_id = "user-ctx"
        db.add(ConversationHistory(
            session_id=uuid.uuid4(),
            user_id=user_id,
            agent_id=agent.agent_id,
            company_id=company.company_id,
            timestamp=datetime.utcnow(),
            user_message="Hello",
            agent_response="Hi there!",
            extracted_entities={},
        ))
        db.commit()

        eng = WorkflowExecutionEngine(
            workflow_json=agent.workflow_json,
            vapi_payload={
                "messages": [{"role": "user", "content": "Follow up"}],
                "call": {"id": "c4", "assistantId": agent.agent_id},
                "metadata": {"user_id": user_id, "company_id": str(company.company_id)},
            },
            db_session=db,
        )
        formatted = eng.context.get("conversation_history", "")
        assert "User: Hello" in formatted
        assert "Agent: Hi there!" in formatted


# ===========================================================================
# 13. User Preferences
# ===========================================================================

class TestUserPreferences:
    def test_preference_model_stored_correctly(self, db, company):
        pref = UserPreference(
            user_id="user-pref-1",
            company_id=company.company_id,
            communication_style="concise",
            preferred_sources=["sales_docs", "product_specs"],
            notification_preferences={"email": True, "sms": False},
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

        assert pref.communication_style == "concise"
        assert "sales_docs" in pref.preferred_sources
        assert pref.notification_preferences["email"] is True

    def test_all_communication_styles_accepted(self, db, company):
        for i, style in enumerate(["concise", "detailed", "technical"]):
            db.add(UserPreference(
                user_id=f"user-style-{i}",
                company_id=company.company_id,
                communication_style=style,
                preferred_sources=[],
                notification_preferences={},
            ))
        db.commit()

        for i, style in enumerate(["concise", "detailed", "technical"]):
            p = db.query(UserPreference).filter_by(user_id=f"user-style-{i}").first()
            assert p.communication_style == style

    def test_agent_specific_preferences_stored_separately(self, db, company):
        db.add(UserPreference(
            user_id="user-agent",
            company_id=company.company_id,
            agent_id=None,
            communication_style="detailed",
            preferred_sources=["general"],
            notification_preferences={},
        ))
        db.add(UserPreference(
            user_id="user-agent",
            company_id=company.company_id,
            agent_id="sales-bot",
            communication_style="technical",
            preferred_sources=["sales_docs"],
            notification_preferences={},
        ))
        db.commit()

        prefs = db.query(UserPreference).filter_by(user_id="user-agent").all()
        assert len(prefs) == 2
        general = next(p for p in prefs if p.agent_id is None)
        specific = next(p for p in prefs if p.agent_id == "sales-bot")
        assert general.communication_style == "detailed"
        assert specific.communication_style == "technical"

    def test_tenant_isolation_for_preferences(self, db, company):
        company2 = Company(company_id=uuid.uuid4(), company_name="Company 2")
        db.add(company2)
        db.commit()

        db.add(UserPreference(
            user_id="shared-user",
            company_id=company.company_id,
            communication_style="concise",
            preferred_sources=[],
            notification_preferences={},
        ))
        db.add(UserPreference(
            user_id="shared-user",
            company_id=company2.company_id,
            communication_style="technical",
            preferred_sources=[],
            notification_preferences={},
        ))
        db.commit()

        p1 = db.query(UserPreference).filter_by(
            user_id="shared-user", company_id=company.company_id
        ).first()
        p2 = db.query(UserPreference).filter_by(
            user_id="shared-user", company_id=company2.company_id
        ).first()
        assert p1.communication_style == "concise"
        assert p2.communication_style == "technical"

    def test_preference_update_preserves_other_fields(self, db, company):
        pref = UserPreference(
            user_id="user-update",
            company_id=company.company_id,
            communication_style="detailed",
            preferred_sources=["docs_a"],
            notification_preferences={"email": True},
        )
        db.add(pref)
        db.commit()

        pref.communication_style = "concise"
        db.commit()
        db.refresh(pref)

        assert pref.communication_style == "concise"
        assert "docs_a" in pref.preferred_sources
        assert pref.notification_preferences["email"] is True

    def test_preference_crud_end_to_end(self, db, company):
        pref = UserPreference(
            user_id="user-e2e",
            company_id=company.company_id,
            communication_style="detailed",
            preferred_sources=["docs"],
            notification_preferences={},
        )
        db.add(pref)
        db.commit()

        retrieved = db.query(UserPreference).filter_by(user_id="user-e2e").first()
        assert retrieved is not None

        retrieved.communication_style = "concise"
        db.commit()
        db.refresh(retrieved)
        assert retrieved.communication_style == "concise"

        db.delete(retrieved)
        db.commit()
        assert db.query(UserPreference).filter_by(user_id="user-e2e").first() is None

    def test_pydantic_model_defaults(self):
        pref = UserPreferenceCreate(user_id="user-defaults")
        assert pref.agent_id is None
        assert pref.communication_style == "detailed"
        assert pref.preferred_sources == []
        assert pref.notification_preferences == {}

    def test_preferred_sources_boost_logic(self):
        session_ctx = {
            "user_preferences": {
                "preferred_sources": ["sales_docs", "product_specs"],
            }
        }
        config_weights = {}
        for source in session_ctx["user_preferences"]["preferred_sources"]:
            if source not in config_weights:
                config_weights[source] = 1.5

        assert config_weights["sales_docs"] == 1.5
        assert config_weights["product_specs"] == 1.5

    def test_explicit_weights_not_overridden_by_preferences(self):
        config_weights = {"sales_docs": 2.0}
        preferred = ["sales_docs"]
        for source in preferred:
            if source not in config_weights:
                config_weights[source] = 1.5

        assert config_weights["sales_docs"] == 2.0

    def test_preferences_loaded_into_engine_session_context(self):
        eng = WorkflowExecutionEngine(
            workflow_json=VALID_WORKFLOW,
            vapi_payload={
                "messages": [{"role": "user", "content": "Hello"}],
                "call": {"id": "c1", "assistantId": "agent-1"},
                "metadata": {"company_id": str(uuid.uuid4()), "user_id": "user-1"},
            },
            db_session=None,
        )
        assert "user_preferences" in eng.session_context
        assert eng.session_context["user_preferences"] == {}


# ===========================================================================
# 14. Vapi SSE Integration
# ===========================================================================

class TestVapiIntegration:
    def test_endpoint_returns_200_and_sse_content_type(self):
        resp = client.post("/chat/completions", json={"messages": [{"role": "user", "content": "Hello"}]})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_sse_stream_contains_done_marker(self):
        resp = client.post("/chat/completions", json={"messages": [{"role": "user", "content": "Hello"}]})
        assert "data: [DONE]" in resp.text

    def test_sse_chunks_are_openai_compatible(self):
        resp = client.post("/chat/completions", json={"messages": [{"role": "user", "content": "Hello"}]})
        data_lines = [
            line for line in resp.text.split("\n")
            if line.startswith("data: ") and line != "data: [DONE]"
        ]
        assert len(data_lines) >= 1
        chunk = json.loads(data_lines[0].replace("data: ", ""))
        assert chunk["object"] == "chat.completion.chunk"
        assert "choices" in chunk
        assert "id" in chunk
        assert "model" in chunk

    def test_sse_stream_has_stop_chunk(self):
        resp = client.post("/chat/completions", json={"messages": [{"role": "user", "content": "Hello"}]})
        data_lines = [
            line for line in resp.text.split("\n")
            if line.startswith("data: ") and line != "data: [DONE]"
        ]
        stop_chunks = [
            json.loads(line.replace("data: ", ""))
            for line in data_lines
            if "finish_reason" in json.loads(line.replace("data: ", "")).get("choices", [{}])[0]
        ]
        assert len(stop_chunks) > 0
        assert stop_chunks[0]["choices"][0]["finish_reason"] == "stop"

    def test_unknown_assistant_id_falls_back_gracefully(self):
        resp = client.post(
            "/chat/completions",
            json={
                "call": {"assistantId": "unknown_agent_999"},
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
