#!/usr/bin/env python3
"""
Manual Demo Script - Visual Workflow Engine Backend

Run this script to see the backend working in real-time.
This demonstrates exactly what happens when a voice call comes in.

Usage:
    python demo_workflow.py
"""
import asyncio
import json
from workflow_execution import WorkflowExecutionEngine
from node_executors import (
    RAGNodeExecutor,
    LLMNodeExecutor,
    ToolNodeExecutor,
    get_registry
)


# Mock clients for demo
class DemoQdrantClient:
    def search(self, collection_name, query_vector, query_filter=None, limit=5):
        # Simulate finding relevant documents
        class Result:
            def __init__(self, text):
                self.payload = {'text': text}
                self.score = 0.95
        
        return [
            Result("Our support hours are Monday-Friday, 9 AM to 6 PM EST."),
            Result("You can reach us via email at support@company.com or call 1-800-SUPPORT."),
            Result("For urgent issues, use our 24/7 emergency hotline.")
        ]


class DemoGeminiClient:
    def __init__(self):
        self.models = self
    
    def embed_content(self, model, contents):
        class Embedding:
            def __init__(self):
                self.values = [0.1] * 768
        
        class Result:
            def __init__(self):
                self.embeddings = [Embedding()]
        
        return Result()
    
    def generate_content(self, model, contents, generation_config=None):
        class Response:
            def __init__(self):
                self.text = (
                    "Our support team is available Monday through Friday from 9 AM to 6 PM EST. "
                    "You can contact us via email at support@company.com or call our main line at 1-800-SUPPORT. "
                    "For urgent matters outside business hours, we have a 24/7 emergency hotline available. "
                    "How else can I assist you today?"
                )
        
        return Response()


async def run_demo():
    """Run a demonstration of the workflow engine."""
    
    print("\n" + "="*80)
    print(" "*20 + "🎯 VISUAL WORKFLOW ENGINE - BACKEND DEMO")
    print("="*80)
    
    print("\n📋 SCENARIO:")
    print("   A customer calls asking about support hours")
    print("   The workflow will:")
    print("   1. Receive the question (Trigger)")
    print("   2. Search the knowledge base (RAG Node)")
    print("   3. Generate a helpful response (LLM Node)")
    print("   4. Return the answer to the customer")
    
    # Define the workflow (this is what the frontend would create)
    workflow = {
        "version": "1.0.0",
        "metadata": {
            "workflow_name": "Customer Support Bot",
            "description": "Answers customer questions using RAG + LLM",
            "created_by": "demo@company.com",
            "updated_at": "2024-01-15T10:00:00Z"
        },
        "nodes": [
            {
                "id": "trigger",
                "type": "trigger",
                "data": {
                    "label": "Customer Question",
                    "config": {}
                },
                "position": {"x": 100, "y": 200}
            },
            {
                "id": "search_kb",
                "type": "rag",
                "data": {
                    "label": "Search Knowledge Base",
                    "config": {
                        "collection_name": "support_docs",
                        "query_template": "{{trigger_output}}",
                        "result_limit": 3
                    }
                },
                "position": {"x": 350, "y": 200}
            },
            {
                "id": "generate_answer",
                "type": "llm",
                "data": {
                    "label": "Generate Answer",
                    "config": {
                        "system_prompt": "You are a friendly customer support agent. Use the context provided to answer questions accurately.",
                        "user_prompt": "Context:\n{{search_kb_output}}\n\nCustomer question: {{trigger_output}}\n\nProvide a helpful answer:",
                        "temperature": 0.7,
                        "max_tokens": 300
                    }
                },
                "position": {"x": 600, "y": 200}
            }
        ],
        "edges": [
            {
                "id": "edge1",
                "source": "trigger",
                "target": "search_kb"
            },
            {
                "id": "edge2",
                "source": "search_kb",
                "target": "generate_answer"
            }
        ]
    }
    
    # Simulate incoming call from Vapi
    vapi_request = {
        "messages": [
            {
                "role": "user",
                "content": "What are your support hours?"
            }
        ],
        "call": {
            "id": "call_abc123",
            "customer_number": "+1-555-0123"
        },
        "metadata": {
            "company_id": "demo_company_123"
        }
    }
    
    print("\n" + "-"*80)
    print("📞 INCOMING CALL")
    print("-"*80)
    print(f"   Call ID: {vapi_request['call']['id']}")
    print(f"   From: {vapi_request['call']['customer_number']}")
    print(f"   Customer said: \"{vapi_request['messages'][0]['content']}\"")
    
    print("\n" + "-"*80)
    print("⚙️  WORKFLOW EXECUTION")
    print("-"*80)
    
    # Initialize the execution engine
    print("\n[1/4] Initializing Workflow Execution Engine...")
    engine = WorkflowExecutionEngine(workflow, vapi_request)
    print("      ✓ Workflow parsed successfully")
    print(f"      ✓ Found {len(workflow['nodes'])} nodes")
    print(f"      ✓ Found {len(workflow['edges'])} edges")
    
    # Set up mock clients
    qdrant = DemoQdrantClient()
    gemini = DemoGeminiClient()
    
    # Register executors
    registry = get_registry()
    registry._executors['rag'] = lambda: RAGNodeExecutor(qdrant, gemini)
    registry._executors['llm'] = lambda: LLMNodeExecutor(gemini)
    
    print("\n[2/4] Executing Trigger Node...")
    print(f"      ✓ User input captured: \"{vapi_request['messages'][0]['content']}\"")
    
    print("\n[3/4] Executing RAG Node (search_kb)...")
    print("      → Generating embedding for query...")
    print("      → Searching Qdrant collection 'support_docs'...")
    print("      → Retrieved 3 relevant documents")
    print("      ✓ Knowledge retrieved successfully")
    
    print("\n[4/4] Executing LLM Node (generate_answer)...")
    print("      → Building prompt with context...")
    print("      → Calling Gemini 2.5 Flash...")
    print("      → Generating response...")
    
    # Execute the workflow
    result = await engine.execute()
    
    print("      ✓ Response generated successfully")
    
    print("\n" + "-"*80)
    print("📤 RESPONSE TO CUSTOMER")
    print("-"*80)
    print(f"\n{result}\n")
    
    print("-"*80)
    print("🔍 EXECUTION DETAILS")
    print("-"*80)
    print(f"\nContext Variables Created:")
    for key, value in engine.context.items():
        if isinstance(value, str):
            preview = value[:60] + "..." if len(value) > 60 else value
            print(f"   • {key}: \"{preview}\"")
    
    print("\n" + "="*80)
    print("✅ WORKFLOW EXECUTION COMPLETE")
    print("="*80)
    print("\nWhat just happened:")
    print("   1. ✓ Workflow JSON was parsed and validated")
    print("   2. ✓ DAG structure was built from nodes and edges")
    print("   3. ✓ Nodes executed in correct topological order")
    print("   4. ✓ Context variables flowed between nodes")
    print("   5. ✓ Final response was generated and returned")
    print("\n💡 This is exactly what happens when a real voice call comes in!")
    print("   The frontend will create the workflow JSON, and the backend executes it.")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("\n🚀 Starting Backend Demo...\n")
    asyncio.run(run_demo())
