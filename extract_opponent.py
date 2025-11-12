import requests
import pandas as pd
import sqlite3
import os

# ---------------- CONFIG ----------------
SEASON = 2025  # Change to 2025 when applicable
DB_PATH = r"C:\Users\Collin Anderson\fantasy\fantasy.db"
# ----------------------------------------

print(f"📡 Fetching NFL schedule for {SEASON} from ESPN API...")

# ESPN API base URL (regular season)
BASE_URL = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&year={SEASON}"

all_games = []

# Loop through each week and collect games
for week in range(1, 19):
    try:
        response = requests.get(f"{BASE_URL}&week={week}")
        if response.status_code != 200:
            print(f"⚠️  Week {week} not found (status {response.status_code}), skipping.")
            continue

        data = response.json()
        events = data.get("events", [])
        if not events:
            print(f"⚠️  No games found for week {week}, skipping.")
            continue

        for event in events:
            try:
                comp = event["competitions"][0]["competitors"]
                home = next(team for team in comp if team["homeAway"] == "home")
                away = next(team for team in comp if team["homeAway"] == "away")

                home_team = home["team"]["abbreviation"]
                away_team = away["team"]["abbreviation"]

                all_games.append({
                    "week": week,
                    "home": home_team,
                    "away": away_team
                })
            except Exception as e:
                print(f"⚠️  Skipped a game in week {week}: {e}")

    except Exception as e:
        print(f"❌  Error fetching week {week}: {e}")

# Make sure we got something
if not all_games:
    raise RuntimeError("No schedule data found. ESPN API might be temporarily unavailable.")

# Convert to DataFrame
schedule = pd.DataFrame(all_games)
print(f"✅ Pulled {len(schedule)} games total across {schedule['week'].nunique()} weeks.")

# Build both directions (home→away and away→home)
home_side = schedule.rename(columns={"home": "team", "away": "opponent"})
away_side = schedule.rename(columns={"away": "team", "home": "opponent"})
matchups = pd.concat([home_side, away_side], ignore_index=True)[["week", "team", "opponent"]]

# ✅ Connect explicitly to SQLite and verify the file exists
if not os.path.exists(DB_PATH):
    print(f"⚠️ Database file not found at {DB_PATH}. Creating a new one...")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
print(f"🔗 Connected to database: {DB_PATH}")

# Optional: drop old table if exists
cur.execute("DROP TABLE IF EXISTS nfl_matchups;")

# ✅ Write DataFrame into SQLite manually
matchups.to_sql("nfl_matchups", conn, if_exists="replace", index=False)

# ✅ Verify it worked
cur.execute("SELECT COUNT(*) FROM nfl_matchups;")
count = cur.fetchone()[0]
conn.commit()
conn.close()

print(f"✅ nfl_matchups table created successfully with {count} rows.")
print("\nPreview of first few matchups:")
print(matchups.head(10))
