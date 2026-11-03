FROM python:3.11-slim

WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y \
    procps \
    bash \
    coreutils \
    findutils \
    gawk \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Generate the WAL fragments
COPY generate_fragments.py /tmp/generate_fragments.py
RUN python3 /tmp/generate_fragments.py && rm /tmp/generate_fragments.py

# Remove the generation manifest (answer key) - keep only FORMAT_SPEC.txt
RUN rm -f /app/.generation_manifest.json

# Create output directory
RUN mkdir -p /app/recovered
