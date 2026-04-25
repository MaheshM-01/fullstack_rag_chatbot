
from src.ingestion.loaders.document_loader import DocumentLoader
from src.ingestion.chunkers.text_chunker import TextChunker

#load documents
loader=DocumentLoader()
docs=loader.load('test_doc.txt')
print(f'loaded {len(docs)} document(s)')

chunker=TextChunker()
chunks=chunker.chunk(docs)

print(f'\n total chunks : {len(chunks)}')
print('content: ',chunks[0].page_content)
print(f' metadata: {chunks[0].metadata}')