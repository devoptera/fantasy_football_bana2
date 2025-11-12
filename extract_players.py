import requests
import json
import os

# ----- Configuration -----
save_path = r"C:\Users\Collin Anderson\fantasy\players.json"
url = "https://api.sleeper.app/v1/players/nfl"
# --------------------------

print("📡 Fetching player data from Sleeper...")

# Fetch JSON data
response = requests.get(url)
response.raise_for_status()  # raises error if bad response
players_data = response.json()

# Save to file
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(players_data, f, indent=2)

size_mb = os.path.getsize(save_path) / (1024 * 1024)
print(f"✅ Saved players.json to {save_path} ({size_mb:.2f} MB)")

