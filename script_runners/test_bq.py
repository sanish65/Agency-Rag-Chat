from google.cloud import bigquery
import os

PROJECT_ID = 'expert-hackathon-2026'

def test_connection():
    try:
        print(f"Attempting to connect to BigQuery project: {PROJECT_ID}")
        client = bigquery.Client(project=PROJECT_ID)
        
        # Try a lightweight query (dry run or simple select 1)
        query = "SELECT 1"
        query_job = client.query(query)
        rows = list(query_job.result())
        print("Successfully connected and executed 'SELECT 1'")
        print(f"Result: {rows}")
    except Exception as e:
        print(f"Connection Failed: {e}")
        print("Ensure you have run 'gcloud auth application-default login'")

if __name__ == "__main__":
    test_connection()
