FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

# Copy scenario generator, run it, then remove both the script and temp files
COPY generate_scenario.py /tmp/generate_scenario.py
RUN python /tmp/generate_scenario.py \
    && rm -f /tmp/generate_scenario.py \
    && rm -f /tmp/verification_data.json

# Create the output directory
RUN mkdir -p /app/output
