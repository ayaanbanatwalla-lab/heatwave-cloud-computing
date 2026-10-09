"""Heatwave early-warning API (educational prototype, SYNTHETIC data)."""
import os, time, datetime, socket
import joblib, numpy as np, pandas as pd
from flask import Flask, request, jsonify, render_template
from common import REGION_LIST, normal_temp, imd_rule, LABELS

app = Flask(__name__)
BUNDLE = joblib.load(os.path.join(os.path.dirname(__file__), "model.joblib"))
REG, CLF, FEATURES = BUNDLE["reg"], BUNDLE["clf"], BUNDLE["features"]
for m in (REG, CLF):
    m.set_params(n_jobs=1)
STARTED = time.time()

ADVICE = {
    0: "No heatwave expected. Normal precautions; stay hydrated.",
    1: "HEATWAVE likely. Avoid outdoor work 12:00-16:00, drink water often, check on elderly and children. Farmers: irrigate in early morning/evening.",
    2: "SEVERE HEATWAVE likely. Stay indoors in peak hours, hospitals on alert for heatstroke, local authorities to open cooling shelters. Postpone outdoor activity.",
}


class BadInput(ValueError):
    pass


def parse(payload: dict):
    region = payload.get("region")
    if region not in REGION_LIST:
        raise BadInput(f"region must be one of {REGION_LIST}")
    try:
        date = datetime.date.fromisoformat(str(payload.get("date")))
    except ValueError:
        raise BadInput("date must be YYYY-MM-DD")
    temps = []
    for k in ("temp_today", "temp_yesterday", "temp_2days_ago"):
        try:
            v = float(payload.get(k))
        except (TypeError, ValueError):
            raise BadInput(f"{k} must be a number")
        if not np.isfinite(v) or not -10.0 <= v <= 60.0:
            raise BadInput(f"{k} must be between -10 and 60 degrees C")
        temps.append(v)
    return region, date, temps


def predict(region, date, temps):
    t0, t1, t2 = temps
    doy = min(date.timetuple().tm_yday, 365)
    normal0 = normal_temp(region, doy)
    nnext = normal_temp(region, min(doy + 1, 365))
    row = pd.DataFrame([{
        "region_id": REGION_LIST.index(region),
        "sin": np.sin(2 * np.pi * doy / 365), "cos": np.cos(2 * np.pi * doy / 365),
        "tmax": t0, "next_normal": nnext, "dep": t0 - normal0,
        "dep1": t1 - normal_temp(region, max(doy - 1, 1)),
        "dep2": t2 - normal_temp(region, max(doy - 2, 1)),
    }])[FEATURES]
    pred_t = float(REG.predict(row)[0] + nnext)
    proba = CLF.predict_proba(row)[0]
    ml_cls = int(CLF.classes_[int(np.argmax(proba))])
    cls = imd_rule(region, pred_t, nnext)      # primary: AI temperature forecast -> simplified IMD rule (hybrid)
    return {
        "region": region, "date": date.isoformat(),
        "predicted_next_day_tmax_c": round(pred_t, 1),
        "risk_level": LABELS[cls],
        "ml_classifier_risk": LABELS[ml_cls],
        "risk_probabilities": {LABELS[int(c)]: round(float(p), 3) for c, p in zip(CLF.classes_, proba)},
        "rule_baseline_today": LABELS[imd_rule(region, t0, normal0)],
        "normal_tmax_c": round(normal0, 1),
        "alert": ADVICE[cls],
        "disclaimer": "Educational prototype on SYNTHETIC data. Not an official IMD warning.",
        "served_by": socket.gethostname(),
    }


@app.get("/")
def index():
    return render_template("index.html", regions=REGION_LIST, today=datetime.date.today().isoformat())


@app.post("/predict")
def predict_api():
    payload = request.get_json(silent=True) or request.form.to_dict()
    try:
        return jsonify(predict(*parse(payload)))
    except BadInput as e:
        return jsonify({"error": str(e)}), 400


@app.get("/health")
def health():
    return jsonify({"status": "ok", "uptime_s": round(time.time() - STARTED, 1), "pod": socket.gethostname()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
