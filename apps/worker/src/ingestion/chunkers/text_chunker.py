
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from src.ingestion.loaders.document_loader import LoadedDocument
from src.config import settings


class TextChunker:
     def __init__(self):
          self.chunk_size= settings.rag_chunk_size
          self.chunk_overlap = settings.rag_chunk_overlap
          self.splitter = RecursiveCharacterTextSplitter(
               chunk_size=self.chunk_size,
               chunk_overlap=self.chunk_overlap,
               length_function=len,
               separators=["\n\n", "\n", ". ", " ", ""]
          )
          print(f' text chunker ready - size: { self.chunk_size} overlap : {self.chunk_overlap}')

     def chunk(self,loaded_docs: List[LoadedDocument]) -> List[Document]:
        
        all_chunks=[]

        for doc_index, loaded_doc in enumerate(loaded_docs):

            if not loaded_doc.content or not loaded_doc.content.strip():
                print(f' skipping empty document : {loaded_doc.source}')
                continue

            text_chunks = self.splitter.split_text(loaded_doc.content)

            total_chunks= len(text_chunks) 
            print(f' {loaded_doc.metadata.get("file_name", loaded_doc.source)}',
                  f'{total_chunks}chunks')
            
            for chunk_index, chunk_text in enumerate(text_chunks):
                if not chunk_text.strip():
                    continue
                
                chunk_metadata={
                    **loaded_doc.metadata,
                    "chunk_index": chunk_index,
                    "total_chunks": total_chunks,
                    "chunk_size": len(chunk_text),
                    "doc_index": doc_index,
                }

                all_chunks.append(Document(
                    page_content=chunk_text,
                    metadata=chunk_metadata
                ))
            print(f"\n✅ Chunking complete!")
        print(f"   Total documents processed: {len(loaded_docs)}")
        print(f"   Total chunks created: {len(all_chunks)}")
        print(f"   Avg chunks per doc: {len(all_chunks) // max(len(loaded_docs), 1)}")

        return all_chunks
     
     def chunk_single_text(self,text: str, metadata: dict={})-> List[Document]:
         text_chunks= self.splitter.split_text(text)

         return [
             Document(
                 page_content = chunk_text,
                 metadata={
                     **metadata,
                     "chunk_index": i,
                     "total_chunks": len(text_chunks),
                     "chunk_size": len(chunk_text),
                 }
             )
             for i,chunk_text in enumerate(text_chunks)
             if chunk_text.strip()
         ]
         


        
