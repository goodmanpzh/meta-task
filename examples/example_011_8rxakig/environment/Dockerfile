FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y procps gcc g++ build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir numpy==1.24.0 scipy==1.11.4

COPY knn.py /app/knn.py
COPY knn_baseline.py /app/knn_baseline.py
COPY benchmark.py /app/benchmark.py
