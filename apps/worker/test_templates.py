
from src.generation.prompts.templates import (
    RAG_PROMPT_TEMPLATE,
    format_chat_history,
    format_context
)
from langchain.schema import Document

# Test 1: format_chat_history
print("=" * 50)
print("TEST 1: Chat History Formatting")
print("=" * 50)

history = [
    {"question": "What is gold loan interest rate?",
     "answer": "It is 12% per annum."},
    {"question": "What about processing fee?",
     "answer": "Processing fee is 0.5%."}
]

formatted = format_chat_history(history)
print(formatted)

# Test 2: format_context
print("\n" + "=" * 50)
print("TEST 2: Context Formatting")
print("=" * 50)

chunks = [
    Document(
        page_content="Gold loan interest rate is 12% per annum.",
        metadata={"file_name": "gold_loan.pdf", "page": "3",
                  "similarity_score": 0.85}
    ),
    Document(
        page_content="Processing fee is 0.5% of loan amount.",
        metadata={"file_name": "smartspend_docs.txt", "page": "",
                  "similarity_score": 0.72}
    )
]

context = format_context(chunks)
print(context)

# Test 3: Full prompt
print("\n" + "=" * 50)
print("TEST 3: Full RAG Prompt")
print("=" * 50)

full_prompt = RAG_PROMPT_TEMPLATE.format(
    context=context,
    chat_history=formatted,
    question="What is the gold loan interest rate?"
)
print(full_prompt)
print("\n✅ Templates working correctly!")