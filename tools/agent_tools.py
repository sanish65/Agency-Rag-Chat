import json
import base64
import io
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from langchain.tools import tool
from google.cloud import bigquery
import os
from tools.document_rag import search_documents
from cache.cache_manager import cached

# Configuration
PROJECT_ID = 'expert-hackathon-2026'
DATASET_ID = 'hackathon_data'

# Initialize Client
def get_bq_client(project):
    json_creds = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')
    if json_creds:
        from google.oauth2 import service_account
        from google.cloud import bigquery
        try:
            info = json.loads(json_creds)
            credentials = service_account.Credentials.from_service_account_info(info)
            return bigquery.Client(project=project, credentials=credentials)
        except Exception as e:
            print(f"Error loading GCP_SERVICE_ACCOUNT_JSON in tools: {e}")
    from google.cloud import bigquery
    return bigquery.Client(project=project)

bq_client = get_bq_client(PROJECT_ID)

@tool
def list_tables() -> str:
    """
    List all tables in the dataset and their schemas. 
    Use this to understand the database structure before writing queries.
    """
    try:
        tables = list(bq_client.list_tables(DATASET_ID))
        schema_text = []
        
        for table in tables:
            t_ref = bq_client.get_table(table)
            schema_text.append(f"Table: {DATASET_ID}.{t_ref.table_id}")
            columns = [f" - {schema.name} ({schema.field_type})" for schema in t_ref.schema]
            schema_text.extend(columns)
            schema_text.append("") 
            
        return "\n".join(schema_text)
    except Exception as e:
        return f"Error fetching schema: {e}"

@tool
def execute_sql(query: str) -> str:
    """
    Execute a Standard SQL query in BigQuery and return the results as a string.
    Always query against `expert-hackathon-2026.hackathon_data`.
    """
    try:
        query_job = bq_client.query(query)
        rows = list(query_job.result())
        
        if not rows:
            return "[]" # Return empty JSON array
            
        # Serialize to formatted string for the Agent to read
        # Limit to 50 rows to prevent context overflow
        valid_rows = []
        for row in rows[:50]:
            # Convert row to dict and handle datetimes
            d = {}
            for key, value in row.items():
                 if hasattr(value, 'isoformat'):
                      d[key] = value.isoformat()
                 else:
                      d[key] = str(value)
            valid_rows.append(d)

        return json.dumps(valid_rows)
        
    except Exception as e:
        return f"Error executing SQL: {e}"

def generate_plot_image(data_query: str, chart_type: str, title: str) -> dict:
    """
    Helper function to generate plot and return dict with base64 image.
    """
    try:
        # 1. Get Data
        query_job = bq_client.query(data_query)
        df = query_job.to_dataframe()
        
        if df.empty:
            return {"error": "No data returned for visualization"}

        # 2. Cleanup / Setup Plot
        plt.figure(figsize=(12, 7))
        sns.set_theme(style="whitegrid")
        
        # 3. Plotting Logic
        cols = df.columns
        x_col = cols[0]
        y_col = cols[1] if len(cols) > 1 else cols[0]
        
        # Handle different chart types
        ax = None
        if chart_type == 'bar':
            if len(cols) >= 2:
                ax = sns.barplot(data=df, x=x_col, y=y_col, hue=x_col, palette="viridis", legend=False)
            else:
                ax = sns.countplot(x=x_col, data=df, palette="viridis")
            
            # Add labels on top of bars
            if ax:
                for p in ax.patches:
                    ax.annotate(format(p.get_height(), '.0f'), 
                                (p.get_x() + p.get_width() / 2., p.get_height()), 
                                ha = 'center', va = 'center', 
                                xytext = (0, 9), 
                                textcoords = 'offset points',
                                fontsize=10, fontweight='bold')
                
        elif chart_type == 'line':
            ax = sns.lineplot(data=df, x=x_col, y=y_col, marker='o', linewidth=2.5)
            
        elif chart_type == 'scatter':
            ax = sns.scatterplot(data=df, x=x_col, y=y_col, s=100)
            
        elif chart_type == 'hist':
            ax = sns.histplot(data=df, x=x_col, kde=True)
            
        elif chart_type == 'pie':
            if len(cols) >= 2:
                plt.pie(df[y_col], labels=df[x_col], autopct='%1.1f%%', startangle=140, 
                        colors=sns.color_palette("viridis", len(df)))
            else:
                counts = df[x_col].value_counts()
                plt.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140,
                        colors=sns.color_palette("viridis", len(counts)))

        plt.title(title, fontsize=16, pad=20, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.xlabel(x_col, fontsize=12, fontweight='bold')
        plt.ylabel(y_col if len(cols) > 1 else 'Count', fontsize=12, fontweight='bold')
        plt.tight_layout()

        # 4. Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return {
            "image": img_str,
            "title": title,
            "chart_type": chart_type
        }
        
    except Exception as e:
        plt.close()
        return {"error": f"Visualization failed: {e}"}

@tool
def create_visualization(data_query: str, chart_type: str, title: str) -> str:
    """
    Visualize data using a specific chart type via Seaborn/Matplotlib.
    Returns a Base64 encoded image string of the chart.
    
    Args:
        data_query: The valid SQL query to get data for the chart.
        chart_type: One of 'bar', 'line', 'pie', 'scatter', 'hist'.
        title: A descriptive title for the chart.
    """
    result = generate_plot_image(data_query, chart_type, title)
    return json.dumps(result)
