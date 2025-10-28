"""Archivist Agent - Agentic RAG for retrieval and storage."""

from typing import List, Dict, Optional
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.prompts import ChatPromptTemplate
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os


class ArchivistAgent:
    """Agent responsible for document storage, retrieval, and RAG operations."""
    
    def __init__(self, llm: ChatNVIDIA, persist_directory: str = "./chroma_db"):
        """Initialize the Archivist Agent.
        
        Args:
            llm: Language model instance
            persist_directory: Directory to persist vector store
        """
        self.llm = llm
        self.persist_directory = persist_directory
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize or load vector store
        self.vector_store = self._initialize_vector_store()
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def _initialize_vector_store(self) -> Chroma:
        """Initialize or load the vector store."""
        try:
            # Try to load existing vector store
            if os.path.exists(self.persist_directory):
                return Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            else:
                # Create new vector store
                return Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
        except Exception as e:
            print(f"Warning: Could not initialize vector store: {e}")
            # Return a new instance without persistence
            return Chroma(embedding_function=self.embeddings)
    
    def archive_document(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Archive a document in the vector store.
        
        Args:
            content: Document content to archive
            metadata: Optional metadata for the document
            
        Returns:
            Confirmation message
        """
        try:
            # Split the document into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Create documents with metadata
            documents = [
                Document(
                    page_content=chunk,
                    metadata=metadata or {}
                )
                for chunk in chunks
            ]
            
            # Add to vector store
            self.vector_store.add_documents(documents)
            
            # Persist if possible
            try:
                if hasattr(self.vector_store, 'persist'):
                    self.vector_store.persist()
            except:
                pass
            
            return f"Successfully archived document with {len(chunks)} chunks."
        except Exception as e:
            return f"Error archiving document: {str(e)}"
    
    def retrieve_documents(self, query: str, k: int = 3) -> List[Document]:
        """Retrieve relevant documents based on a query.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        try:
            results = self.vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []
    
    def query_with_context(self, query: str, k: int = 3) -> str:
        """Query the knowledge base and generate an answer with context.
        
        Args:
            query: User query
            k: Number of context documents to retrieve
            
        Returns:
            Generated answer with context
        """
        try:
            # Retrieve relevant documents
            docs = self.retrieve_documents(query, k=k)
            
            if not docs:
                return "No relevant information found in the archive."
            
            # Prepare context from retrieved documents
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # Generate answer using LLM with context
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a knowledgeable archivist. Answer questions based on the provided context. If the context doesn't contain relevant information, say so."),
                ("user", f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:")
            ])
            
            formatted = prompt.format_messages()
            response = self.llm.invoke(formatted)
            
            return response.content
        except Exception as e:
            return f"Error querying with context: {str(e)}"
    
    def semantic_search(self, query: str, k: int = 5) -> List[Dict]:
        """Perform semantic search in the archive.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of search results with content and metadata
        """
        try:
            docs = self.retrieve_documents(query, k=k)
            
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in docs
            ]
        except Exception as e:
            return [{"error": f"Error in semantic search: {str(e)}"}]
    
    def summarize_archive(self, topic: Optional[str] = None) -> str:
        """Summarize documents in the archive, optionally filtered by topic.
        
        Args:
            topic: Optional topic to filter by
            
        Returns:
            Summary of archived documents
        """
        try:
            if topic:
                docs = self.retrieve_documents(topic, k=5)
            else:
                # Get a sample of documents
                docs = self.retrieve_documents("summary overview", k=5)
            
            if not docs:
                return "No documents found in the archive."
            
            # Combine document contents
            combined_content = "\n\n".join([doc.page_content for doc in docs])
            
            # Generate summary
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert summarizer. Provide a comprehensive summary of the archived documents."),
                ("user", f"Summarize these archived documents:\n\n{combined_content}")
            ])
            
            formatted = prompt.format_messages()
            response = self.llm.invoke(formatted)
            
            return response.content
        except Exception as e:
            return f"Error summarizing archive: {str(e)}"
    
    def process_request(self, request: str, content: Optional[str] = None) -> str:
        """Process an archival request.
        
        Args:
            request: Type of operation requested
            content: Optional content for the operation
            
        Returns:
            Result of the operation
        """
        request_lower = request.lower()
        
        if "archive" in request_lower and content:
            return self.archive_document(content)
        elif "search" in request_lower or "find" in request_lower:
            results = self.semantic_search(content or request, k=3)
            return "\n\n".join([r.get("content", "") for r in results if "error" not in r])
        elif "query" in request_lower or "question" in request_lower:
            return self.query_with_context(content or request)
        elif "summarize" in request_lower:
            return self.summarize_archive(content)
        else:
            return "Please specify an operation: archive, search, query, or summarize."
