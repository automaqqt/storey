
import os

class Settings():
    llm_api_url: str = "http://localhost:11434/api/generate" # Default Ollama generate URL
    llm_model_name: str = "google_gemma-3-12b-it" #"bartowski/RekaAI_reka-flash-3-GGUF" # "mradermacher/gemma-2-Ifable-9B-GGUF" #"gemma-3-4b-it" #"gemma-2-ifable-9b" # "r1-deepseek-distill-llama-8b" #"lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF" # 

    llm_type: str = "openrouter" # or "openai_compatible"
    openai_api_url: str = "http://localhost:1234/v1/chat/completions" # LM Studio default
    embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2" #"intfloat/multilingual-e5-large-instruct" # #all-MiniLM-L6-v2"
    chroma_db_path: str = "./chroma_db"
    chroma_collection_name: str = "german_tales"
    tale_metadata_path: str = "./app/services/tale_metadata.json"
    openrouter_model: str =  "google/gemini-2.0-flash-exp:free" #"google/gemini-2.0-flash-exp:free" #"google/gemini-2.5-pro-exp-03-25:free" #"deepseek/deepseek-r1:free" # "deepseek/deepseek-chat-v3-0324:free"

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields in .env

settings = Settings()