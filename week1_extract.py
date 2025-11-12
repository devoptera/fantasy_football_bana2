import pandas as pd
import sqlite3

week = 1
base_path = r'C:\Users\Collin Anderson\fantasy'
json_file = fr'{base_path}\week{week}_raw.json'
db_file = fr'{base_path}\fantasy.db'
table_name = f'week{week}'

# Load JSON (player IDs are index)
df = pd.read_json(json_file, orient='index')

# 🔹 Make playerID a normal column
df = df.reset_index().rename(columns={'index': 'playerID'})

# Write to SQLite (now includes playerID column)
conn = sqlite3.connect(db_file)
df.to_sql(table_name, conn, if_exists='replace', index=False)
conn.close()

print(f"✅ week{week} written to fantasy.db with playerID column")

