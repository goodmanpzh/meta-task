FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    procps \
    supervisor \
    net-tools \
    lsof \
    strace \
    curl \
    vim-tiny \
    less \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /app/data/queue /app/data/results /app/logs /app/output /run/pipeline

# Copy service scripts
COPY queue_server.py /app/queue_server.py
COPY worker.py /app/worker.py
COPY aggregator.py /app/aggregator.py

# Generate job data
COPY generate_jobs.py /app/generate_jobs.py
RUN python3 /app/generate_jobs.py && rm /app/generate_jobs.py

# Copy broken supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/pipeline.conf

# Set up a restrictive file descriptor limit for the worker
# This will cause the worker's fd leak to surface quickly
RUN echo "* soft nofile 64" >> /etc/security/limits.conf && \
    echo "* hard nofile 128" >> /etc/security/limits.conf

# Create a tiny tmpfs mount point (will be mounted at runtime for the aggregator bug)
RUN mkdir -p /tmp/pipeline-out

# Set up the broken environment:
# - supervisord config points to wrong paths
# - wrong ports/addresses
# - wrong user
# - socket permission issues
# - fd limits too low
# - output dir mismatch

# Ensure supervisor base config exists
RUN echo '[supervisord]' > /etc/supervisor/supervisord.conf && \
    echo 'logfile=/app/logs/supervisord.log' >> /etc/supervisor/supervisord.conf && \
    echo 'pidfile=/run/supervisord.pid' >> /etc/supervisor/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisor/supervisord.conf && \
    echo '' >> /etc/supervisor/supervisord.conf && \
    echo '[unix_http_server]' >> /etc/supervisor/supervisord.conf && \
    echo 'file=/run/supervisor.sock' >> /etc/supervisor/supervisord.conf && \
    echo '' >> /etc/supervisor/supervisord.conf && \
    echo '[rpcinterface:supervisor]' >> /etc/supervisor/supervisord.conf && \
    echo 'supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface' >> /etc/supervisor/supervisord.conf && \
    echo '' >> /etc/supervisor/supervisord.conf && \
    echo '[supervisorctl]' >> /etc/supervisor/supervisord.conf && \
    echo 'serverurl=unix:///run/supervisor.sock' >> /etc/supervisor/supervisord.conf && \
    echo '' >> /etc/supervisor/supervisord.conf && \
    echo '[include]' >> /etc/supervisor/supervisord.conf && \
    echo 'files = /etc/supervisor/conf.d/*.conf' >> /etc/supervisor/supervisord.conf
