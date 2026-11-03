FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    procps \
    tcpdump \
    tshark \
    netcat-openbsd \
    curl \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install scapy==2.6.1 dpkt==1.9.8

# Copy and run the environment setup script
COPY setup_env.py /tmp/setup_env.py
RUN python3 /tmp/setup_env.py && rm /tmp/setup_env.py
