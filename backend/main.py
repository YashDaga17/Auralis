from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
import os
import time
import json
from google import genai
from dotenv import load_dotenv
from database import check_postgres_health, check_neo4j_health, close_connections, get_db
from auth import get_auth_context, AuthContext

# Import route modules
from routes import workflows, knowledge, graph

load_dotenv()

app = FastAPI(
    title="Auralis Visual Workflow Engine",
    description="Multi-tenant SaaS platform for designing and deploying custom voice agents",
    version="1.0.0"
)

# Configure CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development
        "http://localhost:3001",
        os.getenv("FRONTEND_URL", "https://auralis.vercel.app")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route modules
app.include_router(workflows.router)
app.include_router(knowledge.router)
app.include_router(graph.router)

# Initialize Clients
q_client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Shutdown event
@app.on_event("shutdown")
def shutdown_event():
    """Clean up database connections on shutdown."""
    close_connections()

@app.get("/")
async def root():
    return {"status": "Auralis is Online", "message": "Backend is reachable."}

@app.get("/health")
async def health_check():
    """Health check endpoint for all services."""
    postgres_healthy = check_postgres_health()
    neo4j_healthy = check_neo4j_health()
    
    # Check Qdrant
    qdrant_healthy = False
    try:
        q_client.get_collections()
        qdrant_healthy = True
    except Exception:
        pass
    
    return {
        "status": "healthy" if all([postgres_healthy, qdrant_healthy]) else "degraded",
        "services": {
            "postgres": "healthy" if postgres_healthy else "unhealthy",
            "qdrant": "healthy" if qdrant_healthy else "unhealthy",
            "neo4j": "healthy" if neo4j_healthy else "not_configured",
            "gemini": "configured"
        }
    }

@app.post("/chat/completions")
async def vapi_handler(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Vapi webhook endpoint for voice agent responses.
    
    Note: Authentication is optional for this endpoint as Vapi sends requests
    without JWT tokens. In production, verify requests using Vapi webhook signatures.
    
    Requirements: 5.1, 5.2, 20.1, 20.2
    """
    data = await request.json()
    
    # Extract assistant_id from Vapi payload (if available)
    assistant_id = data.get("call", {}).get("assistantId") or data.get("assistant_id")
    
    # 1. Extract user query from OpenAI format (Custom LLM expects this)
    messages = data.get("messages", [])
    user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_query = msg.get("content", "")
            break
    
    if not user_query:
         user_query = "Hello Auralis."

    # 2. Qdrant Safety Net (Skip if empty)
    context = "No specific enterprise documents found. Answer generally."
    try:
        # NEW SDK: Generating Embeddings
        result = genai_client.models.embed_content(
            model="text-embedding-004",
            contents=user_query 
        )
        # Extract the actual float array
        vector = result.embeddings[0].values

        docs = q_client.search(
            collection_name="auralis_knowledge",
            query_vector=vector,
            limit=2
        )
        if docs:
            context = "\n".join([d.payload.get("text", "") for d in docs])
    except Exception as e:
        print(f"Qdrant memory skip (database likely empty): {e}")

    # 3. Agentic Logic (Synthesis) - NEW SDK Syntax
    prompt = (
        f"You are Auralis, an Enterprise Voice Agent orchestrator. "
        f"Speak concisely. Do not use markdown.\n\n"
        f"Context: {context}\n\nUser Question: {user_query}"
    )
    
    response = genai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    final_text = response.text

    # 4. Stream the response back to Vapi (Server-Sent Events)
    async def stream_generator():
        chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "auralis-engine",
            "choices": [{"delta": {"content": final_text}, "index": 0, "finish_reason": None}]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        
        stop_chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "auralis-engine",
            "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(stop_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")