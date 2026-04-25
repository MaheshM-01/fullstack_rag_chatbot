from src.ingestion.loaders.document_loader import DocumentLoader

loader = DocumentLoader()
docs = loader.load('test_doc.txt')    # ← 'test' not 'tst'

print('✅ Loaded', len(docs), 'document(s)')
print('Content preview:', docs[0].content[:100])
print('Metadata:', docs[0].metadata)