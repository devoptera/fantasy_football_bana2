import sqlite3
import pandas as pd
import numpy as np

# ======================================
# Load Week 11 Projections for All Positions
# ======================================
conn = sqlite3.connect("fantasy.db")

wr = pd.read_sql("SELECT * FROM wr_week11_predictions", conn)
rb = pd.read_sql("SELECT * FROM rb_week11_predictions", conn)
te = pd.read_sql("SELECT * FROM te_week11_predictions", conn)
qb = pd.read_sql("SELECT * FROM qb_week11_predictions", conn)

# ======================================
# Load residuals (for Monte Carlo)
# ======================================
wr_resid = pd.read_sql("SELECT playerID, resid FROM wr_residuals", conn)
rb_resid = pd.read_sql("SELECT playerID, resid FROM rb_residuals", conn)
te_resid = pd.read_sql("SELECT playerID, resid FROM te_residuals", conn)
qb_resid = pd.read_sql("SELECT playerID, resid FROM qb_residuals", conn)

# Build lookup maps
residual_lookup = {
    "WR": wr_resid.groupby("playerID")["resid"].apply(list).to_dict(),
    "RB": rb_resid.groupby("playerID")["resid"].apply(list).to_dict(),
    "TE": te_resid.groupby("playerID")["resid"].apply(list).to_dict(),
    "QB": qb_resid.groupby("playerID")["resid"].apply(list).to_dict(),
}

# ======================================
# Add Standardized Projected Stat Columns
# ======================================

# ---- WR ----
wr["proj_rec_tgt"] = wr["rec_tgt"]
wr["proj_rec"]     = wr["rec"]
wr["proj_rec_yd"]  = wr["rec_yd"]
wr["proj_rec_td"]  = wr["rec_td"]

# ---- TE ----
te["proj_rec_tgt"] = te["rec_tgt"]
te["proj_rec"]     = te["rec"]
te["proj_rec_yd"]  = te["rec_yd"]
te["proj_rec_td"]  = te["rec_td"]

# ---- RB ----
rb["proj_rush_att"] = rb["rush_att"]
rb["proj_rush_yd"]  = rb["rush_yd"]
rb["proj_rush_td"]  = rb["rush_td"]

rb["proj_rec_tgt"]  = rb["rec_tgt"]
rb["proj_rec"]      = rb["rec"]
rb["proj_rec_yd"]   = rb["rec_yd"]
rb["proj_rec_td"]   = rb["rec_td"]

# ---- QB ----
qb["proj_pass_att"] = qb["pass_att"]
qb["proj_pass_cmp"] = qb["pass_cmp"]
qb["proj_pass_yd"]  = qb["pass_yd"]
qb["proj_pass_td"]  = qb["pass_td"]
qb["proj_pass_int"] = qb["pass_int"]

# QBs often have rushing columns too
if "rush_att" in qb.columns:
    qb["proj_rush_att"] = qb["rush_att"]
else:
    qb["proj_rush_att"] = 0

qb["proj_rush_yd"]  = qb["rush_yd"]
qb["proj_rush_td"]  = qb["rush_td"]

# ======================================
# Combine all positions
# ======================================
combined = pd.concat([wr, rb, te, qb], ignore_index=True)

# ======================================
# Monte Carlo Simulation
# ======================================
def simulate_player(mu, residuals, sims=5000):
    # if player has no residuals → fallback low variance
    if residuals is None or len(residuals) == 0:
        draws = np.random.normal(loc=mu, scale=4.0, size=sims)
    else:
        draws = mu + np.random.choice(residuals, size=sims, replace=True)

    p10 = np.percentile(draws, 10)
    median = np.percentile(draws, 50)
    p90 = np.percentile(draws, 90)

    return median, p10, p90


medians = []
p10s = []
p90s = []

for _, row in combined.iterrows():
    pos = row["position"]
    pid = row["playerID"]
    mu  = row["mu"]

    residuals = residual_lookup.get(pos, {}).get(pid, [])

    median, p10, p90 = simulate_player(mu, residuals)
    medians.append(median)
    p10s.append(p10)
    p90s.append(p90)

combined["median"] = medians
combined["p10"] = p10s
combined["p90"] = p90s

# ======================================
# Save Combined Table
# ======================================
combined.to_sql("week11_simulated_all", conn, if_exists="replace", index=False)

conn.close()

print("✔ week11_simulated_all generated successfully!")
