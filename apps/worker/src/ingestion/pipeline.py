
"""
INGESTION PIPELINE
==================
WHAT:  Orchestrates full document ingestion:
       File/URL → Load → Chunk → Embed → Store in ChromaDB

WHY:   Single entry point for adding documents to knowledge base.
       api/main.py just calls pipeline.ingest(source) — done!

WHERE: Called by src/api/main.py
       POST /ingest/file → pipeline.ingest(file_path, namespace)
       POST /ingest/url  → pipeline.ingest(url, namespace)

WHEN:  User uploads a document via frontend.

FLOW:
       Source (file path or URL)
              ↓
       DocumentLoader.load()     → List[LoadedDocument]
              ↓
       TextChunker.chunk()       → List[Document] (chunks)
              ↓
       ChromaVectorStore.add_documents() → stored in ChromaDB
              ↓
       Return ingestion stats dict
"""

import os
import hashlib
from pathlib import Path
from typing import List, Optional

from src.ingestion.loaders.document_loader import DocumentLoader
from src.ingestion.chunkers.text_chunker import TextChunker
from src.retrieval.vector_store.chroma_store import ChromaVectorStore
from src.config import settings


class IngestionPipeline:
    """
    WHAT: Full document ingestion orchestrator.

    WHY ONE CLASS:
      All ingestion logic in one place.
      API layer stays clean — just calls ingest().

    USAGE:
      pipeline = IngestionPipeline()

      # Ingest a file
      result = pipeline.ingest("docs/gold_loan.pdf")

      # Ingest a URL
      result = pipeline.ingest("https://smartspend.ai/faq")

      # Ingest multiple files at once
      results = pipeline.ingest_multiple([
          "docs/gold_loan.pdf",
          "docs/pricing.pdf",
          "https://smartspend.ai/help"
      ])

      print(result)
      # {
      #   "status": "success",
      #   "source": "gold_loan.pdf",
      #   "chunks_created": 42,
      #   "namespace": "default"
      # }
    """

    def __init__(self):
        """
        WHAT: Initialize all pipeline components.

        WHY initialize once:
          ChromaVectorStore loads embedding model (~90MB) on init.
          Expensive operation — do it ONCE, reuse for all ingestions.
          FastAPI creates ONE pipeline instance, reuses for all requests.
        """
        print("🏗️  Initializing Ingestion Pipeline...")

        self.loader   = DocumentLoader()
        self.chunker  = TextChunker()
        self.store    = ChromaVectorStore()

        # Track ingested files to prevent duplicates
        # WHY dict: filename → chunk_count (easy lookup)
        # NOTE: In production use Redis/DB for persistence
        #       For portfolio: in-memory dict is fine
        self._ingested_files: dict = {}

        print("✅ Ingestion Pipeline ready!\n")

    # ============================================================
    # MAIN INGEST METHOD
    # ============================================================
    def ingest(
        self,
        source: str,
        namespace: str = "default",
        force_reingest: bool = False,
        display_file_name: Optional[str] = None,
    ) -> dict:
        """
        WHAT: Full pipeline — source → stored in ChromaDB.

        WHY force_reingest param:
          Default behavior: skip if already ingested (no duplicates)
          force_reingest=True: re-ingest even if already processed
          
          Use case: user uploads updated version of same document
          → force_reingest=True to replace old vectors with new ones

        WHY namespace:
          Groups documents together.
          Search can be scoped to specific namespace.
          "default" = all documents mixed together (fine for portfolio)
          "user_123" = only this user's documents (for multi-user)

        Args:
            source:         File path OR URL string
            namespace:      ChromaDB namespace for this document
            force_reingest: Skip duplicate check if True
            display_file_name: Original filename for user-facing metadata
                               (useful when source is a temporary upload path)

        Returns:
            dict with ingestion stats:
            {
              "status": "success" | "skipped" | "failed",
              "source": "gold_loan.pdf",
              "file_name": "gold_loan.pdf",
              "chunks_created": 42,
              "namespace": "default",
              "message": "Successfully ingested..."
            }
        """
        source = source.strip()
        file_name = display_file_name or self._get_source_name(source)

        print(f"\n{'=' * 55}")
        print(f"📥 Ingesting: {file_name}")
        print(f"   Namespace: {namespace}")
        print(f"{'=' * 55}")

        # --------------------------------------------------------
        # DUPLICATE CHECK
        # --------------------------------------------------------
        # WHY: Prevent same document being stored multiple times
        #      Duplicates waste ChromaDB space + hurt search quality
        #      (same chunk appears twice = artificially boosted rank)
        #
        # HOW: Track ingested sources in memory dict
        #      Key = source path/URL
        #      Value = number of chunks stored
        # --------------------------------------------------------
        source_key = f"{namespace}_{file_name}"

        if not force_reingest and source_key in self._ingested_files:
            existing_chunks = self._ingested_files[source_key]
            print(f"   ⏭️  Already ingested! ({existing_chunks} chunks)")
            print(f"   Use force_reingest=True to re-process.")
            return {
                "status":        "skipped",
                "source":        source,
                "file_name":     file_name,
                "chunks_created": existing_chunks,
                "namespace":     namespace,
                "message":       f"Already ingested ({existing_chunks} chunks). "
                                 f"Use force_reingest=True to update."
            }

        try:
            # --------------------------------------------------------
            # STEP 1: LOAD
            # --------------------------------------------------------
            # WHAT: Read file/URL → extract raw text
            # WHY:  Can't process binary PDF/DOCX directly
            # --------------------------------------------------------
            print(f"\n📖 Step 1/3: Loading document...")
            loaded_docs = self.loader.load(source)

            # Preserve original upload filename in metadata.
            # WHY: uploaded files are written to temporary paths (tmp*.pdf),
            # but users should see the real filename in citations/sources.
            if display_file_name:
                for loaded_doc in loaded_docs:
                    loaded_doc.metadata["file_name"] = display_file_name

            if not loaded_docs:
                return {
                    "status":    "failed",
                    "source":    source,
                    "file_name": file_name,
                    "message":   "Document loaded but no text extracted. "
                                 "Check if file is empty or image-only PDF."
                }

            total_chars = sum(len(d.content) for d in loaded_docs)
            print(f"   ✅ Loaded {len(loaded_docs)} section(s), "
                  f"{total_chars:,} characters total")

            # --------------------------------------------------------
            # STEP 2: CHUNK
            # --------------------------------------------------------
            # WHAT: Split text → smaller searchable pieces
            # WHY:  LLM token limits + better search accuracy
            # --------------------------------------------------------
            print(f"\n✂️  Step 2/3: Chunking text...")
            chunks = self.chunker.chunk(loaded_docs)

            if not chunks:
                return {
                    "status":    "failed",
                    "source":    source,
                    "file_name": file_name,
                    "message":   "Text loaded but chunking produced no results. "
                                 "Document may be too short."
                }

            print(f"   ✅ Created {len(chunks)} chunks "
                  f"(size={settings.rag_chunk_size}, "
                  f"overlap={settings.rag_chunk_overlap})")

            # --------------------------------------------------------
            # STEP 3: EMBED + STORE
            # --------------------------------------------------------
            # WHAT: Convert chunks → vectors → save in ChromaDB
            # WHY:  Enables semantic search later
            # --------------------------------------------------------
            print(f"\n💾 Step 3/3: Embedding and storing in ChromaDB...")

            # If force re-ingesting, delete old vectors first
            # WHY: Prevent duplicates when updating a document
            if force_reingest and source_key in self._ingested_files:
                print(f"   🗑️  Removing old vectors (force reingest)...")
                self.store.delete_file(namespace=namespace, file_name=file_name)

            stored_count = self.store.add_documents(
                chunks,
                namespace=namespace
            )

            # Track this ingestion to prevent future duplicates
            self._ingested_files[source_key] = stored_count

            # --------------------------------------------------------
            # SUCCESS
            # --------------------------------------------------------
            print(f"\n{'=' * 55}")
            print(f"✅ Ingestion Complete!")
            print(f"   File:   {file_name}")
            print(f"   Chunks: {stored_count}")
            print(f"   Namespace: {namespace}")
            print(f"{'=' * 55}\n")

            return {
                "status":         "success",
                "source":         source,
                "file_name":      file_name,
                "sections_loaded": len(loaded_docs),
                "chunks_created": stored_count,
                "total_chars":    total_chars,
                "namespace":      namespace,
                "message":        f"Successfully ingested {stored_count} "
                                  f"chunks from {file_name}"
            }

        except FileNotFoundError as e:
            print(f"❌ File not found: {e}")
            return {
                "status":    "failed",
                "source":    source,
                "file_name": file_name,
                "message":   f"File not found: {source}"
            }

        except Exception as e:
            print(f"❌ Ingestion failed: {e}")
            return {
                "status":    "failed",
                "source":    source,
                "file_name": file_name,
                "message":   f"Ingestion failed: {str(e)}"
            }

    # ============================================================
    # INGEST MULTIPLE SOURCES
    # ============================================================
    def ingest_multiple(
        self,
        sources: List[str],
        namespace: str = "default",
        force_reingest: bool = False
    ) -> dict:
        """
        WHAT: Ingest multiple files/URLs in one call.

        WHY:
          User might upload 5 PDFs at once.
          This handles all of them, returns combined stats.
          Continues even if one file fails (doesn't stop pipeline).

        Args:
            sources:        List of file paths or URLs
            namespace:      ChromaDB namespace
            force_reingest: Re-ingest even if already processed

        Returns:
            {
              "total": 5,
              "success": 4,
              "failed": 1,
              "skipped": 0,
              "total_chunks": 210,
              "results": [...]   ← individual result per source
            }
        """
        print(f"\n📦 Ingesting {len(sources)} sources...")

        results       = []
        success_count = 0
        failed_count  = 0
        skipped_count = 0
        total_chunks  = 0

        for i, source in enumerate(sources, 1):
            print(f"\n[{i}/{len(sources)}] Processing: {source}")

            result = self.ingest(
                source=source,
                namespace=namespace,
                force_reingest=force_reingest
            )
            results.append(result)

            if result["status"] == "success":
                success_count += 1
                total_chunks  += result.get("chunks_created", 0)
            elif result["status"] == "failed":
                failed_count += 1
            elif result["status"] == "skipped":
                skipped_count += 1

        # Summary
        print(f"\n{'=' * 55}")
        print(f"📊 Batch Ingestion Summary:")
        print(f"   Total sources:  {len(sources)}")
        print(f"   ✅ Success:     {success_count}")
        print(f"   ❌ Failed:      {failed_count}")
        print(f"   ⏭️  Skipped:    {skipped_count}")
        print(f"   📦 Total chunks: {total_chunks}")
        print(f"{'=' * 55}\n")

        return {
            "total":        len(sources),
            "success":      success_count,
            "failed":       failed_count,
            "skipped":      skipped_count,
            "total_chunks": total_chunks,
            "results":      results
        }

    # ============================================================
    # UTILITY METHODS
    # ============================================================
    def get_stats(self) -> dict:
        """
        WHAT: Returns current pipeline + ChromaDB stats.
        WHY:  Useful for admin dashboard or health checks.
        """
        store_stats = self.store.get_collection_stats()
        return {
            **store_stats,
            "ingested_sources": len(self._ingested_files),
            "tracked_files":    list(self._ingested_files.keys()),
        }

    def reset(self) -> bool:
        """
        WHAT: Wipe ChromaDB + reset tracking.
        WHY:  Development/testing — start completely fresh.
        ⚠️  WARNING: Deletes ALL ingested documents!
        """
        print("⚠️  Resetting pipeline — ALL data will be deleted!")
        self.store.reset_collection()
        self._ingested_files.clear()
        print("✅ Pipeline reset complete!")
        return True

    def _get_source_name(self, source: str) -> str:
        """
        WHAT: Extracts human-readable name from source path/URL.

        Examples:
          "C:/docs/gold_loan.pdf" → "gold_loan.pdf"
          "https://smartspend.ai/faq" → "smartspend.ai/faq"
          "test_doc.txt" → "test_doc.txt"
        """
        if source.startswith("http://") or source.startswith("https://"):
            # URL → remove protocol prefix
            return source.replace("https://", "").replace("http://", "")

        # File path → just the filename
        return Path(source).name
