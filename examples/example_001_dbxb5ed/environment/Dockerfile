FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install numpy==1.26.4

# Copy task files
COPY utils.py /app/utils.py
COPY reference_trainer.py /app/reference_trainer.py
COPY distributed_trainer.py /app/distributed_trainer.py
