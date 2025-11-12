import pandas as pd
import sqlite3
import json

base_path = r'C:\Users\Collin Anderson\fantasy'
json_file = fr'{base_path}\players.json'
db_file = fr'{base_path}\fantasy.db'

# Load Sleeper player data
with open(json_file) as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame.from_dict(data, orient='index')

# Clean up to essential columns
keep = ['player_id', 'full_name', 'position', 'team']
df = df[keep]
df = df.rename(columns={'player_id': 'playerID', 'full_name': 'playerName'})

# Write to fantasy.db
conn = sqlite3.connect(db_file)
df.to_sql('players', conn, if_exists='replace', index=False)
conn.close()

print("✅ Sleeper player table loaded into fantasy.db")
