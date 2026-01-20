from app import get_dataset_schema

print("Testing usage of get_dataset_schema...")
try:
    schema = get_dataset_schema()
    print("--- SCHEMA START ---")
    print(schema)
    print("--- SCHEMA END ---")
except Exception as e:
    print(f"FAILED: {e}")



