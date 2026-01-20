# document_rag.py
import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.tools import tool
import json
from dotenv import load_dotenv
from cache.cache_manager import cached

# Load environment variables
load_dotenv()

# Configuration
PUBLIC_FOLDER = "public"
VECTOR_STORE_PATH = "document_vectors"

# Global vector store instance
vector_store = None

def initialize_document_store(force_rebuild: bool = False):
    """
    Initialize the document vector store by processing all PDFs in the public folder.
    
    Args:
        force_rebuild: If True, will rebuild the store even if it exists.
    """
    global vector_store
    
    try:
        # Check if vector store already exists and we're not forcing rebuild
        if not force_rebuild and os.path.exists(VECTOR_STORE_PATH):
            print(f"Loading existing vector store from {VECTOR_STORE_PATH}")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vector_store = FAISS.load_local(
                VECTOR_STORE_PATH, 
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("Vector store loaded successfully")
            return
        
        if force_rebuild:
            print("Force rebuild requested. Processing all documents...")
        
        # Get all PDF files from public folder
        if not os.path.exists(PUBLIC_FOLDER):
            print(f"Warning: {PUBLIC_FOLDER} folder does not exist")
            return
        
        pdf_files = [f for f in os.listdir(PUBLIC_FOLDER) if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in {PUBLIC_FOLDER} folder")
            return
        
        print(f"Found {len(pdf_files)} PDF file(s) to process")
        
        # Load and process documents
        all_documents = []
        for pdf_file in pdf_files:
            pdf_path = os.path.join(PUBLIC_FOLDER, pdf_file)
            print(f"Processing: {pdf_file}")
            
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            # Add source metadata
            for doc in documents:
                doc.metadata['source_file'] = pdf_file
            
            all_documents.extend(documents)
        
        if not all_documents:
            print("No documents loaded")
            return
        
        print(f"Loaded {len(all_documents)} pages from PDFs")
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_documents(all_documents)
        print(f"Created {len(chunks)} text chunks")
        
        # Create embeddings and vector store
        print("Generating embeddings...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # Save vector store
        vector_store.save_local(VECTOR_STORE_PATH)
        print(f"Vector store saved to {VECTOR_STORE_PATH}")
        
    except Exception as e:
        print(f"Error initializing document store: {e}")
        vector_store = None

@cached
def search_documents_rag(query: str, k: int = 4) -> str:
    """
    Search documents using RAG and return relevant context.
    
    Args:
        query: The search query
        k: Number of relevant chunks to retrieve
        
    Returns:
        JSON string with relevant document chunks and sources
    """
    global vector_store
    
    if vector_store is None:
        return json.dumps({
            "error": "Document store not initialized. No documents available."
        })
    
    try:
        # Perform similarity search
        results = vector_store.similarity_search(query, k=k)
        
        if not results:
            return json.dumps({
                "message": "No relevant information found in documents."
            })
        
        # Format results
        formatted_results = []
        for i, doc in enumerate(results):
            formatted_results.append({
                "chunk_id": i + 1,
                "content": doc.page_content,
                "source": doc.metadata.get('source_file', 'Unknown'),
                "page": doc.metadata.get('page', 'Unknown')
            })
        
        return json.dumps({
            "results": formatted_results,
            "total_chunks": len(formatted_results)
        })
        
    except Exception as e:
        return json.dumps({
            "error": f"Error searching documents: {str(e)}"
        })

@tool
def search_documents(query: str) -> str:
    """
    Search through uploaded PDF documents in the public folder to find relevant information.
    Use this tool when the user asks about document content, workflows, processes, or any 
    information that might be in uploaded files.
    
    Args:
        query: The search query or question about document content
        
    Returns:
        Relevant text chunks from documents with source information
    """
    result = search_documents_rag(query)
    
    try:
        data = json.loads(result)
        
        if "error" in data:
            return data["error"]
        
        if "message" in data:
            return data["message"]
        
        # Format results for the agent
        if "results" in data:
            formatted_text = f"Found {data['total_chunks']} relevant sections:\n\n"
            for chunk in data["results"]:
                formatted_text += f"--- From {chunk['source']} (Page {chunk['page']}) ---\n"
                formatted_text += f"{chunk['content']}\n\n"
            
            return formatted_text
        
        return "No results found"
        
    except Exception as e:
        return f"Error processing search results: {str(e)}"
