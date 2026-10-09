# Heatwave Early Warning - Cloud Computing Mini Project (KJS-CES-01)

Educational prototype on **synthetic** data (not an official IMD warning). Experiments: 2 (Docker), 3 (Kubernetes), 4 (EC2 Linux/Windows), 7 (right-sizing).

## Files
| File | Purpose |
|---|---|
| `data/generate_data.py`, `data/heat_data.csv` | synthetic daily Tmax for 7 regions, 2014-2023 |
| `train.py`, `common.py`, `model.joblib` | trains Random Forest models; simplified IMD rule; metrics in `results/model_metrics.json` |
| `app.py`, `templates/index.html` | Flask API (`/predict`, `/health`) and web form |
| `Dockerfile`, `requirements.txt` | container image (Exp 2) |
| `k8s/deployment.yaml`, `k8s/service.yaml` | Kubernetes deployment, 2 replicas + NodePort 30080 (Exp 3) |
| `tests/test_api.py` | 8 functional + invalid-input tests |
| `loadtest.py` | load generator (throughput, latency) |
| `exp7_rightsizing.py` | over-provisioned vs right-sized run with `docker stats` (Exp 7) |

## Run locally
```
pip install -r requirements.txt
python data/generate_data.py && python train.py     # optional: model.joblib is included
python app.py                                        # http://localhost:5000
python tests/test_api.py http://localhost:5000
```

## Docker (Exp 2)
```
docker build -t YOUR_USER/heatwave-api:v1 .
docker run -d -p 8080:5000 --name hw YOUR_USER/heatwave-api:v1
docker push YOUR_USER/heatwave-api:v1
```

## Kubernetes (Exp 3, Killercoda)
```
sed -i 's/DOCKERHUB_USER/YOUR_USER/' k8s/deployment.yaml
kubectl apply -f k8s/ && kubectl get pods,svc
curl localhost:30080/health
```

## EC2 (Exp 4)
```
sudo apt-get update && sudo apt-get install -y docker.io
sudo docker run -d -p 8080:5000 YOUR_USER/heatwave-api:v1     # open http://<ip>:8080 from the Windows instance
```

## Right-sizing (Exp 7)
```
pip install requests
python exp7_rightsizing.py --image YOUR_USER/heatwave-api:v1
```
Costs are **estimates** (Fargate-style per vCPU-hour / GB-hour rates, editable via `--cpu-hour-usd`, `--gb-hour-usd`), not AWS charges.
