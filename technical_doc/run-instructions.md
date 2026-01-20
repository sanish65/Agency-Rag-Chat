# Run Instructions: Agency OS RAG Chat

This guide provides step-by-step instructions to set up, run, and maintain the Agency OS RAG Chat application.

## 1. Prerequisites
- **Docker & Docker Compose** (Recommended)
- **Python 3.10+** (For local execution)
- **Google Cloud Service Account JSON** (with BigQuery permissions)
- **Google AI Studio API Key** (for Gemini)

---

## 2. Initial Setup

### Credentials Configuration
1. Create a `credentials/` folder in the project root.
2. Place your service account JSON file inside.
3. Rename the file to `gcp-credentials.json`.

### Environment Variables
1. Copy `.env.example` to `.env`.
2. Open `.env` and add your `GOOGLE_API_KEY`.
3. Ensure `GOOGLE_CLOUD_PROJECT` is set to `expert-hackathon-2026`.

---

## 3. Running the Application

### Option A: Using Docker (Recommended)
This approach handles all dependencies and environment isolation automatically.

```bash
# Build and start the container
docker-compose up --build -d

# Monitor logs
docker-compose logs -f
```
The application will be accessible at: **http://localhost:5001**

### Option B: Local Execution
For development or environments where Docker is not available.

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python app.py
```
*Note: Local execution defaults to port 5002 if 5001 is busy. Check console output for the exact URL.*

---

## 4. Managing Documents (RAG)

### Adding New Documents
To add new knowledge to the AI:
1. Place your PDF files in the `public/` directory.
2. The system supports multiple PDFs.

### Re-indexing Documents
Whenever you add, remove, or modify files in the `public/` folder, you MUST rebuild the vector index for the AI to "see" the changes.

**Run the re-indexing command:**
```bash
# Local
python reindex_documents.py

# Via Docker
docker-compose exec rag-chat-app python reindex_documents.py
```
This script will:
- Parse all PDFs in the `public/` folder.
- Split text into optimized chunks.
- Generate new embeddings using Google's embedding model.
- Save the updated index to `document_vectors/`.

---

## 5. Maintenance & Troubleshooting

### Clearing the Cache
If you encounter stale responses or want to force the AI to re-evaluate its logic:
- Reset the cache by deleting `cache.db`:
  ```bash
  rm cache.db
  ```

### Stopping the Application
```bash
# Docker
docker-compose down

# Local
# Press CTRL+C in the terminal
```
