# bq_to_sqlite.py
import sqlite3
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "expert-hackathon-2026"
DATASET_ID = "hackathon_data"  # your dataset
SQLITE_FILE = "local_hackathon.db"

client = bigquery.Client(project=PROJECT_ID)
conn = sqlite3.connect(SQLITE_FILE)

tables = client.list_tables(DATASET_ID)
print(f"Found {len(tables)} tables in {DATASET_ID}")

for table in tables:
    table_id = table.table_id
    print(f"Fetching table: {table_id}")
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{table_id}` LIMIT 1000"
    df = client.query(query).to_dataframe()
    df.to_sql(table_id, conn, if_exists="replace", index=False)

conn.close()
print("✅ All tables from hackathon_data are now in local SQLite!")
