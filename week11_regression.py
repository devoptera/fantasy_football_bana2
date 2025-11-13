import sqlite3
import pandas as pd
import numpy as np
import statsmodels.api as sm

DB_PATH = "fantasy.db"
TABLE = "all_weeks_joined"

TRAIN_START = 1
TRAIN_END = 9     # use weeks 1–9 for training
PRED_WEEK = 11    # predict week 11 using season averages

TARGET = "pts_ppr"

print("\n=== Loading Data ===")
conn = sqlite3.connect(DB_PATH)
df_all = pd.read_sql(f"SELECT * FROM {TABLE}", conn)
print(df_all.head())
print(f"Loaded {len(df_all)} rows\n")

# -----------------------------
# 1. CLEAN + REBUILD TEAM TOTALS
# -----------------------------

team_totals = df_all.groupby(["team", "week_num"]).agg(
    team_pass_att=("pass_att", "sum"),
    team_rush_att=("rush_att", "sum"),
    team_rec_tgt=("rec_tgt", "sum"),
).reset_index()

df_all = df_all.merge(team_totals, on=["team", "week_num"], how="left")

# safety: avoid divide-by-zero
def safe_div(a, b):
    return np.where(b == 0, 0, a / b)

# -----------------------------
# 2. BASIC USAGE STATS
# -----------------------------

df_all["snap_share"] = safe_div(df_all["off_snp"], df_all["off_snp"])  # placeholder; WR/RB won't use this
df_all["target_share"] = safe_div(df_all["rec_tgt"], df_all["team_rec_tgt"])
df_all["carry_share"] = safe_div(df_all["rush_att"], df_all["team_rush_att"])

# QB efficiency
df_all["ypa"] = safe_div(df_all["pass_yd"], df_all["pass_att"])
df_all["cmp_pct"] = safe_div(df_all["pass_cmp"], df_all["pass_att"])

# -----------------------------
# 3. WR-SPECIFIC FIXES
# -----------------------------

print("Building WR receiving yards per game...")

wr_stats = df_all[df_all["position"] == "WR"].groupby("playerID").agg(
    total_yd=("rec_yd", "sum"),
    games=("week_num", "nunique"),
    avg_tgt=("rec_tgt", "mean"),
).reset_index()

wr_stats["wr_yd_per_game"] = wr_stats["total_yd"] / wr_stats["games"]
wr_stats["wr_tgt_per_game"] = wr_stats["avg_tgt"]

df_all = df_all.merge(
    wr_stats[["playerID", "wr_yd_per_game", "wr_tgt_per_game"]],
    on="playerID",
    how="left",
)

df_all["wr_yd_per_game"] = df_all["wr_yd_per_game"].fillna(0)
df_all["wr_tgt_per_game"] = df_all["wr_tgt_per_game"].fillna(0)

# -----------------------------
# 4. AGGREGATE SEASON AVERAGE FEATURES FOR PREDICTION
# -----------------------------

print("Building season-average predictors...")

feature_cols = [
    # Generic usage
    "snap_share",
    "carry_share",
    "target_share",

    # QB Stats
    "pass_att",
    "ypa",
    "cmp_pct",
    "rush_att",
    "rush_yd",

    # Defense adjustment
    "ease_factor",

    # Team context
    "team_pass_att",
    "team_rush_att",
    "team_rec_tgt",

    # WR-only stability features
    "wr_yd_per_game",
    "wr_tgt_per_game",
]


df_pred_avg = df_all.groupby(
    ["playerID", "playerName", "team", "position"]
)[feature_cols].mean().reset_index()

print(df_pred_avg.head())
print(df_pred_avg.shape)

# -----------------------------
# 5. FILTER OUT USELESS WRs
# -----------------------------
print("\nApplying WR filters...")

before_wr = df_pred_avg[df_pred_avg["position"] == "WR"].shape[0]

df_pred_avg = df_pred_avg[~(
    (df_pred_avg["position"] == "WR") &
    (df_pred_avg["wr_tgt_per_game"] < 2.0) &
    (df_pred_avg["wr_yd_per_game"] < 20)
)]

after_wr = df_pred_avg[df_pred_avg["position"] == "WR"].shape[0]

print(f"WRs before filter: {before_wr}, after filter: {after_wr}")

# -----------------------------
# 6. FEATURE SETS FOR REGRESSION
# -----------------------------

features_by_pos = {
    "RB": ["carry_share", "target_share", "rush_yd", "ease_factor"],
    "WR": ["wr_tgt_per_game", "wr_yd_per_game", "ease_factor"],
    "TE": ["target_share", "ease_factor"],
    "QB": ["pass_att", "ypa", "cmp_pct", "rush_yd", "ease_factor"],
}

# -----------------------------
# 7. TRAIN MODELS
# -----------------------------

print("\n=== Training Models ===")
models = {}

df_train = df_all[
    (df_all["week_num"] >= TRAIN_START) &
    (df_all["week_num"] <= TRAIN_END)
]

for pos, feats in features_by_pos.items():
    df_pos = df_train[df_train["position"] == pos].dropna(subset=feats + [TARGET])

    if df_pos.empty:
        print(f"Skipping {pos}: no rows")
        continue

    X = sm.add_constant(df_pos[feats])
    y = df_pos[TARGET]

    model = sm.OLS(y, X).fit()
    models[pos] = model

    print(f"{pos}: n={len(df_pos)}, R²={model.rsquared:.3f}")

# -----------------------------
# 8. APPLY MODELS TO df_pred_avg
# -----------------------------

print("\n=== Running Predictions ===")

def predict_row(row):
    pos = row["position"]
    if pos not in models:
        return None

    feats = features_by_pos[pos]
    X = [1.0] + [row[f] for f in feats]
    return float(np.dot(models[pos].params.values, X))

df_pred_avg["proj"] = df_pred_avg.apply(predict_row, axis=1)

# Drop rows with no projection
df_pred_avg = df_pred_avg.dropna(subset=["proj"])

# -----------------------------
# 9. RANK AND SAVE TO SQLITE
# -----------------------------

df_pred_avg["rank"] = df_pred_avg["proj"].rank(ascending=False)

df_pred_avg.to_sql(
    "week11_projections",
    conn,
    if_exists="replace",
    index=False
)

conn.commit()
conn.close()

print("\nSaved table week11_projections to fantasy.db")

top10 = df_pred_avg.sort_values("proj", ascending=False).head(10)
print("\n=== Top 10 Overall ===")
print(top10[["playerName", "team", "position", "proj"]])
