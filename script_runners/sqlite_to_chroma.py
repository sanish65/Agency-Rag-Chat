import sqlite3
import pandas as pd
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
SQLITE_FILE = "local_hackathon.db"
VECTOR_DB_DIR = "chroma_db"

# Initialize Ollama embeddings
embeddings = OllamaEmbeddings(model="llama3.2")

# Initialize Chroma
vector_db = Chroma(
    persist_directory=VECTOR_DB_DIR,
    embedding_function=embeddings,
    collection_name="hackathon_data"
)

# Load SQLite tables
conn = sqlite3.connect(SQLITE_FILE)
cursor = conn.cursor()
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
tables = [t[0] for t in tables]

all_docs = []
for table in tables:
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    for _, row in df.iterrows():
        content = " | ".join([f"{col}: {row[col]}" for col in df.columns])
        all_docs.append(Document(page_content=content, metadata={"table": table}))

conn.close()

# Add to Chroma
vector_db.add_documents(all_docs)
vector_db.persist()
print("✅ Vector DB updated with all tables from hackathon_data")
