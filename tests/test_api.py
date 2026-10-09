"""Functional + failure tests. Run against a live URL:  python tests/test_api.py http://localhost:8080"""
import sys, requests
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:5000"
ok = {"region": "Central", "date": "2026-05-20", "temp_today": 47, "temp_yesterday": 46, "temp_2days_ago": 45}
cases = [  # (name, payload, expected HTTP status)
    ("valid hot day",          ok, 200),
    ("valid mild day",         {**ok, "date": "2026-12-10", "temp_today": 27, "temp_yesterday": 26, "temp_2days_ago": 26}, 200),
    ("valid hills region",     {**ok, "region": "Hills", "temp_today": 36, "temp_yesterday": 35, "temp_2days_ago": 34}, 200),
    ("INVALID text temp",      {**ok, "temp_today": "hot"}, 400),
    ("INVALID negative temp",  {**ok, "temp_today": -99}, 400),
    ("INVALID region",         {**ok, "region": "Atlantis"}, 400),
    ("INVALID date",           {**ok, "date": "20-05-2026"}, 400),
    ("INVALID missing field",  {k: v for k, v in ok.items() if k != "temp_yesterday"}, 400),
]
fails = 0
for name, payload, want in cases:
    r = requests.post(f"{BASE}/predict", json=payload, timeout=10)
    good = r.status_code == want
    fails += not good
    j = r.json()
    detail = f"{j.get('risk_level')} (pred {j.get('predicted_next_day_tmax_c')} C)" if r.ok else j.get("error")
    print(f"[{'PASS' if good else 'FAIL'}] {name:24s} HTTP {r.status_code} -> {detail}")
print(f"\n{len(cases)-fails}/{len(cases)} passed")
sys.exit(1 if fails else 0)
