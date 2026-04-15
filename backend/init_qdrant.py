import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

load_dotenv()

def initialize_memory():
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

    collection_name = "auralis_knowledge"

    # Create collection with 1536 dimensions (Standard for OpenAI/Gemini embeddings)
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=1536, 
            distance=models.Distance.COSINE
        ),
    )
    print(f"✅ Collection '{collection_name}' initialized in Qdrant.")

if __name__ == "__main__":
    initialize_memory()