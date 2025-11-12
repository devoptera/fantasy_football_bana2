import sqlite3

db_path = r"C:\Users\Collin Anderson\fantasy\fantasy.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# find all tables that start with 'week'
tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'week%';")]

for table in tables:
    # get all columns in current order
    cur.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cur.fetchall()]

    # put desired ones first if they exist
    front = [c for c in ['playerName', 'team', 'position', 'playerID'] if c in cols]
    remaining = [c for c in cols if c not in front]
    new_order = front + remaining

    # rebuild SQL for new table
    select_clause = ", ".join(new_order)
    new_table = f"{table}_new"

    print(f"Reordering columns for {table}...")

    # create new table with columns in correct order
    cur.execute(f"CREATE TABLE {new_table} AS SELECT {select_clause} FROM {table};")

    # drop old and rename new
    cur.execute(f"DROP TABLE {table};")
    cur.execute(f"ALTER TABLE {new_table} RENAME TO {table};")

conn.commit()
conn.close()

print("✅ All week tables reordered successfully.")
