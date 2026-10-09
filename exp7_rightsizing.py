"""Experiment 7 - Cloud cost optimisation through resource right-sizing.

Runs the SAME container + SAME load twice:
  1) over-provisioned limits  2) right-sized limits (computed from phase-1 measurements).
Collects CPU / memory with `docker stats`, latency/throughput with loadtest.py, and estimates cost.

Usage:  python exp7_rightsizing.py --image YOURUSER/heatwave-api:v1
"""
import argparse, json, math, subprocess, sys, threading, time, csv, os, shutil
import requests

ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True)
ap.add_argument("--port", type=int, default=8081)
ap.add_argument("--seconds", type=int, default=45)
ap.add_argument("--threads", type=int, default=4)
ap.add_argument("--think", type=float, default=0.05, help="pause per request (s) -> realistic, not saturating load")
ap.add_argument("--over-cpus", type=float, default=2.0)
ap.add_argument("--over-mem-mib", type=int, default=1024)
ap.add_argument("--cpu-hour-usd", type=float, default=0.04048, help="ESTIMATE: Fargate-style on-demand $/vCPU-hour (verify current price)")
ap.add_argument("--gb-hour-usd", type=float, default=0.004445, help="ESTIMATE: Fargate-style on-demand $/GB-hour (verify current price)")
a = ap.parse_args()
DOCKER = shutil.which("docker") or "docker"
os.makedirs("results", exist_ok=True)


def sh(*cmd):
    return subprocess.run([DOCKER, *cmd], capture_output=True, text=True)


def parse_mem_mib(txt):          # "85.2MiB / 1GiB" -> 85.2
    used = txt.split("/")[0].strip()
    for unit, f in (("GiB", 1024), ("MiB", 1), ("KiB", 1 / 1024), ("kB", 1 / 1000 / 1.048576), ("MB", 1 / 1.048576), ("B", 1 / 1048576)):
        if used.endswith(unit):
            return float(used[:-len(unit)]) * f
    raise ValueError(txt)


def run_phase(name, cpus, mem_mib):
    cname = f"hw-{name}"
    sh("rm", "-f", cname)
    r = sh("run", "-d", "--name", cname, f"--cpus={cpus}", f"--memory={mem_mib}m", "-p", f"{a.port}:5000", a.image)
    if r.returncode:
        sys.exit(f"docker run failed: {r.stderr}")
    url = f"http://localhost:{a.port}"
    for _ in range(60):
        try:
            if requests.get(url + "/health", timeout=2).ok:
                break
        except Exception:
            time.sleep(1)
    else:
        sh("logs", cname); sys.exit("app did not become healthy")
    samples, stop = [], threading.Event()

    def sampler():
        t0 = time.time()
        while not stop.is_set():
            o = sh("stats", "--no-stream", "--format", "{{.CPUPerc}}|{{.MemUsage}}", cname).stdout.strip()
            if "|" in o:
                c, m = o.split("|")
                samples.append((round(time.time() - t0, 1), float(c.strip().rstrip("%")), round(parse_mem_mib(m), 1)))
            time.sleep(0.5)

    th = threading.Thread(target=sampler); th.start()
    out = subprocess.run([sys.executable, "loadtest.py", url, str(a.seconds), str(a.threads), str(a.think)],
                         capture_output=True, text=True).stdout.strip().splitlines()[-1]
    stop.set(); th.join()
    oom = sh("inspect", "-f", "{{.State.OOMKilled}}", cname).stdout.strip()
    sh("rm", "-f", cname)
    lt = json.loads(out)
    cpu = [s[1] for s in samples]; mem = [s[2] for s in samples]
    res = {"phase": name, "cpus": cpus, "mem_mib": mem_mib, **lt,
           "cpu_avg_pct_of_1core": round(sum(cpu) / len(cpu), 1), "cpu_peak_pct_of_1core": max(cpu),
           "mem_avg_mib": round(sum(mem) / len(mem), 1), "mem_peak_mib": max(mem), "oom_killed": oom}
    res["cpu_util_of_alloc_pct"] = round(res["cpu_avg_pct_of_1core"] / (cpus * 100) * 100, 1)
    res["mem_util_of_alloc_pct"] = round(res["mem_avg_mib"] / mem_mib * 100, 1)
    res["est_monthly_usd"] = round(730 * (cpus * a.cpu_hour_usd + mem_mib / 1024 * a.gb_hour_usd), 2)
    with open(f"results/exp7_{name}_samples.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["t_s", "cpu_pct", "mem_mib"]); w.writerows(samples)
    return res


print(f"== Phase 1: over-provisioned ({a.over_cpus} vCPU, {a.over_mem_mib} MiB)")
p1 = run_phase("overprovisioned", a.over_cpus, a.over_mem_mib)
# Right-size: ~25% headroom above peak CPU (0.25 vCPU steps), ~50% above peak memory (64 MiB steps)
new_cpus = max(0.25, math.ceil(p1["cpu_peak_pct_of_1core"] / 100 * 1.25 * 4) / 4)
new_mem = max(128, math.ceil(p1["mem_peak_mib"] * 1.5 / 64) * 64)
print(f"== Right-sized values: {new_cpus} vCPU, {new_mem} MiB")
print(f"== Phase 2: right-sized")
p2 = run_phase("rightsized", new_cpus, new_mem)

rows = [("vCPU allocated", "cpus"), ("Memory allocated (MiB)", "mem_mib"), ("CPU avg (% of 1 core)", "cpu_avg_pct_of_1core"),
        ("CPU peak (% of 1 core)", "cpu_peak_pct_of_1core"), ("CPU utilisation of allocation (%)", "cpu_util_of_alloc_pct"),
        ("Memory peak (MiB)", "mem_peak_mib"), ("Memory utilisation of allocation (%)", "mem_util_of_alloc_pct"),
        ("Throughput (req/s)", "throughput_rps"), ("Avg latency (ms)", "avg_ms"), ("p95 latency (ms)", "p95_ms"),
        ("Errors", "errors"), ("OOM killed", "oom_killed"), ("Est. monthly cost (USD, ESTIMATE)", "est_monthly_usd")]
print(f"\n{'Metric':42s}{'Over-provisioned':>20s}{'Right-sized':>16s}")
for label, k in rows:
    print(f"{label:42s}{str(p1[k]):>20s}{str(p2[k]):>16s}")
saving = (1 - p2["est_monthly_usd"] / p1["est_monthly_usd"]) * 100
print(f"\nEstimated cost reduction: {saving:.1f}%  | throughput change: {(p2['throughput_rps']/p1['throughput_rps']-1)*100:+.1f}%  | p95 latency change: {(p2['p95_ms']/p1['p95_ms']-1)*100:+.1f}%")
print("Cost basis: ESTIMATE using Fargate-style on-demand pricing per vCPU-hour and GB-hour x 730 h/month (not an actual AWS charge).")
json.dump({"over": p1, "right": p2, "cost_reduction_pct": round(saving, 1)}, open("results/exp7_results.json", "w"), indent=2)
