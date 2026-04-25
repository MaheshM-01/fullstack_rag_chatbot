
"""
RAG CHAIN
=========
WHAT:  Orchestrates the full RAG pipeline.
       Connects ChromaDB retrieval + Groq generation together.

WHY:   Single entry point for answering questions.
       api/main.py just calls chain.answer(question) — done!
       All complexity hidden inside this file.

WHERE: Called by src/api/main.py
       chain = RAGChain()
       result = chain.answer("What is gold loan rate?")

WHEN:  Every time user sends a message in chat.

PIPELINE:
       Question
          ↓
       [Optional] Condense follow-up question (if chat history exists)
          ↓
       ChromaDB search → retrieve relevant chunks
          ↓
       Format context + chat history
          ↓
       Build RAG prompt
          ↓
       Groq LLM generates answer
          ↓
       Return {answer, sources, chunks_used}
"""

from typing import Generator, Optional
from langchain.schema import Document

from src.retrieval.vector_store.chroma_store import ChromaVectorStore
from src.generation.llm.groq_client import GroqLLMClient
from src.generation.prompts.templates import (
    RAG_PROMPT_TEMPLATE,
    ANSWER_REWRITE_PROMPT_TEMPLATE,
    CONDENSE_QUESTION_PROMPT,
    NO_CONTEXT_PROMPT,
    format_chat_history,
    format_context,
)
from src.config import settings


class RAGChain:
    """
    WHAT: Full RAG pipeline orchestrator.

    WHY ONE CLASS:
      All RAG logic in one place.
      FastAPI just calls: chain.answer(question)
      No need to know about ChromaDB, Groq, or prompts.

    USAGE:
      # Initialize once (expensive — loads models)
      chain = RAGChain()

      # Call many times (fast — models already loaded)
      result = chain.answer("What is gold loan rate?")
      print(result["answer"])
      print(result["sources"])

      # With chat history (follow-up questions)
      history = [{"question": "...", "answer": "..."}]
      result = chain.answer("What about EMI?", chat_history=history)

      # Streaming (for real-time chat UI)
      for token in chain.stream("What is gold loan rate?"):
          print(token, end="", flush=True)
    """

    def __init__(self, namespace: str = "default"):
        """
        WHAT: Initialize all components.

        WHY namespace param:
          Namespace = which set of documents to search.
          "default"   → all documents
          "user_123"  → only this user's documents
          "project_x" → only project X documents

          For portfolio project → "default" is fine.
          For multi-user production → use user ID as namespace.

        Args:
            namespace: ChromaDB namespace to search in
        """
        print("\n🔗 Initializing RAG Chain...")
        print("=" * 50)

        self.namespace = namespace

        # Initialize ChromaDB vector store
        # WHY: Loads embedding model + connects to ChromaDB
        self.vector_store = ChromaVectorStore()

        # Initialize Groq LLM client
        # WHY: Validates API key + sets up Groq connection
        self.llm = GroqLLMClient()

        print("=" * 50)
        print("✅ RAG Chain ready!\n")

    # ============================================================
    # MAIN METHOD — Answer a question
    # ============================================================
    def answer(
        self,
        question: str,
        chat_history: list = [],
        namespace: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> dict:
        """
        WHAT: Full RAG pipeline — question in, answer dict out.

        RETURNS dict with:
          answer       → The generated answer string
          sources      → List of source documents used
          chunks_used  → How many chunks retrieved
          question     → Original question (for logging)
          has_context  → Whether relevant docs were found

        WHY return dict (not just string):
          Frontend needs more than just the answer text.
          It also needs:
            sources → show "Answer from: gold_loan.pdf, Page 3"
            chunks_used → show "Based on 3 documents"
          Dict gives frontend all needed info in one response.

        Args:
            question:     User's question string
            chat_history: Previous Q&A pairs for follow-up support
            namespace:    Override default namespace if needed
            top_k:        Override default top-K chunks if needed

        Returns:
            {
              "answer": "The interest rate is 12%...",
              "sources": [{"file": "gold_loan.pdf", "page": "3"}],
              "chunks_used": 2,
              "question": "What is gold loan rate?",
              "has_context": True
            }
        """
        search_namespace = namespace or self.namespace
        k = top_k or settings.rag_top_k

        print(f"\n{'=' * 50}")
        print(f"❓ Question: {question}")
        print(f"{'=' * 50}")

        # --------------------------------------------------------
        # STEP 1: Condense follow-up question (if history exists)
        # --------------------------------------------------------
        # WHY:
        #   User: "What is gold loan rate?" → Answer: "12%"
        #   User: "What about EMI?"
        #
        #   "What about EMI?" alone = ambiguous for ChromaDB search
        #   Condensed: "What is the EMI for gold loan?" = clear ✅
        #
        # WHEN: Only if chat_history is not empty
        # --------------------------------------------------------
        search_question = question  # Default: use original question

        if chat_history:
            print("📝 Condensing follow-up question...")
            search_question = self._condense_question(
                question, chat_history
            )
            if search_question != question:
                print(f"   Original:  '{question}'")
                print(f"   Condensed: '{search_question}'")

        # --------------------------------------------------------
        # STEP 2: Retrieve relevant chunks from ChromaDB
        # --------------------------------------------------------
        # WHY condensed question for search (not original):
        #   Condensed question has full context → better search results
        #   Original ambiguous question → poor search results
        # --------------------------------------------------------
        print(f"\n🔍 Step 1: Retrieving from ChromaDB...")
        chunks = self.vector_store.search(
            query=search_question,
            top_k=k,
            namespace=search_namespace if search_namespace != "default" else None
        )

        # --------------------------------------------------------
        # STEP 3: Handle case where no relevant chunks found
        # --------------------------------------------------------
        # WHY: Better UX to say "no docs found" than hallucinate
        # --------------------------------------------------------
        if not chunks:
            print("   ⚠️  No relevant chunks found!")
            print("   🤖 Using fallback prompt...")

            # Use fallback prompt (no context)
            fallback_prompt = NO_CONTEXT_PROMPT.format(
                question=question
            )
            fallback_answer = self.llm.generate(
                fallback_prompt,
                max_tokens=256,    # Short response for no-context case
                temperature=0.3
            )

            return {
                "answer":      fallback_answer,
                "sources":     [],
                "chunks_used": 0,
                "question":    question,
                "has_context": False
            }

        # --------------------------------------------------------
        # STEP 4: Format context and history for prompt
        # --------------------------------------------------------
        print(f"\n📋 Step 2: Building prompt...")

        # Format chunks → readable context string
        context_str = format_context(chunks)

        # Format chat history → readable string
        history_str = format_chat_history(chat_history)

        # Build complete RAG prompt
        # WHY use original question (not condensed) here:
        #   Condensed question was for SEARCH accuracy
        #   Original question is what user actually asked
        #   LLM should answer what user asked, not rewritten version
        full_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context_str,
            chat_history=history_str,
            question=question         # Original question here!
        )

        print(f"   Context chunks: {len(chunks)}")
        print(f"   Prompt length: {len(full_prompt)} chars")

        # --------------------------------------------------------
        # STEP 5: Generate answer with Groq
        # --------------------------------------------------------
        print(f"\n🤖 Step 3: Generating answer with Groq...")

        answer_text = self.llm.generate(
            prompt=full_prompt,
            max_tokens=1024,
            temperature=0.1    # Low temperature = factual, accurate
        )

        # Guardrail: sometimes LLM returns source-summary style text
        # instead of directly answering the question.
        # If detected, run one rewrite pass with stricter instructions.
        if self._looks_like_meta_answer(answer_text):
            print("   ⚠️  Meta-style answer detected, rewriting...")
            rewrite_prompt = ANSWER_REWRITE_PROMPT_TEMPLATE.format(
                question=question,
                context=context_str,
                draft_answer=answer_text,
            )
            answer_text = self.llm.generate(
                prompt=rewrite_prompt,
                max_tokens=1024,
                temperature=0.0
            )

        # --------------------------------------------------------
        # STEP 6: Extract source citations
        # --------------------------------------------------------
        sources = self._extract_sources(chunks)

        # --------------------------------------------------------
        # STEP 7: Return complete result
        # --------------------------------------------------------
        print(f"\n✅ Answer generated!")
        print(f"   Answer length: {len(answer_text)} chars")
        print(f"   Sources used: {[s['file'] for s in sources]}")

        return {
            "answer":      answer_text,
            "sources":     sources,
            "chunks_used": len(chunks),
            "question":    question,
            "has_context": True
        }

    # ============================================================
    # STREAMING METHOD — token by token response
    # ============================================================
    def stream(
        self,
        question: str,
        chat_history: list = [],
        namespace: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        WHAT: Stream RAG answer token by token.

        WHY STREAMING FOR CHAT UI:
          Normal: User waits 5-10 seconds → answer appears all at once
                  Bad UX — feels slow and unresponsive ❌

          Stream: Answer appears word by word immediately
                  Like ChatGPT — feels fast and responsive ✅

        HOW:
          Same pipeline as answer() but:
          → Uses llm.stream() instead of llm.generate()
          → Yields each token immediately as Groq sends it
          → FastAPI sends each token to frontend via StreamingResponse

        Usage in FastAPI:
          return StreamingResponse(
              chain.stream(question),
              media_type="text/plain"
          )

        Usage in terminal (testing):
          for token in chain.stream("What is gold loan rate?"):
              print(token, end="", flush=True)

        Yields:
            Individual text tokens: "The", " rate", " is", " 12%"...
        """
        search_namespace = namespace or self.namespace

        # Condense question if follow-up
        search_question = question
        if chat_history:
            search_question = self._condense_question(
                question, chat_history
            )

        # Retrieve chunks
        chunks = self.vector_store.search(
            query=search_question,
            namespace=search_namespace if search_namespace != "default" else None
        )

        # No context fallback
        if not chunks:
            fallback_prompt = NO_CONTEXT_PROMPT.format(question=question)
            yield from self.llm.stream(fallback_prompt, max_tokens=256)
            return

        # Build prompt
        full_prompt = RAG_PROMPT_TEMPLATE.format(
            context=format_context(chunks),
            chat_history=format_chat_history(chat_history),
            question=question
        )

        # Stream answer token by token
        yield from self.llm.stream(full_prompt)

    # ============================================================
    # PRIVATE HELPER METHODS
    # ============================================================
    def _condense_question(
        self,
        question: str,
        chat_history: list
    ) -> str:
        """
        WHAT: Rewrites ambiguous follow-up questions to standalone.

        WHY:
          "What about the EMI?" → needs context to understand
          "What is the EMI for gold loan?" → standalone, searchable

        HOW:
          Uses CONDENSE_QUESTION_PROMPT template
          Sends to Groq with low max_tokens (just needs one sentence)
          Returns rewritten question string

        Args:
            question:     Follow-up question from user
            chat_history: Previous conversation exchanges

        Returns:
            Standalone question string ready for ChromaDB search
        """
        # Only condense if there's actual history to use
        if not chat_history:
            return question

        history_str = format_chat_history(chat_history)

        condense_prompt = CONDENSE_QUESTION_PROMPT.format(
            chat_history=history_str,
            question=question
        )

        try:
            # Low max_tokens — just need a single rewritten question
            condensed = self.llm.generate(
                prompt=condense_prompt,
                max_tokens=100,
                temperature=0.0    # Deterministic — no creativity needed
            )
            return condensed.strip()

        except Exception as e:
            # If condensing fails → use original question
            # WHY: Better to search with original than crash
            print(f"   ⚠️  Question condensing failed: {e}")
            print(f"   Using original question instead.")
            return question

    def _looks_like_meta_answer(self, answer: str) -> bool:
        """
        WHAT: Detects weak responses that describe documents
              without directly answering the question.

        WHY:
          Users reported answers like:
          "According to Document 1, this section covers..."
          which is metadata-style output, not an actual answer.
        """
        if not answer:
            return False

        normalized = " ".join(answer.lower().split())
        meta_markers = [
            "according to document",
            "this section covers",
            "the section covers",
            "the document covers",
            "the document discusses",
            "according to [document",
        ]

        return any(marker in normalized for marker in meta_markers)

    def _extract_sources(self, chunks: list) -> list:
        """
        WHAT: Extracts source citation info from retrieved chunks.

        WHY:
          Frontend shows: "Answer from: gold_loan.pdf (Page 3)"
          User knows WHERE the answer came from → builds trust.

        WHY deduplicate:
          Multiple chunks might come from same page of same file.
          We show each source ONCE — not repeatedly.

        Args:
            chunks: List[Document] from ChromaDB search

        Returns:
            List of unique source dicts:
            [{"file": "gold_loan.pdf", "page": "3", "score": 0.85}]
        """
        sources = []
        seen_sources = set()

        for chunk in chunks:
            file_name = chunk.metadata.get("file_name", "Unknown")
            page      = chunk.metadata.get("page", "")
            score     = chunk.metadata.get("similarity_score", 0)

            # Create unique key to deduplicate
            # WHY: Same file+page might appear in multiple chunks
            source_key = f"{file_name}_{page}"

            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "file":    file_name,
                    "page":    page,
                    "score":   score,
                    "preview": chunk.page_content[:150] + "..."
                    if len(chunk.page_content) > 150
                    else chunk.page_content
                })

        return sources
