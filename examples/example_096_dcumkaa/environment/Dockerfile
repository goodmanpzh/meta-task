FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    procps \
    sqlite3 \
    xxd \
    file \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy data generation script, run it, then remove it
COPY generate_data.py /tmp/generate_data.py
RUN python3 /tmp/generate_data.py && rm /tmp/generate_data.py

# Create output directory for the agent's report
RUN mkdir -p /app/output
