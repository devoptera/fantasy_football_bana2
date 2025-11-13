import sqlite3
import pandas as pd
import os

# Connect to your database

db_path = r"C:\Users\cmice\repo\fantasy\fantasy.db"
output_dir = "data/csv_exports"
os.makedirs(output_dir, exist_ok=True)

conn = sqlite3.connect(db_path)

# Get all table names
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)['name']

# Export each table to CSV
for table in tables:
    df = pd.read_sql_query(f"SELECT * FROM {table};", conn)
    csv_path = os.path.join(output_dir, f"{table}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Exported {table} -> {csv_path}")

conn.close()
print("✅ All tables exported successfully.")
