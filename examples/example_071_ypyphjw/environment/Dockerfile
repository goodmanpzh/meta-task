FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    iverilog \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/output /app/src /app/testbench /app/reference /logs/verifier

# Copy reference GF(2^4) tables (only .py files)
COPY reference/*.py /app/reference/

# Copy source skeleton
COPY src/ /app/src/

# Copy testbench
COPY testbench/ /app/testbench/

# Copy and run test vector generator, then remove it
COPY gen_test_vectors.py /app/gen_test_vectors.py
RUN python3 /app/gen_test_vectors.py && rm /app/gen_test_vectors.py

CMD ["/bin/bash"]
