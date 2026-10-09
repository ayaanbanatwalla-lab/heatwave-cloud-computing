"""Generate CLEARLY LABELLED SYNTHETIC daily max-temperature data (5 years x 7 regions)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from common import REGIONS, normal_temp

rng = np.random.default_rng(42)
rows = []
for region in REGIONS:
    for year in range(2014, 2024):
        anomaly = 0.0
        spell = 0          # remaining days of a heat spell
        spell_amp = 0.0
        for doy in range(1, 366):
            anomaly = 0.75 * anomaly + rng.normal(0, 1.1)       # AR(1) weather noise
            if spell == 0 and 70 <= doy <= 170 and rng.random() < 0.025:
                spell, spell_amp = int(rng.integers(3, 9)), rng.uniform(4.0, 8.5)
            boost = spell_amp if spell > 0 else 0.0
            spell = max(spell - 1, 0)
            t = normal_temp(region, doy) + anomaly + boost
            rows.append((f"{year}-{doy:03d}", region, doy, round(float(t), 1)))
df = pd.DataFrame(rows, columns=["date", "region", "doy", "tmax"])
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "heat_data.csv")
df.to_csv(out, index=False)
print(f"SYNTHETIC data written: {out}  rows={len(df)}")
