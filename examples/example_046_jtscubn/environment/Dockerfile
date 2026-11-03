FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y procps net-tools && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install pytest pytest-asyncio

# Copy application files
COPY protocol.md /app/protocol.md
COPY server.py /app/server.py
