"""Train next-day Tmax regressor + next-day heat-risk classifier; compare with rule baseline."""
import json, time, joblib
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, accuracy_score, f1_score, confusion_matrix
from common import REGION_LIST, normal_temp, imd_rule, LABELS

df = pd.read_csv("data/heat_data.csv")
df["year"] = df["date"].str[:4].astype(int)
df = df.sort_values(["region", "year", "doy"]).reset_index(drop=True)

g = df.groupby(["region", "year"])["tmax"]
df["t1"] = g.shift(1); df["t2"] = g.shift(2); df["next"] = g.shift(-1)
df = df.dropna().reset_index(drop=True)
df["normal"] = [normal_temp(r, d) for r, d in zip(df.region, df.doy)]
df["dep"] = df.tmax - df.normal
df["dep1"] = df.t1 - [normal_temp(r, max(d - 1, 1)) for r, d in zip(df.region, df.doy)]
df["dep2"] = df.t2 - [normal_temp(r, max(d - 2, 1)) for r, d in zip(df.region, df.doy)]
df["region_id"] = df.region.map({r: i for i, r in enumerate(REGION_LIST)})
df["sin"] = np.sin(2 * np.pi * df.doy / 365); df["cos"] = np.cos(2 * np.pi * df.doy / 365)
df["next_normal"] = [normal_temp(r, min(d + 1, 365)) for r, d in zip(df.region, df.doy)]
df["target_anom"] = df["next"] - df.next_normal
df["label"] = [imd_rule(r, t, n) for r, t, n in zip(df.region, df["next"], df.next_normal)]

FEATURES = ["region_id", "sin", "cos", "tmax", "next_normal", "dep", "dep1", "dep2"]
train, test = df[df.year < 2022], df[df.year >= 2022]      # time-based split
X_tr, X_te = train[FEATURES], test[FEATURES]

reg = RandomForestRegressor(n_estimators=100, min_samples_leaf=8, random_state=42, n_jobs=1).fit(X_tr, train["target_anom"])
clf = RandomForestClassifier(n_estimators=100, min_samples_leaf=8, class_weight="balanced", random_state=42, n_jobs=1).fit(X_tr, train["label"])

mae = mean_absolute_error(test["next"], reg.predict(X_te) + test.next_normal)
persist_mae = mean_absolute_error(test["next"], test["tmax"])          # baseline: tomorrow = today
pred = clf.predict(X_te)
base = [imd_rule(r, t, n) for r, t, n in zip(test.region, test.tmax, test.normal)]  # rule on TODAY's temp
pred_next = reg.predict(X_te) + test.next_normal.values
hyb = [imd_rule(r, t, n) for r, t, n in zip(test.region, pred_next, test.next_normal)]   # AI forecast -> rule
metrics = {
    "hybrid_accuracy": round(accuracy_score(test.label, hyb), 4),
    "hybrid_macro_F1": round(f1_score(test.label, hyb, average="macro"), 4),
    "train_rows": int(len(train)), "test_rows": int(len(test)),
    "regressor_MAE_C": round(mae, 3), "persistence_baseline_MAE_C": round(persist_mae, 3),
    "classifier_accuracy": round(accuracy_score(test.label, pred), 4),
    "classifier_macro_F1": round(f1_score(test.label, pred, average="macro"), 4),
    "rule_baseline_accuracy": round(accuracy_score(test.label, base), 4),
    "rule_baseline_macro_F1": round(f1_score(test.label, base, average="macro"), 4),
    "confusion_matrix": confusion_matrix(test.label, pred, labels=[0, 1, 2]).tolist(),
    "class_counts_test": test.label.value_counts().sort_index().to_dict(),
    "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
}
joblib.dump({"reg": reg, "clf": clf, "features": FEATURES}, "model.joblib", compress=3)
json.dump(metrics, open("results/model_metrics.json", "w"), indent=2, default=int)
print(json.dumps(metrics, indent=2, default=int))
