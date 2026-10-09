"""Simple load test. Usage: python loadtest.py URL [seconds=30] [threads=8] [think_seconds=0]
Prints throughput and latency stats, and writes a JSON summary line."""
import sys, time, json, random, threading, statistics, requests
url = sys.argv[1].rstrip("/") + "/predict"
secs = int(sys.argv[2]) if len(sys.argv) > 2 else 30
threads = int(sys.argv[3]) if len(sys.argv) > 3 else 8
think = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0   # pause between requests = realistic user traffic
regions = ["Northwest", "Central", "East", "Northeast", "South Peninsula", "West Coast", "Hills"]
lat, errs, lock = [], [0], threading.Lock()
stop = time.time() + secs

def worker():
    s = requests.Session()
    while time.time() < stop:
        t = random.uniform(30, 47)
        body = {"region": random.choice(regions), "date": "2026-05-%02d" % random.randint(1, 28),
                "temp_today": round(t, 1), "temp_yesterday": round(t - 1, 1), "temp_2days_ago": round(t - 2, 1)}
        t0 = time.perf_counter()
        try:
            ok = s.post(url, json=body, timeout=30).status_code == 200
        except Exception:
            ok = False
        dt = (time.perf_counter() - t0) * 1000
        with lock:
            lat.append(dt); errs[0] += (not ok)
        time.sleep(think)

ts = [threading.Thread(target=worker) for _ in range(threads)]
start = time.time(); [t.start() for t in ts]; [t.join() for t in ts]
el = time.time() - start
lat.sort()
res = {"requests": len(lat), "errors": errs[0], "duration_s": round(el, 1), "threads": threads,
       "throughput_rps": round(len(lat) / el, 1), "avg_ms": round(statistics.mean(lat), 1),
       "p95_ms": round(lat[int(0.95 * len(lat)) - 1], 1), "max_ms": round(lat[-1], 1)}
print(json.dumps(res))
