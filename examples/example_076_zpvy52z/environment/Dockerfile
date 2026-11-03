FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y procps curl git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.12.0 scikit-learn==1.4.0 matplotlib==3.8.3 pandas==2.2.0

# Copy data generation script, run it, and clean up in one layer
COPY generate_data.py /tmp/generate_data.py
RUN python /tmp/generate_data.py && rm -f /tmp/generate_data.py /app/.ground_truth.json

# Create a partial analysis script to simulate previous work
COPY previous_analysis.py /app/previous_analysis.py
