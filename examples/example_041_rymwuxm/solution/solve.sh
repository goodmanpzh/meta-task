#!/bin/bash
set -e

echo "=== Diagnosing and fixing the broken data processing pipeline ==="

# Stop supervisord if it's already running
supervisorctl shutdown 2>/dev/null || true
sleep 1
# Kill any lingering processes
pkill -f supervisord 2>/dev/null || true
pkill -f queue_server 2>/dev/null || true
pkill -f worker.py 2>/dev/null || true
pkill -f aggregator.py 2>/dev/null || true
sleep 1

# Clean up old state
rm -rf /app/data/results/*
rm -f /app/output/results.json
rm -f /app/logs/*.log
rm -f /run/pipeline/*.pid
rm -f /run/pipeline/queue.sock
rm -f /run/supervisor.sock
rm -f /run/supervisord.pid

# Ensure directories exist
mkdir -p /app/data/results /app/logs /app/output /run/pipeline

# ============================================================
# FIX 1: Fix the worker.py file descriptor leak
# The worker opens a log file in process_job() but never closes it.
# With a low ulimit, this causes "Too many open files" after ~60 jobs.
# Fix: close the file handle after writing.
# ============================================================
echo "Fixing worker.py file descriptor leak..."
sed -i 's/log_file.write(f"{time.time()} Processing job {job_id}\\n")/log_file.write(f"{time.time()} Processing job {job_id}\\n")\n    log_file.close()/' /app/worker.py

# ============================================================
# FIX 2: Fix the queue_server.py socket permissions
# The queue server creates a Unix socket with mode 0600 (owner only).
# The worker needs to connect to it. Change to 0666 so any user can connect.
# ============================================================
echo "Fixing queue_server.py socket permissions..."
sed -i 's/os.chmod(SOCKET_PATH, 0o600)/os.chmod(SOCKET_PATH, 0o666)/' /app/queue_server.py

# ============================================================
# FIX 3: Fix the supervisord configuration (multiple bugs)
# ============================================================
echo "Fixing supervisord configuration..."

cat > /etc/supervisor/conf.d/pipeline.conf << 'CONF'
; === Queue Server ===
[program:queue]
command=python3 /app/queue_server.py
directory=/app
autostart=true
autorestart=true
stdout_logfile=/app/logs/queue-stdout.log
stderr_logfile=/app/logs/queue-stderr.log
environment=QUEUE_ENQUEUE_PORT="9100",QUEUE_DEQUEUE_PORT="9101",QUEUE_STATS_PORT="9102",QUEUE_BIND_ADDR="127.0.0.1",QUEUE_DATA_DIR="/app/data/queue",QUEUE_SOCKET_PATH="/run/pipeline/queue.sock"
priority=100

; === Worker ===
[program:worker]
command=python3 /app/worker.py
directory=/app
autostart=true
autorestart=true
stdout_logfile=/app/logs/worker-stdout.log
stderr_logfile=/app/logs/worker-stderr.log
environment=QUEUE_HOST="127.0.0.1",QUEUE_DEQUEUE_PORT="9101",WORKER_USE_SOCKET="false",QUEUE_SOCKET_PATH="/run/pipeline/queue.sock",WORKER_RESULTS_DIR="/app/data/results",WORKER_LOG_DIR="/app/logs",WORKER_ID="worker-0"
priority=200
startsecs=3

; === Aggregator ===
[program:aggregator]
command=python3 /app/aggregator.py
directory=/app
autostart=true
autorestart=false
stdout_logfile=/app/logs/aggregator-stdout.log
stderr_logfile=/app/logs/aggregator-stderr.log
environment=WORKER_RESULTS_DIR="/app/data/results",AGGREGATOR_OUTPUT="/app/output/results.json",QUEUE_STATS_PORT="9102",QUEUE_HOST="127.0.0.1",EXPECTED_JOBS="20",AGGREGATOR_LOG_DIR="/app/logs"
priority=300
startsecs=3
startretries=3
CONF

# Summary of config fixes:
# FIX 3a: queue command path: /app/services/queue_server.py -> /app/queue_server.py
# FIX 3b: QUEUE_BIND_ADDR: 10.0.0.1 -> 127.0.0.1
# FIX 3c: worker user: removed "user=pipeline" (user doesn't exist)
# FIX 3d: QUEUE_DEQUEUE_PORT for worker: 9201 -> 9101
# FIX 3e: WORKER_USE_SOCKET: true -> false (avoid socket permission complexity, use TCP)
# FIX 3f: aggregator WORKER_RESULTS_DIR: /app/results -> /app/data/results
# FIX 3g: AGGREGATOR_OUTPUT: /tmp/pipeline-out/results.json -> /app/output/results.json
# FIX 3h: EXPECTED_JOBS: 25 -> 20

# ============================================================
# FIX 4: Raise file descriptor limits
# The limits.conf settings are too restrictive (64 soft, 128 hard).
# Raise them so the worker can operate even if some fd leak remains.
# ============================================================
echo "Fixing file descriptor limits..."
ulimit -n 4096 2>/dev/null || true

# ============================================================
# Start the pipeline
# ============================================================
echo "Starting supervisord..."
supervisord -c /etc/supervisor/supervisord.conf &
sleep 2

echo "Checking service status..."
supervisorctl status || true

# Wait for the pipeline to complete
echo "Waiting for pipeline to process all jobs..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if [ -f /app/output/results.json ]; then
        # Check if it's a complete (non-partial) result
        if python3 -c "
import json
with open('/app/output/results.json') as f:
    data = json.load(f)
if data.get('total_jobs', 0) >= 20 and not data.get('partial', False):
    exit(0)
else:
    exit(1)
" 2>/dev/null; then
            echo "Pipeline completed successfully!"
            break
        fi
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "Warning: Pipeline did not complete within ${MAX_WAIT} seconds"
    echo "Checking logs for errors..."
    echo "--- Queue logs ---"
    cat /app/logs/queue-stderr.log 2>/dev/null || echo "(no queue stderr log)"
    echo "--- Worker logs ---"
    cat /app/logs/worker-stderr.log 2>/dev/null || echo "(no worker stderr log)"
    echo "--- Aggregator logs ---"
    cat /app/logs/aggregator-stderr.log 2>/dev/null || echo "(no aggregator stderr log)"
fi

echo "=== Pipeline fix complete ==="
echo "Output file: /app/output/results.json"
if [ -f /app/output/results.json ]; then
    python3 -c "
import json
with open('/app/output/results.json') as f:
    data = json.load(f)
print(f'Total jobs: {data.get(\"total_jobs\", \"N/A\")}')
print(f'Partial: {data.get(\"partial\", False)}')
print(f'Integrity hash: {data.get(\"integrity_hash\", \"N/A\")[:16]}...')
"
fi
