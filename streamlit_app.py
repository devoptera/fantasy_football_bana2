import streamlit as st
import pandas as pd
import sqlite3

DB_PATH = "fantasy.db"
TABLE = "week11_projections"

st.set_page_config(page_title="Week 11 Fantasy Projections", layout="wide")

st.title("📊 Week 11 Fantasy Projections")

# ---------------------------
# LOAD DATA
# ---------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM {TABLE}", conn)
    conn.close()
    return df

df = load_data()

# Basic cleaning
df["proj"] = df["proj"].astype(float)
df["rank"] = df["rank"].astype(float)

# ---------------------------
# SIDEBAR FILTERS
# ---------------------------
st.sidebar.header("Filters")

pos_options = ["ALL"] + sorted(df["position"].unique())
selected_pos = st.sidebar.selectbox("Position", pos_options)

search_name = st.sidebar.text_input("Search Player")

# ---------------------------
# APPLY FILTERS
# ---------------------------
df_filtered = df.copy()

if selected_pos != "ALL":
    df_filtered = df_filtered[df_filtered["position"] == selected_pos]

# Auto-complete search using selectbox
all_players = ["(None)"] + sorted(df["playerName"].unique())
selected_player = st.sidebar.selectbox("Search Player", all_players)

if selected_player != "(None)":
    df_filtered = df_filtered[df_filtered["playerName"] == selected_player]


# Sort by projection descending
df_filtered = df_filtered.sort_values("proj", ascending=False)

# ---------------------------
# MAIN TABLE
# ---------------------------
st.subheader("Projections")
st.dataframe(
    df_filtered[["rank", "playerName", "team", "position", "proj"]]
    .sort_values("rank")
    .reset_index(drop=True)
)
