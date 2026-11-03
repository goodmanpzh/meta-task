#!/usr/bin/env python3
"""
Worker process for the data processing pipeline.
Pulls jobs from the queue, processes them, and writes results.

Each job is a JSON object with numerical data to be transformed.
The worker applies statistical computations and writes partial results.
"""

import socket
import json
import os
import sys
import time
import math
import signal
import hashlib

QUEUE_HOST = os.environ.get("QUEUE_HOST", "127.0.0.1")
DEQUEUE_PORT = int(os.environ.get("QUEUE_DEQUEUE_PORT", "9101"))
SOCKET_PATH = os.environ.get("QUEUE_SOCKET_PATH", "/run/pipeline/queue.sock")
USE_SOCKET = os.environ.get("WORKER_USE_SOCKET", "false").lower() == "true"
RESULTS_DIR = os.environ.get("WORKER_RESULTS_DIR", "/app/data/results")
LOG_DIR = os.environ.get("WORKER_LOG_DIR", "/app/logs")
WORKER_ID = os.environ.get("WORKER_ID", "worker-0")
MAX_RETRIES = 5
RETRY_DELAY = 2

running = True


def signal_handler(sig, frame):
    global running
    print(f"[{WORKER_ID}] Received signal {sig}, shutting down...", flush=True)
    running = False


def fetch_job_tcp():
    """Fetch a job from the queue via TCP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect((QUEUE_HOST, DEQUEUE_PORT))
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        response = data.decode("utf-8").strip()
        if response == "EMPTY":
            return None
        return json.loads(response)
    finally:
        sock.close()


def fetch_job_socket():
    """Fetch a job from the queue via Unix socket."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect(SOCKET_PATH)
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        response = data.decode("utf-8").strip()
        if response == "EMPTY":
            return None
        return json.loads(response)
    finally:
        sock.close()


def process_job(job):
    """
    Process a single job. Each job has:
    - id: unique identifier
    - dataset: list of numbers
    - operation: what to compute (stats, transform, hash)
    """
    job_id = job.get("id", "unknown")
    dataset = job.get("dataset", [])
    operation = job.get("operation", "stats")

    print(f"[{WORKER_ID}] Processing job {job_id} (op={operation}, data_points={len(dataset)})", flush=True)

    # BUG: File descriptor leak - opens log file each iteration without closing
    # This is intentional - the agent must find and fix this
    log_path = os.path.join(LOG_DIR, f"{WORKER_ID}-processing.log")
    log_file = open(log_path, "a")
    log_file.write(f"{time.time()} Processing job {job_id}\n")
    # NOTE: log_file is never closed! This leaks a file descriptor each call.

    result = {"id": job_id, "worker": WORKER_ID, "timestamp": time.time()}

    if operation == "stats":
        if not dataset:
            result["error"] = "empty dataset"
        else:
            n = len(dataset)
            mean = sum(dataset) / n
            variance = sum((x - mean) ** 2 for x in dataset) / n
            stddev = math.sqrt(variance)
            sorted_data = sorted(dataset)
            median = sorted_data[n // 2] if n % 2 == 1 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2.0
            result.update({
                "mean": round(mean, 6),
                "variance": round(variance, 6),
                "stddev": round(stddev, 6),
                "median": round(median, 6),
                "min": min(dataset),
                "max": max(dataset),
                "count": n
            })

    elif operation == "transform":
        if not dataset:
            result["error"] = "empty dataset"
        else:
            # Normalize to [0, 1] range and apply sigmoid
            min_val = min(dataset)
            max_val = max(dataset)
            if max_val == min_val:
                normalized = [0.5] * len(dataset)
            else:
                normalized = [(x - min_val) / (max_val - min_val) for x in dataset]
            sigmoid = [round(1.0 / (1.0 + math.exp(-6 * (x - 0.5))), 6) for x in normalized]
            result["transformed"] = sigmoid
            result["checksum"] = hashlib.md5(json.dumps(sigmoid).encode()).hexdigest()

    elif operation == "hash":
        data_str = json.dumps(dataset, sort_keys=True)
        result["sha256"] = hashlib.sha256(data_str.encode()).hexdigest()
        result["md5"] = hashlib.md5(data_str.encode()).hexdigest()
        result["data_size"] = len(data_str)

    return result


def write_result(result):
    """Write a processed result to the results directory."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    job_id = result.get("id", "unknown")
    output_path = os.path.join(RESULTS_DIR, f"result-{job_id}.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[{WORKER_ID}] Wrote result for job {job_id} to {output_path}", flush=True)


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"[{WORKER_ID}] Starting worker (PID {os.getpid()})", flush=True)
    print(f"[{WORKER_ID}] Queue: {QUEUE_HOST}:{DEQUEUE_PORT} (socket={USE_SOCKET})", flush=True)

    # Write PID file
    os.makedirs("/run/pipeline", exist_ok=True)
    with open(f"/run/pipeline/{WORKER_ID}.pid", "w") as f:
        f.write(str(os.getpid()))

    idle_count = 0
    jobs_done = 0

    while running:
        try:
            if USE_SOCKET:
                job = fetch_job_socket()
            else:
                job = fetch_job_tcp()

            if job is None:
                idle_count += 1
                if idle_count > 30:
                    print(f"[{WORKER_ID}] No more jobs after processing {jobs_done} jobs. Exiting.", flush=True)
                    break
                time.sleep(1)
                continue

            idle_count = 0
            result = process_job(job)
            write_result(result)
            jobs_done += 1

        except ConnectionRefusedError:
            print(f"[{WORKER_ID}] Queue not available, retrying in {RETRY_DELAY}s...", flush=True)
            time.sleep(RETRY_DELAY)
        except PermissionError as e:
            print(f"[{WORKER_ID}] Permission error: {e}", flush=True)
            time.sleep(RETRY_DELAY)
        except OSError as e:
            if e.errno == 24:  # Too many open files
                print(f"[{WORKER_ID}] FATAL: Too many open files (fd leak?). Exiting.", flush=True)
                sys.exit(1)
            print(f"[{WORKER_ID}] OS error: {e}", flush=True)
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"[{WORKER_ID}] Unexpected error: {e}", flush=True)
            time.sleep(RETRY_DELAY)

    print(f"[{WORKER_ID}] Worker finished. Processed {jobs_done} jobs total.", flush=True)


if __name__ == "__main__":
    main()
