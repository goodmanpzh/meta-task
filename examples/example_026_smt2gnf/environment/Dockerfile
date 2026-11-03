FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y procps jq bc && rm -rf /var/lib/apt/lists/*

COPY generate_evidence.py /tmp/generate_evidence.py
RUN python3 /tmp/generate_evidence.py && rm /tmp/generate_evidence.py && rm -f /tmp/build_metadata.json

RUN mkdir -p /app/output
