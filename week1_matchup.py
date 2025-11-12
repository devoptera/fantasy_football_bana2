import requests
import pandas as pd
import sqlite3

# ---- CONFIG ----
SEASON = 2024
WEEK = 1
db_path = r"C:\Users\Collin Anderson\fantasy\fantasy.db"
# ----------------

print(f"📡 Fetching NFL Week {WEEK} schedule for {SEASON}...")

url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&year={SEASON}&week={WEEK}"

res = requests.get(url)
if res.status_code != 200:
    raise Exception(f"❌ Failed to fetch data (status {res.status_code})")

data = res.json()

games = []
for event in data.get("events", []):
    try:
        comp = event["competitions"][0]
        home = comp["competitors"][0]["team"]["abbreviation"]
        away = comp["competitors"][1]["team"]["abbreviation"]
        games.append({"week": WEEK, "home": home, "away": away})
    except Exception as e:
        print(f"⚠️ Skipped a game: {e}")

# Convert to DataFrame
schedule = pd.DataFrame(games)
print(f"✅ Pulled {len(schedule)} Week {WEEK} games.")

# Build both directions: home→away and away→home
home_side = schedule.rename(columns={"home": "team", "away": "opponent"})
away_side = schedule.rename(columns={"away": "team", "home": "opponent"})
matchups = pd.concat([home_side, away_side], ignore_index=True)[["week", "team", "opponent"]]

# Write ONLY this week to a new table
conn = sqlite3.connect(db_path)
matchups.to_sql("nfl_matchups_week1", conn, if_exists="replace", index=False)
conn.close()

print("✅ nfl_matchups_week1 table created successfully in fantasy.db")
print(matchups.head())
