# reindex_documents.py
import os
import shutil
from document_rag import initialize_document_store, VECTOR_STORE_PATH

def main():
    print("--- RAG Re-indexing Utility ---")
    
    # Check if vector store exists
    if os.path.exists(VECTOR_STORE_PATH):
        print(f"Removing old vector store at {VECTOR_STORE_PATH}...")
        try:
            shutil.rmtree(VECTOR_STORE_PATH)
            print("Successfully removed old index.")
        except Exception as e:
            print(f"Error removing old index: {e}")
            return

    print("Rebuilding index from scratch...")
    initialize_document_store(force_rebuild=True)
    
    if os.path.exists(VECTOR_STORE_PATH):
        print("\nSUCCESS: Document index has been rebuilt and saved.")
    else:
        print("\nFAILURE: Re-indexing failed. Check logs for details.")

if __name__ == "__main__":
    main()
