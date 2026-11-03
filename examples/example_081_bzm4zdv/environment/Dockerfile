FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y procps vim && rm -rf /var/lib/apt/lists/*

# Copy the data generation script and the broken reassembly script
COPY generate_capture.py /app/generate_capture.py
COPY reassemble.py /app/reassemble.py

# Generate the capture data
RUN python3 /app/generate_capture.py

# Remove the generation script and verification data (no answer leakage)
RUN rm /app/generate_capture.py && rm /app/data/.verify.json && rm /app/data/.stream_sizes.json
