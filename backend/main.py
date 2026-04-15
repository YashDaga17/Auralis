from fastapi import FastAPI, Request
from qdrant_client import QdrantClient
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Initialize clients
q_client = QdrantClient(
    url=os.getenv("QDRANT_URL"), 
    api_key=os.getenv("QDRANT_API_KEY")
)
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.get("/")
async def root():
    return {"status": "Auralis is Online", "message": "Backend is reachable."}

@app.post("/chat/completions")
async def vapi_handler(request: Request):
    try:
        data = await request.json()
        
        # 1. Extract the transcript
        user_query = data.get("message", {}).get("transcript", "")
        
        if not user_query:
            return {"assistantMessage": {"content": "I'm listening. How can Auralis help?"}}

        # 2. Generate Embedding for the query
        # text-embedding-004 is excellent for Qdrant semantic search
        result = genai_client.models.embed_content(
            model="models/text-embedding-004",
            contents=user_query
        )
        vector = result.embedding

        # 3. Search Qdrant Memory
        docs = q_client.search(
            collection_name="auralis_knowledge",
            query_vector=vector,
            limit=2
        )
        
        context = "\n".join([d.payload.get("text", "") for d in docs]) if docs else "No specific documents found."

        # 4. Synthesis Logic
        model = genai_client.models.get('gemini-2.5-flash')
        
        prompt = (
            f"You are Auralis, a high-level enterprise orchestrator. "
            f"Use the following context to answer the user concisely: \n\n"
            f"Context: {context}\n\n"
            f"User Question: {user_query}"
        )
        
        response = model.generate_content(prompt)

        return {"assistantMessage": {"content": response.text}}

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return {"assistantMessage": {"content": "I encountered a sync error, but I'm still here. Could you repeat that?"}}