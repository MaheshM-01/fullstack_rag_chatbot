
"""
FASTAPI MAIN SERVER
===================
WHAT:  HTTP server exposing all RAG functionality as REST API endpoints.
       This is the entry point for the entire Python worker service.

WHY:   NestJS (Node.js) cannot run Python libraries directly.
       FastAPI runs Python RAG logic as a separate HTTP server.
       NestJS calls this server's endpoints via HTTP.

WHERE: This IS the server — started by uvicorn.
       All other Python files are called BY this file.

WHEN:  Always running during development/production.
       Start: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

API DOCS: Once running, visit http://localhost:8000/docs
          FastAPI auto-generates interactive API documentation! ✅
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.ingestion.pipeline import IngestionPipeline
from src.generation.chain import RAGChain
from src.config import settings


# ============================================================
# PYDANTIC MODELS — Request/Response shapes
# ============================================================
# WHAT: Define exact structure of API request and response bodies
# WHY:
#   Without Pydantic:
#     data = request.json()
#     question = data["question"]  # Crashes if "question" missing!
#
#   With Pydantic:
#     FastAPI auto-validates incoming JSON
#     Missing field → clear 422 error with field name
#     Wrong type → clear error message
#     No manual validation code needed ✅
# ============================================================

class ChatRequest(BaseModel):
    """
    Request body for POST /chat endpoint.

    Fields:
      question:     User's question (required)
      namespace:    Which docs to search (default="default")
      chat_history: Previous Q&A for follow-up support
      top_k:        How many chunks to retrieve (optional override)
    """
    question: str = Field(
        ...,                        # ... = required field
        min_length=1,               # Can't be empty string
        max_length=1000,            # Prevent huge inputs
        description="User's question"
    )
    namespace: str = Field(
        default="default",
        description="ChromaDB namespace to search in"
    )
    chat_history: List[dict] = Field(
        default=[],
        description="Previous Q&A pairs for follow-up questions"
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,                       # Must be >= 1
        le=20,                      # Must be <= 20
        description="Number of chunks to retrieve"
    )


class ChatResponse(BaseModel):
    """Response body for POST /chat endpoint."""
    answer:      str
    sources:     List[dict]
    chunks_used: int
    question:    str
    has_context: bool


class IngestURLRequest(BaseModel):
    """Request body for POST /ingest/url endpoint."""
    url: str = Field(
        ...,
        description="URL to fetch and ingest"
    )
    namespace: str = Field(
        default="default",
        description="Namespace to store in"
    )
    force_reingest: bool = Field(
        default=False,
        description="Re-ingest even if already processed"
    )


class IngestResponse(BaseModel):
    """Response body for ingestion endpoints."""
    status:         str
    file_name:      str
    chunks_created: int
    namespace:      str
    message:        str


class ResetResponse(BaseModel):
    """Response body for DELETE /reset endpoint."""
    status:  str
    message: str


# ============================================================
# LIFESPAN — Initialize components when server starts
# ============================================================
# WHAT: Code that runs ONCE when FastAPI starts up.
#
# WHY lifespan (not @app.on_event):
#   Old way: @app.on_event("startup") → deprecated in FastAPI
#   New way: @asynccontextmanager lifespan → recommended ✅
#
# WHY initialize here (not at request time):
#   ChromaVectorStore loads 90MB embedding model on init.
#   If we initialize at request time → every request waits for model load!
#   
#   Initialize ONCE at startup:
#     Server start → load model (5-10 seconds, once)
#     All requests → model already in memory (fast!) ✅
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup: Initialize pipeline and chain.
    Runs on shutdown: Cleanup (if needed).
    """
    # ---- STARTUP ----
    print("\n" + "=" * 55)
    print("🚀 RAG Chatbot Worker Starting...")
    print("=" * 55)

    # Create upload directory if needed
    # WHY: Uploaded files temporarily saved here before ingestion
    os.makedirs(settings.upload_dir, exist_ok=True)
    print(f"📁 Upload dir ready: {settings.upload_dir}")

    # Initialize pipeline (loads embedding model + ChromaDB)
    # Store on app.state so all endpoints can access it
    # WHY app.state: FastAPI's way to share objects between endpoints
    print("\n🏗️  Loading Ingestion Pipeline...")
    app.state.pipeline = IngestionPipeline()

    # Initialize RAG chain (loads Groq client)
    print("🔗 Loading RAG Chain...")
    app.state.chain = RAGChain()

    print("\n✅ Server ready!")
    print(f"   API docs: http://localhost:{settings.worker_port}/docs")
    print(f"   Health:   http://localhost:{settings.worker_port}/health")
    print("=" * 55 + "\n")

    yield  # Server runs here (between startup and shutdown)

    # ---- SHUTDOWN ----
    print("\n👋 RAG Chatbot Worker shutting down...")


# ============================================================
# CREATE FASTAPI APP
# ============================================================
app = FastAPI(
    title="RAG Chatbot Worker API",
    description="""
    🤖 RAG-powered document Q&A API
    
    Stack:
    - ChromaDB (local vector database)
    - Groq Llama3 (free LLM)
    - sentence-transformers (local embeddings)
    
    Workflow:
    1. Upload documents via /ingest/file or /ingest/url
    2. Ask questions via /chat
    3. Get accurate answers with source citations
    """,
    version="1.0.0",
    lifespan=lifespan,    # Use our startup/shutdown handler
)


# ============================================================
# CORS MIDDLEWARE
# ============================================================
# WHAT: Allows frontend (port 3000) to call this API (port 8000)
#
# WHY CORS EXISTS:
#   Browser security rule: "Only call APIs on same domain/port"
#   Frontend: http://localhost:3000
#   API:      http://localhost:8000  ← different port = BLOCKED! ❌
#
#   CORS middleware tells browser: "It's OK, I allow localhost:3000" ✅
#
# allow_origins: Which domains can call our API
# allow_methods: Which HTTP methods (GET, POST, DELETE etc.)
# allow_headers: Which headers are allowed
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,          # http://localhost:3000
        "http://localhost:3000",         # Next.js dev server
        "http://localhost:3001",         # NestJS backend
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],                # Allow all HTTP methods
    allow_headers=["*"],                # Allow all headers
)


# ============================================================
# ENDPOINTS
# ============================================================

# ------------------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    """
    WHAT: Simple health check endpoint.

    WHY:
      Docker, Kubernetes, monitoring tools ping this
      to know if the server is alive and working.
      
      Returns 200 OK → server is healthy ✅
      No response   → server is down ❌

    USAGE:
      GET http://localhost:8000/health
      → {"status": "healthy", "model": "llama-3.3-70b-versatile"}
    """
    return {
        "status":  "healthy",
        "service": "rag-chatbot-worker",
        "model":   settings.groq_model_name,
        "chroma":  settings.chroma_collection_name,
    }


# ------------------------------------------------------------
# STATS
# ------------------------------------------------------------
@app.get("/stats", tags=["System"])
async def get_stats():
    """
    WHAT: Returns ChromaDB collection stats.

    WHY:
      Admin dashboard can show:
      "Your knowledge base has 1,234 document chunks"
      "From 15 documents"

    USAGE:
      GET http://localhost:8000/stats
    """
    stats = app.state.pipeline.get_stats()
    return {
        "status": "success",
        **stats
    }


# ------------------------------------------------------------
# INGEST FILE
# ------------------------------------------------------------
@app.post("/ingest/file", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_file(
    file: UploadFile = File(...),
    namespace: str = Query(default="default"),
    force_reingest: bool = Query(default=False)
):
    """
    WHAT: Upload a file and ingest it into ChromaDB.

    WHY UploadFile (not JSON body):
      Files are binary data (PDF, DOCX).
      Can't put binary in JSON.
      multipart/form-data is the standard for file uploads.

    HOW:
      1. Validate file type (only PDF, TXT, DOCX allowed)
      2. Save to temp file (FastAPI gives us file stream, not path)
      3. Run ingestion pipeline on temp file
      4. Delete temp file (cleanup)
      5. Return ingestion stats

    WHY temp file:
      FastAPI's UploadFile is a stream object (not a saved file).
      DocumentLoader needs a FILE PATH to read.
      Solution: save stream to temp file → get path → pass to loader.

    USAGE:
      curl -X POST http://localhost:8000/ingest/file \
           -F "file=@gold_loan.pdf" \
           -F "namespace=default"

    Args:
      file:          The uploaded file (multipart/form-data)
      namespace:     ChromaDB namespace to store in
      force_reingest: Re-ingest even if already processed
    """
    # Validate file type
    # WHY: Only process supported types, reject everything else
    allowed_extensions = {".pdf", ".txt", ".docx", ".doc"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file_ext}' not supported. "
                   f"Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate file size
    # WHY: Prevent huge files from crashing the server
    max_bytes = settings.max_file_size_mb * 1024 * 1024  # MB → bytes

    # Save uploaded file to temp location
    # WHY tempfile: auto-cleanup, safe unique filename
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_ext,
            dir=settings.upload_dir
        ) as tmp:
            # Read uploaded file stream → write to temp file
            content = await file.read()

            # Check file size
            if len(content) > max_bytes:
                raise HTTPException(
                    status_code=413,    # 413 = Payload Too Large
                    detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
                )

            tmp.write(content)
            tmp_path = tmp.name

        print(f"\n📨 File upload received: {file.filename} "
              f"({len(content):,} bytes)")

        # Run ingestion pipeline
        result = app.state.pipeline.ingest(
            source=tmp_path,
            namespace=namespace,
            force_reingest=force_reingest,
            display_file_name=file.filename,
        )

        # Override file_name with original filename (not temp path)
        result["file_name"] = file.filename

        if result["status"] == "failed":
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )

        return IngestResponse(
            status=         result["status"],
            file_name=      file.filename,
            chunks_created= result.get("chunks_created", 0),
            namespace=      namespace,
            message=        result["message"]
        )

    finally:
        # ALWAYS delete temp file — even if error occurred
        # WHY: Don't leave sensitive documents on disk
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            print(f"   🗑️  Temp file cleaned up")


# ------------------------------------------------------------
# INGEST URL
# ------------------------------------------------------------
@app.post("/ingest/url", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_url(request: IngestURLRequest):
    """
    WHAT: Fetch a webpage URL and ingest its content.

    WHY:
      Not all knowledge is in PDFs.
      Company FAQ pages, documentation sites, news articles
      can be ingested directly from their URL.

    USAGE:
      POST http://localhost:8000/ingest/url
      Body: {"url": "https://smartspend.ai/faq", "namespace": "default"}
    """
    # Basic URL validation
    if not (request.url.startswith("http://") or
            request.url.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://"
        )

    result = app.state.pipeline.ingest(
        source=request.url,
        namespace=request.namespace,
        force_reingest=request.force_reingest
    )

    if result["status"] == "failed":
        raise HTTPException(status_code=500, detail=result["message"])

    return IngestResponse(
        status=         result["status"],
        file_name=      result["file_name"],
        chunks_created= result.get("chunks_created", 0),
        namespace=      request.namespace,
        message=        result["message"]
    )


# ------------------------------------------------------------
# CHAT — Normal (full response)
# ------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    WHAT: Ask a question, get a complete RAG-powered answer.

    WHY async:
      While waiting for Groq API response,
      async allows server to handle other requests.
      Synchronous → server blocked during API call ❌
      Async       → server handles other requests while waiting ✅

    USAGE:
      POST http://localhost:8000/chat
      Body: {
        "question": "What is gold loan interest rate?",
        "namespace": "default",
        "chat_history": []
      }

    Response: {
      "answer": "According to gold_loan.pdf, the rate is 12%...",
      "sources": [{"file": "gold_loan.pdf", "page": "3"}],
      "chunks_used": 3,
      "question": "What is gold loan interest rate?",
      "has_context": true
    }
    """
    try:
        result = app.state.chain.answer(
            question=     request.question,
            chat_history= request.chat_history,
            namespace=    request.namespace,
            top_k=        request.top_k,
        )

        return ChatResponse(**result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {repr(e)}"
        )


# ------------------------------------------------------------
# CHAT STREAM — Token by token (for real-time UI)
# ------------------------------------------------------------
@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest):
    """
    WHAT: Ask a question, get answer streamed token by token.

    WHY STREAMING:
      Normal /chat: User waits 5-10s → full answer appears
      /chat/stream: Answer appears word by word instantly
                    Like ChatGPT — much better UX ✅

    HOW StreamingResponse works:
      FastAPI sends HTTP chunked transfer encoding.
      Each token → sent immediately as HTTP chunk.
      Frontend receives and displays tokens as they arrive.

    FRONTEND USAGE (JavaScript fetch):
      const response = await fetch('/chat/stream', {
        method: 'POST',
        body: JSON.stringify({question: "What is gold loan rate?"})
      });
      const reader = response.body.getReader();
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        const token = new TextDecoder().decode(value);
        displayToken(token);  // Show token in UI immediately
      }

    USAGE:
      POST http://localhost:8000/chat/stream
      Body: {"question": "What is gold loan rate?"}
    """
    def generate():
        """Generator function that yields tokens."""
        try:
            for token in app.state.chain.stream(
                question=     request.question,
                chat_history= request.chat_history,
                namespace=    request.namespace,
            ):
                yield token
        except Exception as e:
            yield f"\n\n❌ Error: {str(e)}"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            # Tell client this is streaming
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        }
    )


# ------------------------------------------------------------
# DELETE / RESET
# ------------------------------------------------------------
@app.delete("/reset", response_model=ResetResponse, tags=["System"])
async def reset_knowledge_base():
    """
    WHAT: Wipe ALL documents from ChromaDB.

    WHY:
      Development: start fresh without restarting server.
      Testing: clean state before each test.

    ⚠️  WARNING: This deletes ALL ingested documents permanently!
    
    USAGE:
      DELETE http://localhost:8000/reset
    """
    app.state.pipeline.reset()
    return ResetResponse(
        status="success",
        message="Knowledge base reset. All documents deleted."
    )


# ------------------------------------------------------------
# DELETE NAMESPACE
# ------------------------------------------------------------
@app.delete("/namespace/{namespace}", tags=["System"])
async def delete_namespace(namespace: str):
    """
    WHAT: Delete all documents in a specific namespace.

    WHY:
      User wants to remove ONE set of documents
      without deleting everything else.

    USAGE:
      DELETE http://localhost:8000/namespace/user_123
    """
    app.state.pipeline.store.delete_namespace(namespace)
    return {
        "status":    "success",
        "namespace": namespace,
        "message":   f"All documents in namespace '{namespace}' deleted."
    }


# ============================================================
# RUN SERVER (when file run directly)
# ============================================================
# WHY this block:
#   When you run: python src/api/main.py
#   This block starts uvicorn server automatically.
#
#   When imported by other code (testing):
#   This block is SKIPPED (only runs when __name__ == "__main__")
#
# NORMAL WAY TO START (recommended):
#   uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.worker_host,
        port=settings.worker_port,
        reload=settings.worker_reload,    # Auto-restart on code change
        log_level=settings.log_level,
    )

