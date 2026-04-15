from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from qdrant_client import QdrantClient
import os
import time
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Initialize Clients
q_client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.get("/")
async def root():
    return {"status": "Auralis is Online", "message": "Backend is reachable."}

@app.post("/chat/completions")
async def vapi_handler(request: Request):
    data = await request.json()
    
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