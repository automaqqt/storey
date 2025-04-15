from typing import List
import chromadb
from sentence_transformers import SentenceTransformer
from ..core.config import settings
import json
from functools import lru_cache # Cache model and client

@lru_cache(maxsize=1)
def get_embedding_model():
    print(f"Loading embedding model: {settings.embedding_model_name}")
    return SentenceTransformer(settings.embedding_model_name)

@lru_cache(maxsize=1)
def get_chroma_client():
    print(f"Connecting to Chroma DB at: {settings.chroma_db_path}")
    return chromadb.PersistentClient(path=settings.chroma_db_path)

@lru_cache(maxsize=1)
def load_tale_metadata():
     print(f"Loading tale metadata from: {settings.tale_metadata_path}")
     try:
         with open(settings.tale_metadata_path, 'r', encoding='utf-8') as f:
             return json.load(f)
     except FileNotFoundError:
         print(f"Error: Tale metadata file not found at {settings.tale_metadata_path}")
         return {}
     except json.JSONDecodeError:
          print(f"Error: Could not decode JSON from {settings.tale_metadata_path}")
          return {}

def get_original_summary(tale_id: str) -> str:
    metadata = load_tale_metadata()
    return metadata.get(tale_id, {}).get("original_summary", f"The original tale of {tale_id}.")


def retrieve_relevant_chunks(tale_id: str, query_text: str, k: int = 3) -> str:
    model = get_embedding_model()
    client = get_chroma_client()

    try:
        collection = client.get_collection(name=settings.chroma_collection_name)
    except Exception as e:
        print(f"Error getting Chroma collection: {e}")
        return "Error: Could not access original tale context."

    if not query_text:
        return "No query provided for context retrieval."

    print(f"RAG: Generating query embedding for: '{query_text[:100]}...'")
    query_embedding = model.encode([query_text])[0].tolist()

    print(f"RAG: Querying collection for tale '{tale_id}'...")
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"tale_title": tale_id}, # Filter by the specific tale
            include=['documents'] # We only need the text content
        )
    except Exception as e:
         print(f"Error querying Chroma DB: {e}")
         return "Error retrieving context from original tale."

    # Ensure results structure is as expected
    if not results or not results.get('documents') or not results['documents'][0]:
         print("RAG: No relevant documents found.")
         return "No specific context found in the original tale for this situation."

    retrieved_docs = results['documents'][0]
    context = " ".join(retrieved_docs)
    print(f"RAG: Retrieved {len(retrieved_docs)} chunks.")

    return f"Relevant context from the original tale: {context}"

def get_available_tales() -> List[str]:
    metadata = load_tale_metadata()
    return list(metadata.keys())