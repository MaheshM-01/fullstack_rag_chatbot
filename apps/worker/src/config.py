



from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from pathlib import Path


# ============================================================
# FIND .ENV FILE
# ============================================================
def find_env_file() -> str:
    
    
    current = Path(__file__).resolve().parent

    
    for level in range(5):
        env_file = current / ".env"

        if env_file.exists():
            print(f" .env found at level {level}: {env_file}")
            return str(env_file)

       
        current = current.parent

    
    
    return ".env"


# ============================================================
# SETTINGS CLASS
# ============================================================
class Settings(BaseSettings):
   

   
    groq_api_key: str = Field(..., env="GROQ_API_KEY")

    
    groq_model_name: str = Field(
        default="llama3-70b-8192",
        env="GROQ_MODEL_NAME"
    )

    
    chroma_persist_directory: str = Field(
        default="./chroma_db",
        env="CHROMA_PERSIST_DIRECTORY"
    )
    chroma_collection_name: str = Field(
        default="rag_documents",
        env="CHROMA_COLLECTION_NAME"
    )

    
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL_NAME"
    )

    
    worker_host: str = Field(default="0.0.0.0", env="WORKER_HOST")
    worker_port: int = Field(default=8000, env="WORKER_PORT")
    worker_reload: bool = Field(default=True, env="WORKER_RELOAD")

    
    rag_top_k: int = Field(default=5, env="RAG_TOP_K")
    rag_score_threshold: float = Field(
        default=0.7,
        env="RAG_SCORE_THRESHOLD"
    )
    rag_chunk_size: int = Field(default=500, env="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(
        default=50,
        env="RAG_CHUNK_OVERLAP"
    )

    
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    max_file_size_mb: int = Field(
        default=10,
        env="MAX_FILE_SIZE_MB"
    )

    # --------------------------------------------------------
    # APP SETTINGS
    # --------------------------------------------------------
    node_env: str = Field(default="development", env="NODE_ENV")
    log_level: str = Field(default="debug", env="LOG_LEVEL")

   
    frontend_url: str = Field(
        default="http://localhost:3000",
        env="FRONTEND_URL"
    )

    class Config:
       
        env_file = find_env_file()
        env_file_encoding = "utf-8"
        extra = "ignore"



@lru_cache()
def get_settings() -> Settings:
    """Returns cached Settings instance."""
    return Settings()         



settings = get_settings()