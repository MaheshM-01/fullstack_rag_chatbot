
"""
PROMPT TEMPLATES
================
WHAT:  All LLM prompt templates in one place.
       Templates = instructions + placeholders for dynamic content.

WHY:   Prompt quality directly affects answer quality.
       Separate file = easy to tune without touching chain logic.

WHERE: Used by src/generation/chain.py
       chain.py imports these templates, fills variables, sends to Groq.

WHEN:  Every time user asks a question.

HOW PROMPT ENGINEERING WORKS:
       Good prompt = clear role + strict rules + structured format
       
       Role:  "You are a helpful assistant for SmartSpend AI"
              → LLM knows its persona and purpose
       
       Rules: "Answer ONLY from context below"
              → Prevents hallucination (making up facts)
       
       Format: "Cite your sources"
               → User knows WHERE answer came from
"""


# ============================================================
# MAIN RAG PROMPT
# ============================================================
# WHAT: Primary prompt used for all Q&A in this RAG system.
#
# WHY EACH SECTION:
#
# ROLE SECTION:
#   Tells LLM WHO it is and WHAT it does.
#   LLMs perform better with clear persona.
#   "helpful, accurate, honest" → guides tone of answers.
#
# STRICT RULES:
#   Rule 1 — "ONLY from context"
#     → Prevents LLM from using outside knowledge
#     → All answers grounded in YOUR documents ✅
#
#   Rule 2 — "say I don't know"
#     → Better to admit than hallucinate wrong answer
#     → Builds user trust in the system
#
#   Rule 3 — cite sources
#     → User knows which document answered their question
#     → Increases credibility of answers
#
#   Rule 4 — language matching
#     → User asks in Tamil → answer in Tamil
#     → Better UX for multilingual users
#
#   Rule 5 — no repetition
#     → Professional, clean responses
#
# CONTEXT SECTION:
#   {context} placeholder filled with ChromaDB retrieved chunks
#   Each chunk labeled [Document 1], [Document 2] etc.
#   LLM reads these to find the answer
#
# CHAT HISTORY SECTION:
#   {chat_history} = last 5 exchanges
#   WHY: User might ask follow-up questions
#   "What about the EMI?" (after asking about gold loan)
#   Without history → LLM doesn't know what "it" refers to ❌
#   With history → LLM understands context ✅
#
# QUESTION + ANSWER:
#   {question} = current user question
#   "ANSWER:" → prompts LLM to start responding
# ============================================================

RAG_PROMPT_TEMPLATE = """You are a helpful, accurate, and honest AI assistant.
Your job is to answer questions from the provided context documents.

STRICT RULES - Follow these exactly:
1. Use ONLY the information from CONTEXT DOCUMENTS.
   Do not use outside knowledge or guess missing facts.
2. Start with a direct answer to the user's question in the first sentence.
3. Do NOT write meta responses like:
   - "According to Document X..."
   - "This section covers..."
   - "The document discusses..."
   Instead, give the actual definition/explanation/fact.
4. If the context does not contain enough details to answer, respond exactly:
   "I couldn't find this information in the provided documents.
   Please check the source documents or rephrase your question."
5. If the user writes in Tamil or Hindi, respond in that same language.
6. Keep the answer concise and useful. Quote numbers/dates exactly when present.
7. End with one short citation line in this format:
   Sources: [filename p.X], [filename p.Y]
   (If page is missing, use [filename])

CONTEXT DOCUMENTS:
{context}

CONVERSATION HISTORY:
{chat_history}

CURRENT QUESTION: {question}

ANSWER:"""


# ============================================================
# ANSWER REWRITE PROMPT (Guardrail for weak meta answers)
# ============================================================
ANSWER_REWRITE_PROMPT_TEMPLATE = """You are improving a weak RAG answer.

Rewrite the DRAFT ANSWER so it directly answers the user's question.

RULES:
1. Keep the response grounded only in CONTEXT DOCUMENTS.
2. First sentence must directly answer the question.
3. Remove meta phrases such as:
   "According to Document...", "this section covers...", "the document contains..."
4. If context is insufficient, output exactly:
   "I couldn't find this information in the provided documents.
   Please check the source documents or rephrase your question."
5. End with a citation line:
   Sources: [filename p.X], [filename p.Y]

QUESTION:
{question}

CONTEXT DOCUMENTS:
{context}

DRAFT ANSWER:
{draft_answer}

REWRITTEN ANSWER:"""


# ============================================================
# CONDENSE QUESTION PROMPT
# ============================================================
# WHAT: Rewrites follow-up questions into standalone questions.
#
# WHY THIS IS NEEDED:
#   User conversation:
#     Q1: "What is the gold loan interest rate?"
#     A1: "It is 12% per annum."
#     Q2: "What about the processing fee?"  ← Ambiguous!
#
#   Problem: "What about the processing fee?"
#     → ChromaDB search for this = poor results
#     → Because "what about" gives no context
#
#   Solution: Rewrite to standalone:
#     "What is the processing fee for gold loan?"
#     → ChromaDB search = great results ✅
#
# HOW:
#   This prompt is called BEFORE main RAG prompt.
#   Takes chat history + follow-up question
#   → Groq rewrites into clear standalone question
#   → That rewritten question goes to ChromaDB search
# ============================================================

CONDENSE_QUESTION_PROMPT = """Given the conversation history and a follow-up question,
rewrite the follow-up question to be a complete, standalone question.
The standalone question should make sense without any conversation history.

RULES:
1. Keep all important keywords from the original question
2. Add context from conversation history if needed
3. Return ONLY the rewritten question — no explanation, no preamble
4. If the question is already standalone, return it as-is

CONVERSATION HISTORY:
{chat_history}

FOLLOW-UP QUESTION: {question}

STANDALONE QUESTION:"""


# ============================================================
# NO CONTEXT FALLBACK PROMPT
# ============================================================
# WHAT: Used when ChromaDB returns NO relevant chunks.
#
# WHY:
#   Sometimes user asks question completely unrelated to documents.
#   OR documents don't cover that topic yet.
#   Instead of crashing or hallucinating, give honest response.
#
# WHEN:
#   chain.py calls this when search() returns empty list.
# ============================================================

NO_CONTEXT_PROMPT = """You are a helpful AI assistant.
The user asked a question but no relevant documents were found
in the knowledge base to answer it.

QUESTION: {question}

Respond politely that:
1. You couldn't find relevant information in the current documents
2. Suggest they upload relevant documents or rephrase the question
3. Keep response short and helpful

If the question is a simple greeting or general chat (not document-specific),
respond normally and helpfully without mentioning documents.

RESPONSE:"""


# ============================================================
# HELPER FUNCTION — Format chat history
# ============================================================
def format_chat_history(chat_history: list) -> str:
    """
    WHAT: Converts list of chat exchanges → readable string for prompt.

    WHY:
      LLM needs history as readable text in the prompt.
      List of dicts → formatted string.

    WHY LAST 5 ONLY:
      More history = more tokens = hits Groq rate limit faster.
      Last 5 exchanges = enough context for follow-up questions.
      Older history usually not relevant to current question.

    Args:
        chat_history: List of dicts:
                      [{"question": "...", "answer": "..."}, ...]

    Returns:
        Formatted string or "No previous conversation." if empty.

    Example output:
        Human: What is the gold loan interest rate?
        Assistant: The interest rate is 12% per annum...

        Human: What about the processing fee?
        Assistant: The processing fee is 0.5% of loan amount...
    """
    if not chat_history:
        return "No previous conversation."

    # Take only last 5 exchanges to save tokens
    # WHY 5: Enough for follow-up context, not too many tokens
    recent_history = chat_history[-5:]

    formatted_lines = []
    for exchange in recent_history:
        question = exchange.get("question", "")
        answer   = exchange.get("answer", "")

        if question:
            formatted_lines.append(f"Human: {question}")
        if answer:
            # Truncate very long answers in history
            # WHY: Save tokens — full answer not needed in history
            truncated_answer = answer[:300] + "..." if len(answer) > 300 else answer
            formatted_lines.append(f"Assistant: {truncated_answer}")

    return "\n".join(formatted_lines)


# ============================================================
# HELPER FUNCTION — Format retrieved chunks as context
# ============================================================
def format_context(chunks: list) -> str:
    """
    WHAT: Converts ChromaDB chunks → readable context string for prompt.

    WHY FORMAT NICELY:
      LLM reads this context to find answers.
      Clear formatting = LLM understands structure better
      = more accurate answers.

    WHY INCLUDE SOURCE LABELS:
      [Document 1 - gold_loan.pdf (Page 3)]
      → LLM can cite exact source in its answer
      → User knows WHERE information came from

    Args:
        chunks: List[Document] from ChromaVectorStore.search()

    Returns:
        Formatted context string ready to insert into prompt.
        Returns "No relevant context found." if chunks empty.

    Example output:
        [Document 1 - gold_loan.pdf (Page 3)]
        Gold loan interest rate is 12% per annum...

        ---

        [Document 2 - smartspend_docs.txt]
        Processing fee is 0.5% of loan amount...
    """
    if not chunks:
        return "No relevant context found."

    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        # Build source label
        file_name = chunk.metadata.get("file_name", "Unknown Source")
        page      = chunk.metadata.get("page", "")
        score     = chunk.metadata.get("similarity_score", 0)

        # Add page info if available (PDFs have page numbers)
        page_info  = f" (Page {page})" if page else ""

        # Source label tells LLM where this chunk came from
        source_label = f"[Document {i} - {file_name}{page_info}]"

        context_parts.append(
            f"{source_label}\n{chunk.page_content}"
        )

    # Join chunks with separator line
    # WHY separator: LLM clearly sees where one chunk ends, next begins
    return "\n\n---\n\n".join(context_parts)
