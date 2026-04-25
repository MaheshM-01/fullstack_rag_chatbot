
from src.ingestion.loaders.document_loader import DocumentLoader
from src.ingestion.chunkers.text_chunker import TextChunker
from src.retrieval.vector_store.chroma_store import ChromaVectorStore
from src.generation.chain import RAGChain

print("=" * 50)
print("STEP 1: Ingest test document")
print("=" * 50)

# Load + chunk + store
loader  = DocumentLoader()
chunker = TextChunker()
store   = ChromaVectorStore()

docs   = loader.load("test_doc.txt")
chunks = chunker.chunk(docs)
store.add_documents(chunks, namespace="default")
print(f"✅ Ingested {len(chunks)} chunks")

print("\n" + "=" * 50)
print("STEP 2: Initialize RAG Chain")
print("=" * 50)

chain = RAGChain(namespace="default")

print("\n" + "=" * 50)
print("STEP 3: Ask a question (normal)")
print("=" * 50)

result = chain.answer("What is the gold loan interest rate?")

print(f"\n💬 Answer:\n{result['answer']}")
print(f"\n📚 Sources: {result['sources']}")
print(f"📊 Chunks used: {result['chunks_used']}")
print(f"✅ Has context: {result['has_context']}")

print("\n" + "=" * 50)
print("STEP 4: Ask with chat history (follow-up)")
print("=" * 50)

history = [{"question": "What is gold loan?",
            "answer": result["answer"]}]

result2 = chain.answer(
    "What about the processing fee?",
    chat_history=history
)
print(f"\n💬 Follow-up Answer:\n{result2['answer']}")

print("\n" + "=" * 50)
print("STEP 5: Streaming answer")
print("=" * 50)

print("Streaming: ", end="")
for token in chain.stream("What plans are available?"):
    print(token, end="", flush=True)

print("\n\n✅ Full RAG Chain working!")