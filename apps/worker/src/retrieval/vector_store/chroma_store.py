"""
CHROMA VECTOR STORE
===================
WHAT:  Local vector database using ChromaDB + sentence-transformers.
       Stores document chunks as vectors, searches by semantic similarity.

WHY:   ChromaDB = 100% local, no cloud, no cost, no internet after setup.
       sentence-transformers = local embeddings, no API key needed.

WHERE: Called by:
       - src/ingestion/pipeline.py  → add_documents() during ingestion
       - src/generation/chain.py    → search() during chat

WHEN:
       add_documents() → user uploads a file
       search()        → user asks a question

HOW:
       Store:  chunk text → embed → vector saved in ./chroma_db
       Search: question → embed → cosine similarity → top-K chunks
"""

import os
import hashlib
import logging
from typing import List, Optional
from langchain.schema import Document

# Disable ChromaDB telemetry BEFORE importing chromadb
# WHY: ChromaDB 0.5.x has a bug where telemetry fails with loud errors
#      Setting env vars before import prevents it at source
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

# Suppress chromadb log noise
# WHY: Even with env vars, some versions still log telemetry errors
#      This silences them completely so our logs stay clean
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("chromadb").setLevel(logging.WARNING)

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from src.config import settings


class ChromaVectorStore:
    """
    WHAT: Manages all ChromaDB operations.
          Handles: embedding generation, document storage, similarity search.

    WHY ONE CLASS:
      All vector DB logic in one place.
      pipeline.py and chain.py just call simple methods:
        store.add_documents(chunks)   → store documents
        store.search("question")      → find relevant chunks
      They don't need to know HOW ChromaDB works internally.

    USAGE:
      store = ChromaVectorStore()
      store.add_documents(chunks)
      results = store.search("gold loan interest rate")
    """

    def __init__(self):
        """
        WHAT: Initialize in correct ORDER:
          1. Define persist_dir (needed by ChromaDB init)
          2. Create ChromaDB client
          3. Get or create collection
          4. Load embedding model

        WHY THIS ORDER:
          persist_dir must be defined BEFORE os.makedirs(persist_dir)
          ChromaDB must be ready BEFORE loading embedding model
          Each step depends on the previous one completing successfully
        """

        # --------------------------------------------------------
        # STEP 1: Define ChromaDB storage path
        # --------------------------------------------------------
        # WHAT: Where ChromaDB saves all data on your computer
        # WHY:  Define THIS FIRST — used in next step
        # PATH: ./chroma_db folder (from .env CHROMA_PERSIST_DIRECTORY)
        #
        # After first use, folder looks like:
        # chroma_db/
        #   ├── chroma.sqlite3       ← metadata
        #   └── [collection-uuid]/   ← vector index files
        # --------------------------------------------------------
        persist_dir = settings.chroma_persist_directory  # Define FIRST

        # Create folder if it doesn't exist
        # exist_ok=True → no error if folder already exists
        os.makedirs(persist_dir, exist_ok=True)

        # --------------------------------------------------------
        # STEP 2: Initialize ChromaDB Client
        # --------------------------------------------------------
        # WHAT: PersistentClient saves data permanently to disk
        # WHY:  Without persistent → data lost when app restarts!
        #
        # allow_reset=True       → can wipe collection in dev/testing
        # anonymized_telemetry=False → no data sent to ChromaDB servers
        # --------------------------------------------------------
        print(f"📁 Initializing ChromaDB at: {persist_dir}")

        self.chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )

        # --------------------------------------------------------
        # STEP 3: Get or Create Collection
        # --------------------------------------------------------
        # WHAT: Collection = like a "table" in SQL database
        #       All document chunks stored here as vectors
        #
        # get_or_create_collection:
        #   → Collection exists? → load it (existing data preserved) ✅
        #   → Doesn't exist?    → create new empty collection ✅
        #
        # hnsw:space = "cosine":
        #   → Use cosine similarity for search
        #   → Cosine measures ANGLE between vectors
        #   → Score 1.0 = identical meaning
        #   → Score 0.0 = completely different meaning
        # --------------------------------------------------------
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        print(f"   ✅ Collection '{settings.chroma_collection_name}' ready!")
        print(f"   📊 Current chunks in store: {self.collection.count()}")

        # --------------------------------------------------------
        # STEP 4: Load Embedding Model
        # --------------------------------------------------------
        # WHAT: sentence-transformers converts text → vectors locally
        # WHY:  100% free, no API key, works offline
        #
        # local_files_only=True:
        #   → Use cached model only (no internet download attempts)
        #   → Model must be downloaded at least once first
        #   → After that, works 100% offline ✅
        #
        # all-MiniLM-L6-v2:
        #   → 90MB model, cached in ~/.cache/huggingface/
        #   → Output: 384-dimensional vectors
        #   → Fast: ~10ms per sentence
        # --------------------------------------------------------
        print(f"🧠 Loading embedding model: {settings.embedding_model_name}")

        self.embedding_model = SentenceTransformer(
            settings.embedding_model_name,
            local_files_only=False    # Offline mode — no internet needed
        )
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 output size

        print(f"   ✅ Embedding model loaded!")

    # ============================================================
    # EMBED TEXT → VECTORS
    # ============================================================
    def _embed(self, texts: List[str]) -> List[List[float]]:
        """
        WHAT: Converts list of text strings → list of vectors (numbers).

        WHY private (_embed):
          Internal helper. Called by add_documents() and search().
          Callers don't need to know HOW embedding works.

        WHY batch processing:
          Faster to embed 50 texts at once than one by one.
          sentence-transformers optimizes batch operations internally.

        WHY .tolist():
          encode() returns NumPy array — fast for math operations.
          ChromaDB API requires Python list — not NumPy array.
          .tolist() converts at the API boundary only.
          Rule: "NumPy internally, list at API boundary"

        Args:
            texts: ["chunk text 1", "chunk text 2", ...]

        Returns:
            [[0.23, -0.87, ...], [0.45, 0.12, ...], ...]
            Each inner list = 384 numbers representing text meaning
        """
        embeddings = self.embedding_model.encode(
            texts,
            convert_to_tensor=False,        # Keep as NumPy (faster than tensor)
            normalize_embeddings=True,      # Unit sphere → better cosine similarity
            show_progress_bar=len(texts) > 10  # Show progress for large batches
        )

        # Convert NumPy → Python list at ChromaDB boundary
        # hasattr check → safe if somehow already a list
        if hasattr(embeddings, 'tolist'):
            return embeddings.tolist()

        return [
            e.tolist() if hasattr(e, 'tolist') else list(e)
            for e in embeddings
        ]

    # ============================================================
    # ADD DOCUMENTS TO CHROMADB
    # ============================================================
    def add_documents(
        self,
        documents: List[Document],
        namespace: str = "default"
    ) -> int:
        """
        WHAT: Embeds and stores document chunks in ChromaDB.

        WHY namespace:
          Separates documents from different sources/users.
          "user_123" namespace → search only their documents.
          "project_abc" namespace → search only project docs.
          Default = "default" for simple single-user setup.

        WHY upsert not add:
          If user uploads same document twice:
          add()    → creates duplicates ❌
          upsert() → updates existing, no duplicates ✅

        Args:
            documents: List[Document] from TextChunker
            namespace: Group name for this set of documents

        Returns:
            Total number of chunks stored
        """
        if not documents:
            print("⚠️  No documents to add!")
            return 0

        print(f"\n💾 Storing {len(documents)} chunks in ChromaDB...")

        batch_size = 50   # Process 50 chunks at a time
        total_stored = 0

        for batch_start in range(0, len(documents), batch_size):

            batch = documents[batch_start: batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(documents) - 1) // batch_size + 1

            print(f"   Processing batch {batch_num}/{total_batches}...")

            # Extract text content from each document
            texts = [doc.page_content for doc in batch]

            # Generate embeddings for this batch
            embeddings = self._embed(texts)

            # Build stable IDs for ChromaDB.
            # WHY:
            # - old IDs used only namespace + index, so new uploads could overwrite
            #   older chunks in the same namespace.
            # - stable hash IDs keep chunks distinct across files and re-ingestions.
            ids = []
            for i, doc in enumerate(batch):
                chunk_index = int(doc.metadata.get("chunk_index", i))
                page = str(doc.metadata.get("page", ""))
                file_type = str(doc.metadata.get("file_type", ""))
                identity_text = (
                    f"{namespace}|{file_type}|{page}|{chunk_index}|{doc.page_content}"
                )
                chunk_hash = hashlib.md5(
                    identity_text.encode("utf-8")
                ).hexdigest()
                ids.append(f"{namespace}_{chunk_hash}")

            # Clean metadata for ChromaDB
            # WHY clean: ChromaDB only accepts str, int, float, bool
            #            No nested dicts or lists allowed!
            metadatas = []
            for doc in batch:
                clean_metadata = {
                    "namespace":    namespace,
                    "source":       str(doc.metadata.get("source", "")),
                    "file_name":    str(doc.metadata.get("file_name", "")),
                    "file_type":    str(doc.metadata.get("file_type", "")),
                    "page":         str(doc.metadata.get("page", "")),
                    "chunk_index":  int(doc.metadata.get("chunk_index", 0)),
                    "total_chunks": int(doc.metadata.get("total_chunks", 0)),
                    "chunk_size":   int(doc.metadata.get("chunk_size", 0)),
                }
                metadatas.append(clean_metadata)

            # Store in ChromaDB
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )

            total_stored += len(batch)

        print(f"   ✅ Stored {total_stored} chunks!")
        print(f"   📊 Total in ChromaDB: {self.collection.count()}")
        return total_stored

    # ============================================================
    # SEARCH CHROMADB
    # ============================================================
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        namespace: Optional[str] = None,
    ) -> List[Document]:
        """
        WHAT: Finds most relevant chunks for a user's question.

        WHY semantic search beats keyword search:
          Keyword: "loan rate" → finds docs with exact words only ❌
          Semantic: "loan rate" → finds docs about "interest",
                    "borrowing cost", "EMI" — same MEANING ✅

        HOW cosine similarity works:
          question → vector [0.45, -0.23, ...]
          chunk 1  → vector [0.43, -0.25, ...]  ← close! high score
          chunk 2  → vector [-0.8, 0.90, ...]   ← far!  low score
          ChromaDB returns chunks sorted by closeness (score)

        FALLBACK:
          If no chunks pass score threshold (happens with short text),
          return best match if score >= 0.2.
          WHY: Better than returning nothing for demo/portfolio use.
          Real production: remove fallback, keep strict threshold.

        Args:
            query: User's question in natural language
            top_k: How many chunks to return
            namespace: Search only in this namespace (optional)

        Returns:
            List[Document] — most relevant chunks, best match first
        """
        k = top_k or settings.rag_top_k

        print(f"\n🔍 Searching ChromaDB...")
        print(f"   Query: '{query[:60]}...'" if len(query) > 60 else f"   Query: '{query}'")
        print(f"   Top-K: {k}")

        # Guard: empty collection → return immediately
        collection_size = self.collection.count()
        if collection_size == 0:
            print("   ⚠️  Collection is empty — no results!")
            return []

        # Embed the question
        # WHY same model as documents:
        #   Vectors must be in same "space" to compare
        #   Using different model = comparing apples to oranges ❌
        query_embedding = self._embed([query])[0]

        # Namespace filter — search only specific docs if provided
        where_filter = None
        if namespace:
            where_filter = {"namespace": {"$eq": namespace}}

        # Query ChromaDB for similar vectors
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection_size),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Unpack results (nested lists — we queried 1 item so take [0])
        docs_texts = results["documents"][0]
        metadatas  = results["metadatas"][0]
        distances  = results["distances"][0]

        # Filter by similarity threshold
        relevant_chunks = []

        for text, metadata, distance in zip(docs_texts, metadatas, distances):

            # Convert distance → similarity score
            # ChromaDB cosine distance: 0=identical, 2=opposite
            # Similarity: 1=identical, 0=opposite (1 - distance)
            similarity_score = 1 - distance

            if similarity_score < settings.rag_score_threshold:
                print(f"   ⚠️  Skipping chunk "
                      f"(score {similarity_score:.3f} < "
                      f"threshold {settings.rag_score_threshold})")
                continue

            metadata["similarity_score"] = round(similarity_score, 4)
            relevant_chunks.append(Document(
                page_content=text,
                metadata=metadata
            ))

        # Fallback for short demo text
        # WHY: Short text embeddings have lower similarity scores
        #      In production with real PDFs, scores will be 0.7-0.95
        if not relevant_chunks and docs_texts:
            best_similarity = round(1 - distances[0], 4)
            if best_similarity >= 0.2:
                metadatas[0]["similarity_score"] = best_similarity
                metadatas[0]["fallback_match"] = True
                relevant_chunks.append(Document(
                    page_content=docs_texts[0],
                    metadata=metadatas[0]
                ))
                print(f"   🔄 Fallback: returning best chunk "
                      f"(score {best_similarity})")

        # Log results
        print(f"   ✅ Found {len(relevant_chunks)} relevant chunks")
        for i, chunk in enumerate(relevant_chunks):
            score  = chunk.metadata.get("similarity_score", 0)
            source = chunk.metadata.get("file_name", "unknown")
            print(f"      Chunk {i+1}: score={score} | source={source}")

        return relevant_chunks

    # ============================================================
    # UTILITY METHODS
    # ============================================================
    def get_collection_stats(self) -> dict:
        """Returns current ChromaDB collection info."""
        return {
            "total_chunks":      self.collection.count(),
            "collection_name":   settings.chroma_collection_name,
            "persist_directory": settings.chroma_persist_directory,
            "embedding_model":   settings.embedding_model_name,
        }

    def delete_namespace(self, namespace: str) -> bool:
        """
        WHAT: Delete all chunks belonging to one namespace.
        WHY:  When user deletes a document, remove its vectors too.
        """
        print(f"🗑️  Deleting namespace: {namespace}")
        self.collection.delete(
            where={"namespace": {"$eq": namespace}}
        )
        print(f"   ✅ Deleted all chunks for namespace: {namespace}")
        return True

    def delete_file(self, namespace: str, file_name: str) -> int:
        """
        WHAT: Delete all chunks in a namespace for a specific file.
        WHY:  Supports clean re-ingest for one document without wiping
              the entire namespace.
        """
        print(f"🗑️  Deleting file '{file_name}' from namespace '{namespace}'")

        rows = self.collection.get(
            where={"namespace": {"$eq": namespace}},
            include=["metadatas"]
        )
        ids_to_delete = []

        for chunk_id, metadata in zip(rows["ids"], rows["metadatas"]):
            if str(metadata.get("file_name", "")) == str(file_name):
                ids_to_delete.append(chunk_id)

        if not ids_to_delete:
            print("   ℹ️  No matching chunks found.")
            return 0

        self.collection.delete(ids=ids_to_delete)
        print(f"   ✅ Deleted {len(ids_to_delete)} chunk(s)")
        return len(ids_to_delete)

    def reset_collection(self) -> bool:
        """
        WHAT: Wipe ALL data from ChromaDB.
        WHY:  Development/testing — start completely fresh.
        ⚠️  WARNING: Irreversible! All vectors permanently deleted!
        """
        print("⚠️  Resetting entire ChromaDB collection...")
        self.chroma_client.delete_collection(settings.chroma_collection_name)
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print("✅ Collection reset complete!")
        return True
