import os
import json
import logging
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from utils import setup_logger

# Setup logger
logger = setup_logger()

class KnowledgeBase:
    def __init__(self, persist_directory="data/chroma_db"):
        """
        Initialize the knowledge base with ChromaDB for vector storage.
        
        Args:
            persist_directory (str): Directory to persist ChromaDB
        """
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Use default embedding function (all-MiniLM-L6-v2)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name="research_documents",
                embedding_function=self.embedding_function
            )
            logger.info(f"Loaded existing collection with {self.collection.count()} documents")
        except Exception:
            self.collection = self.client.create_collection(
                name="research_documents",
                embedding_function=self.embedding_function
            )
            logger.info("Created new collection")
    
    def add_document(self, text, metadata=None):
        """
        Add a document to the knowledge base.
        
        Args:
            text (str): Document text
            metadata (dict): Document metadata
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Attempted to add empty document, skipping")
            return
        
        # Generate ID from metadata or timestamp
        if metadata and 'url' in metadata:
            doc_id = str(hash(metadata['url']))
        else:
            doc_id = str(hash(f"{text[:100]}{datetime.now().isoformat()}"))
        
        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
            logger.info(f"Added document {doc_id} to knowledge base")
        except Exception as e:
            logger.error(f"Error adding document to knowledge base: {e}")
    
    def query(self, query_text, n_results=5):
        """
        Query the knowledge base for relevant documents.
        
        Args:
            query_text (str): Query text
            n_results (int): Number of results to return
            
        Returns:
            list: List of documents with text and metadata
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            documents = []
            for i, doc in enumerate(results['documents'][0]):
                documents.append({
                    'text': doc,
                    'metadata': results['metadatas'][0][i] if i < len(results['metadatas'][0]) else {},
                    'distance': results['distances'][0][i] if 'distances' in results and i < len(results['distances'][0]) else None
                })
            
            logger.info(f"Query '{query_text[:50]}...' returned {len(documents)} results")
            return documents
        except Exception as e:
            logger.error(f"Error querying knowledge base: {e}")
            return []
    
    def count(self):
        """Return the number of documents in the knowledge base"""
        try:
            return self.collection.count()
        except Exception:
            return 0
    
    def clear(self):
        """Clear all documents from the knowledge base"""
        try:
            self.client.delete_collection("research_documents")
            self.collection = self.client.create_collection(
                name="research_documents",
                embedding_function=self.embedding_function
            )
            logger.info("Cleared knowledge base")
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {e}")
