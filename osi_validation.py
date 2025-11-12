import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression
from scipy.stats import pearsonr

# --- Connect to DB ---
conn = sqlite3.connect("C:/Users/cmice/repo/fantasy/fantasy.db")
print("✅ Connected to DB...")

# --- Query ---
query = """
SELECT 
    a.position,
    a.pts_ppr      AS actual_pts,
    e.ease_factor  AS ease
FROM all_weeks a
JOIN opponent_strength_offadj e
  ON a.opponent = e.defense_team
 AND a.position = e.position
WHERE a.pts_ppr IS NOT NULL
  AND e.ease_factor IS NOT NULL;
"""

df = pd.read_sql(query, conn)
print(f"✅ Retrieved {len(df)} rows")
print(df.head())
# ✅ Close connection AFTER pulling data
conn.close()

# --- Run regression and correlation ---
results = {}
for pos in df['position'].unique():
    sub = df[df['position'] == pos]
    X = sub[['ease']].values
    y = sub['actual_pts'].values

    if len(sub) < 5:  # Skip tiny groups
        continue

    model = LinearRegression().fit(X, y)
    r2 = model.score(X, y)
    coef = model.coef_[0]
    corr, p = pearsonr(X.flatten(), y)

    results[pos] = {
        'R2': r2,
        'Coefficient': coef,
        'Pearson r': corr,
        'p-value': p,
        'n': len(sub)
    }

# --- Print results ---
print("\n📊 Regression Results:")
for pos, stats in results.items():
    print(f"{pos}: R²={stats['R2']:.3f} | coef={stats['Coefficient']:.3f} | "
          f"r={stats['Pearson r']:.3f} | p={stats['p-value']:.3f} | n={stats['n']}")
