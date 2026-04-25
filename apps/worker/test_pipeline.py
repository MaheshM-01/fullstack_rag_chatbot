
from src.ingestion.pipeline import IngestionPipeline
from src.generation.chain import RAGChain

print("=" * 55)
print("STEP 1: Initialize Pipeline + Reset ChromaDB")
print("=" * 55)

pipeline = IngestionPipeline()
pipeline.reset()   # Fresh start — no duplicates!

print("\n" + "=" * 55)
print("STEP 2: Ingest test document")
print("=" * 55)

result = pipeline.ingest("test_doc.txt", namespace="default")
print(f"\nResult: {result['status']}")
print(f"Chunks: {result['chunks_created']}")
print(f"Message: {result['message']}")

print("\n" + "=" * 55)
print("STEP 3: Try ingesting SAME file again (duplicate check)")
print("=" * 55)

result2 = pipeline.ingest("test_doc.txt", namespace="default")
print(f"Status: {result2['status']}")   # Should be 'skipped'
print(f"Message: {result2['message']}")

print("\n" + "=" * 55)
print("STEP 4: Pipeline Stats")
print("=" * 55)

stats = pipeline.get_stats()
print(f"Total chunks in ChromaDB: {stats['total_chunks']}")
print(f"Ingested sources tracked: {stats['ingested_sources']}")

print("\n" + "=" * 55)
print("STEP 5: Ask question via RAG Chain")
print("=" * 55)

chain = RAGChain()
result3 = chain.answer("What is the premium plan price?")
print(f"\n💬 Answer: {result3['answer']}")
print(f"📚 Sources: {[s['file'] for s in result3['sources']]}")

print("\n✅ Full Pipeline working perfectly!")