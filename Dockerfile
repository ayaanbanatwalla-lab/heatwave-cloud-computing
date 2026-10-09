FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=5000
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common.py app.py model.joblib ./
COPY templates ./templates
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:5000/health')" || exit 1
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "60", "app:app"]
