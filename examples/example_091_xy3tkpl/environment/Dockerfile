FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest

RUN mkdir -p /app/data/snapshots /logs/verifier

COPY generate_data.py /tmp/generate_data.py
RUN python3 /tmp/generate_data.py && rm /tmp/generate_data.py
