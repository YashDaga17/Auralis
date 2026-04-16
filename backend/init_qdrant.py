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

    # Create collection with 768 dimensions (Gemini text-embedding-004)
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=768,  # Gemini text-embedding-004 dimension
            distance=models.Distance.COSINE
        ),
    )
    print(f"[SUCCESS] Collection '{collection_name}' initialized in Qdrant.")

if __name__ == "__main__":
    initialize_memory()