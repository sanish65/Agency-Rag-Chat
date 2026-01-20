# Agency OS Application

An advanced AI-powered chat application built with Flask and LangChain, designed for data-driven insights through BigQuery integration and document-based Retrieval-Augmented Generation (RAG).

## 🚀 Features

- **BigQuery Integration**: Query and analyze your BigQuery datasets using natural language.
- **Document RAG**: Upload and search through PDF documents in the `public/` folder.
- **Dynamic Visualizations**: Automatically generates charts (Bar, Line, Pie, etc.) and Mermaid flowcharts.
- **Interactive 3D Globe**: Visualizes branch locations and data points on an interactive 3D globe.
- **Smart Caching**: Efficient response caching to improve performance and reduce API costs.
- **Data Export**: Export chat results to Excel or Google Sheets.

## 📋 Prerequisites

- **Python 3.11+** (if running locally)
- **Docker & Docker Compose** (recommended)
- **Google Cloud Project**: With BigQuery API enabled.
- **Google Generative AI API Key**: Get it from [Google AI Studio](https://makersuite.google.com/app/apikey).
- **Service Account Credentials**: A JSON key file for a GCP service account with BigQuery permissions.

## 🛠️ Setup Instructions

### 1. Credentials Setup

1. Create a directory named `credentials` in the project root.
2. Place your Google Cloud service account JSON file inside and rename it to `gcp-credentials.json`.
   ```bash
   mkdir credentials
   # Copy your-key.json to credentials/gcp-credentials.json
   ```

### 2. Environment Configuration

Create a `.env` file in the project root based on `.env.example`:
```bash
cp .env.example .env
```
Edit `.env` and add your `GOOGLE_API_KEY`.

### 3. Running the Application

#### Option A: Using Docker (Recommended)
```bash
docker-compose up --build
```
The application will be available at `http://localhost:5001`.

#### Option B: Local Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

### 🔄 Updating the Document Index

If you add new PDF files to the `public/` folder or rename existing ones, you need to refresh the document index:

**Run the re-indexing script:**
```bash
python reindex_documents.py
```
This will recreate the vector store in the `document_vectors/` directory, allowing the chatbot to search the updated files.

## 📂 Project Structure

- `app.py`: Main Flask application and agent logic.
- `tools/agent_tools.py`: Custom LangChain tools for BigQuery and visualization.
- `tools/document_rag.py`: PDF processing and vector store management.
- `templates/`: HTML templates (Dashboard, Login).
- `public/`: Place your PDF documents here for RAG.
- `requirements.txt`: Python dependencies.
- `script_runners/`: Python code that was created to test the functionality of the app. They got upgraded as the test completed and main logic was deployed in app.py. It is kept for the reference of how the system was developed. Do not delete it.
- `cache/`: Cache directory for storing vector store and other temporary files.

## 📊 Usage

Once logged in, you can ask questions like:
- "List all tables in our hackathon dataset."
- "Show me a bar chart of applications by branch."
- "What does the CRM manual say about the refund process?"
- "Compare the enquiry status across different regions."

## 📜 License

This project is developed for the Expert Hackathon 2026.  

## 📝 Author

Heubert Sans
Note: script_runners are the python code that was created to test the functionality of the app. They got useless as the test completed and main logic was deployed in app.py. It is kept for the reference of how the system was developed. Do not delete it.

## Deployment
I have deployed this project on Render: https://agency-os-bot-4.onrender.com/

Project needs: GCP access control for Bigquery 
