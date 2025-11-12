import pandas as pd
import numpy as np
import sqlite3
from sklearn.linear_model import LinearRegression

# ---------- SETUP ----------
conn = sqlite3.connect(r"C:/Users/cmice/repo/fantasy/fantasy.db")

# ---------- TRAIN REGRESSION ----------
wr = pd.read_sql("""
    SELECT * FROM all_weeks_joined
    WHERE position='WR' AND week_num <= 9
""", conn)

features = ["rec_tgt","rec","rec_yd","rec_td","off_snp","ease_factor"]
X = wr[features].fillna(0)
y = wr["pts_ppr"]

model = LinearRegression().fit(X, y)
wr["resid"] = y - model.predict(X)

print("Intercept:", model.intercept_)
print(pd.DataFrame({"feature": features, "coef": model.coef_}))
print("R²:", model.score(X, y))
print("Sample residuals:")
print(wr["resid"].head())

# Save model info
pd.DataFrame({"feature": features, "coef": model.coef_}).to_sql("wr_model_coefs", conn, if_exists="replace", index=False)
wr[["playerID","week_num","resid"]].to_sql("wr_residuals", conn, if_exists="replace", index=False)

# ---------- BUILD PLAYER RATES ----------
rate_df = (
    wr.groupby("playerID", as_index=False)
      .agg(rec_sum=("rec","sum"),
           tgt_sum=("rec_tgt","sum"),
           yds_sum=("rec_yd","sum"),
           td_sum=("rec_td","sum"))
)

pos_catch_rate = rate_df["rec_sum"].sum() / rate_df["tgt_sum"].sum()
pos_ypt = rate_df["yds_sum"].sum() / rate_df["tgt_sum"].sum()
pos_td_rate = rate_df["td_sum"].sum() / rate_df["tgt_sum"].sum()

rate_df["catch_rate"] = rate_df["rec_sum"] / rate_df["tgt_sum"]
rate_df["ypt"] = rate_df["yds_sum"] / rate_df["tgt_sum"]
rate_df["td_rate"] = rate_df["td_sum"] / rate_df["tgt_sum"]

for col, lo, hi, fallback in [
    ("catch_rate", 0.3, 0.9, pos_catch_rate),
    ("ypt",        4.0, 14.0, pos_ypt),
    ("td_rate",    0.0, 0.20, pos_td_rate),
]:
    rate_df[col] = rate_df[col].replace([np.inf, -np.inf], np.nan)
    rate_df[col] = rate_df[col].fillna(fallback).clip(lo, hi)

# ---------- PREPARE WEEK 11 INPUTS ----------
week11_wr = pd.read_sql("""
    SELECT * FROM week11_inputs
    WHERE position='WR'
""", conn)

# Normalize naming
week11_wr = week11_wr.rename(columns={
    "rec_tgt_base": "rec_tgt",
    "rush_att_base": "rush_att",
    "off_snp_base": "off_snp",
    "ease_base": "ease_factor"
})

# Merge player-specific rate data
week11_wr = week11_wr.merge(
    rate_df[["playerID","catch_rate","ypt","td_rate"]],
    on="playerID", how="left"
)

# Fill missing with position-wide averages
week11_wr["catch_rate"] = week11_wr["catch_rate"].fillna(pos_catch_rate).clip(0.3,0.9)
week11_wr["ypt"] = week11_wr["ypt"].fillna(pos_ypt).clip(4.0,14.0)
week11_wr["td_rate"] = week11_wr["td_rate"].fillna(pos_td_rate).clip(0.0,0.20)

# Compute expected stats from targets
week11_wr["rec"] = week11_wr["rec_tgt"] * week11_wr["catch_rate"]
week11_wr["rec_yd"] = week11_wr["rec_tgt"] * week11_wr["ypt"]
week11_wr["rec_td"] = week11_wr["rec_tgt"] * week11_wr["td_rate"]

# ---------- PREDICT WEEK 11 ----------
X11 = week11_wr[["rec_tgt","rec","rec_yd","rec_td","off_snp","ease_factor"]].fillna(0)
week11_wr["mu"] = model.predict(X11)

print("\n--- WEEK 11 EXPECTED POINTS (FIXED) ---")
print(week11_wr[["playerName","team","opponent","rec_tgt","rec","rec_yd","rec_td","mu"]]
      .sort_values("mu", ascending=False).head(20))

week11_wr.to_sql("wr_week11_predictions", conn, if_exists="replace", index=False)
conn.close()
