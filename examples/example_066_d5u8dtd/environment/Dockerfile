FROM python:3.11-slim AS builder
WORKDIR /app
COPY generate_crypto.py /tmp/generate_crypto.py
RUN pip install --no-cache-dir numpy==1.24.0 && python /tmp/generate_crypto.py

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy==1.24.0
COPY --from=builder /app/data /app/data
