
# from src.ingestion.loaders.document_loader import DocumentLoader
# from src.ingestion.chunkers.text_chunker import TextChunker
# from src.config import settings
# from src.retrieval.vector_store.chroma_store import ChromaVectorStore

# print( 'load documents')
# loader=DocumentLoader()
# docs=loader.load('test_doc.txt')
# print(f' loaded {len(docs)}doc(s)')


# print('chunk documents')
# chunker=TextChunker()
# chunks=chunker.chunk(docs)
# print(f' chunks created: {len(chunks)}')


# print('store chunks in chromadb')
# store=ChromaVectorStore()
# stored=store.add_documents(chunks,namespace='test')
# print(f'stored: {stored} chunks')




# print('search Chromadb')
# result=store.search('gold loan interest rate')
# print(f' results found: {len(result)}')
# if result:
#     print(f' best match : {result[0].page_content[:100]}')
#     print(f' score{result[0].metadata['similarity_score']}')

# print('collection stats')
# stats=store.get_collection_stats()
# print(stats)









from src.ingestion.loaders.document_loader import DocumentLoader
from src.ingestion.chunkers.text_chunker import TextChunker
from src.retrieval.vector_store.chroma_store import ChromaVectorStore

print("=" * 50)
print("STEP 1: Load document")
print("=" * 50)
loader = DocumentLoader()
docs = loader.load('test_doc.txt')
print(f"Loaded: {len(docs)} doc(s)")

print("\n" + "=" * 50)
print("STEP 2: Chunk document")
print("=" * 50)
chunker = TextChunker()
chunks = chunker.chunk(docs)
print(f"Chunks created: {len(chunks)}")

print("\n" + "=" * 50)
print("STEP 3: Store in ChromaDB")
print("=" * 50)
store = ChromaVectorStore()
stored = store.add_documents(chunks, namespace="test")
print(f"Stored: {stored} chunks")

print("\n" + "=" * 50)
print("STEP 4: Search ChromaDB")
print("=" * 50)
results = store.search("gold loan interest rate")
print(f"Results found: {len(results)}")
if results:
    print(f"Best match: {results[0].page_content[:100]}")
    print(f"Score: {results[0].metadata['similarity_score']}")

print("\n" + "=" * 50)
print("STEP 5: Collection Stats")
print("=" * 50)
stats = store.get_collection_stats()
print(stats)