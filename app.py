import streamlit as st
import pandas as pd
import numpy as np
import sqlite3

# ============================
# LOAD DATA
# ============================
@st.cache_data
def load_data():
    conn = sqlite3.connect("fantasy.db")
    df = pd.read_sql("SELECT * FROM week11_simulated_all", conn)
    conn.close()
    return df

df = load_data()

# ============================
# PAGE SETUP + STYLING
# ============================
st.set_page_config(layout="wide")

st.markdown("""
    <style>
        body {
            background-color: #f7f1e3;
            font-family: Georgia, serif;
        }
        .main-title {
            font-size: 40px;
            text-align: center;
            color: #3e2723;
            margin-bottom: 5px;
        }
        .subtitle {
            text-align: center;
            color: #5d4037;
            margin-bottom: 20px;
        }
        .rank-table th {
            padding: 8px 4px;
            border-bottom: 2px solid #3e2723;
            color: #3e2723;
            font-size: 16px;
        }
        .rank-table td {
            padding: 6px 4px;
            border-bottom: 1px solid #d7ccc8;
            font-size: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# ============================
# TITLE
# ============================
st.markdown("<div class='main-title'>🏈 Week 11 Fantasy Projections</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Regression + Monte Carlo Simulation</div>", unsafe_allow_html=True)
st.markdown("---")

# ============================
# FILTERS + SEARCH
# ============================
col1, col2 = st.columns([1, 1])

with col1:
    pos_filter = st.multiselect(
        "Filter by position:",
        df["position"].unique(),
        default=df["position"].unique()
    )

with col2:
    search = st.text_input("Search player:")

filtered = df[df["position"].isin(pos_filter)].copy()

if search.strip():
    filtered = filtered[filtered["playerName"].str.contains(search, case=False)]

filtered = filtered.sort_values("median", ascending=False)
filtered.insert(0, "Rank", range(1, len(filtered) + 1))

# ============================
# BOOM / BUST CALCULATION
# ============================
def boom_bust(row):
    p10 = row["p10"]
    p90 = row["p90"]
    projection = row["median"]

    spread = p90 - p10
    if spread <= 0:
        std = 1.0
    else:
        std = spread / 2.56  # approx 1.28σ each side

    sims = np.random.normal(loc=projection, scale=std, size=5000)

    boom = np.mean(sims > p90) * 100   # chance to beat P90
    bust = np.mean(sims < p10) * 100   # chance to fall below P10

    return round(boom, 1), round(bust, 1)

boom_list = []
bust_list = []

for _, r in filtered.iterrows():
    b1, b2 = boom_bust(r)
    boom_list.append(b1)
    bust_list.append(b2)

filtered["Boom%"] = boom_list
filtered["Bust%"] = bust_list

# ============================
# RANKING TABLE
# ============================
st.markdown("<h3 style='color:#3e2723;'>Overall Rankings</h3>", unsafe_allow_html=True)

table_html = """
<table class='rank-table' style='width:100%; border-collapse:collapse;'>
<tr>
    <th>Rank</th>
    <th>Name</th>
    <th>Pos</th>
    <th>Team</th>
    <th>Opp</th>
    <th>Projection</th>
    <th>Boom%</th>
    <th>Bust%</th>
</tr>
"""

for _, row in filtered.iterrows():
    table_html += (
        "<tr>"
        f"<td>{int(row['Rank'])}</td>"
        f"<td>{row['playerName']}</td>"
        f"<td>{row['position']}</td>"
        f"<td>{row['team']}</td>"
        f"<td>{row['opponent']}</td>"
        f"<td>{row['median']:.1f}</td>"
        f"<td>{row['Boom%']}</td>"
        f"<td>{row['Bust%']}</td>"
        "</tr>"
    )

table_html += "</table>"

st.markdown(table_html, unsafe_allow_html=True)

# ============================
# PROJECTED STATLINE SECTION
# ============================
st.markdown("---")
st.markdown("<h3 style='color:#3e2723;'>Projected Statline</h3>", unsafe_allow_html=True)

if not filtered.empty:
    player_choice = st.selectbox(
        "Select a player to view projected stats:",
        filtered["playerName"].unique()
    )

    row = filtered[filtered["playerName"] == player_choice].iloc[0]

    st.markdown(
        f"**{row['playerName']}** "
        f"({row['team']} • {row['position']} vs {row['opponent']})"
    )

    # Define which projected stat columns to look for by position
    pos = row["position"]

    if pos == "QB":
        desired_cols = [
            ("proj_pass_att", "Pass Attempts"),
            ("proj_pass_cmp", "Completions"),
            ("proj_pass_yd",  "Pass Yards"),
            ("proj_pass_td",  "Pass TD"),
            ("proj_pass_int", "Interceptions"),
            ("proj_rush_att", "Rush Attempts"),
            ("proj_rush_yd",  "Rush Yards"),
            ("proj_rush_td",  "Rush TD"),
        ]
    elif pos == "RB":
        desired_cols = [
            ("proj_rush_att", "Rush Attempts"),
            ("proj_rush_yd",  "Rush Yards"),
            ("proj_rush_td",  "Rush TD"),
            ("proj_rec_tgt",  "Targets"),
            ("proj_rec",      "Receptions"),
            ("proj_rec_yd",   "Rec Yards"),
            ("proj_rec_td",   "Rec TD"),
        ]
    elif pos in ("WR", "TE"):
        desired_cols = [
            ("proj_rec_tgt",  "Targets"),
            ("proj_rec",      "Receptions"),
            ("proj_rec_yd",   "Rec Yards"),
            ("proj_rec_td",   "Rec TD"),
        ]
    else:
        # Fallback: show any proj_ columns generically
        desired_cols = [
            (c, c) for c in row.index if c.startswith("proj_")
        ]

    # Build a simple bullet list for existing projected stats
    lines = []
    for col, label in desired_cols:
        if col in row.index and pd.notnull(row[col]):
            try:
                val = float(row[col])
                lines.append(f"- **{label}:** {val:.1f}")
            except (TypeError, ValueError):
                lines.append(f"- **{label}:** {row[col]}")

    if lines:
        st.markdown("\n".join(lines))
    else:
        st.markdown("_No projected statline columns found yet. Make sure you add `proj_...` columns in your prediction script and save them into `week11_simulated_all`._")
else:
    st.markdown("_No players match the current filter/search._")
