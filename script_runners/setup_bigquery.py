import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings  # Using Ollama locally
from langchain_community.document_loaders import BigQueryLoader

# Config
# PROJECT_ID = "your_project_id"
PROJECT_ID = "expert-hackathon-2026"

DATASET_ID = "your_dataset_id"
TABLES = ["table1", "table2"]  # Add all BigQuery tables you want to query
PERSIST_DIR = "embeddings_store"

# Ensure embeddings directory exists
os.makedirs(PERSIST_DIR, exist_ok=True)

# Initialize embeddings
embeddings = OllamaEmbeddings(model="llama3.2")

all_docs = []

for table in TABLES:
    loader = BigQueryLoader(project_id=PROJECT_ID, dataset_id=DATASET_ID, table_id=table)
    docs = loader.load()
    all_docs.extend(docs)

# Create or persist vectorstore
vectorstore = Chroma.from_documents(all_docs, embeddings, persist_directory=PERSIST_DIR)
vectorstore.persist()

print(f"Embeddings saved in '{PERSIST_DIR}'")
