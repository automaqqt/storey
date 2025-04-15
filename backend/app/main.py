from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import routes
from .core.config import settings # Ensure settings are loaded

# Initialize services (loads models/clients on startup)
from .services import rag_service, llm_service
rag_service.get_embedding_model()
rag_service.get_chroma_client()
rag_service.load_tale_metadata()
# Add LLM client initialization if needed (e.g., pre-connecting Ollama)

app = FastAPI(title="Interactive Storyteller API")

# CORS Middleware (Adjust origins as needed for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Allow Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api") # Add '/api' prefix

@app.get("/")
async def root():
    return {"message": "Welcome to the Interactive Storyteller API"}