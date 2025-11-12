import requests, json

for week in range(1, 2):     # sets extraction for weeks 1–9
    url = f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{week}"  # pulls data for 2025 season
    data = requests.get(url).json() # fetches JSON data from the URL
    with open(f"week{week}_raw.json", "w") as f:
        json.dump(data, f)  # saves each week's data to a separate JSON file


