#!/usr/bin/env python3
"""
Simple TCP-based job queue server for the data processing pipeline.
Accepts jobs on one port (enqueue) and serves them on another (dequeue).
Also provides a stats endpoint.
"""

import socket
import threading
import json
import os
import sys
import time
import signal

ENQUEUE_PORT = int(os.environ.get("QUEUE_ENQUEUE_PORT", "9100"))
DEQUEUE_PORT = int(os.environ.get("QUEUE_DEQUEUE_PORT", "9101"))
STATS_PORT = int(os.environ.get("QUEUE_STATS_PORT", "9102"))
BIND_ADDR = os.environ.get("QUEUE_BIND_ADDR", "127.0.0.1")
DATA_DIR = os.environ.get("QUEUE_DATA_DIR", "/app/data/queue")
SOCKET_PATH = os.environ.get("QUEUE_SOCKET_PATH", "/run/pipeline/queue.sock")

job_queue = []
processed_count = 0
lock = threading.Lock()
running = True


def load_initial_jobs():
    """Load job files from the data directory into the queue."""
    global job_queue
    if not os.path.isdir(DATA_DIR):
        print(f"[queue] Warning: data directory {DATA_DIR} does not exist", flush=True)
        return
    files = sorted(os.listdir(DATA_DIR))
    for fname in files:
        fpath = os.path.join(DATA_DIR, fname)
        if fname.endswith(".json") and os.path.isfile(fpath):
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
                with lock:
                    job_queue.append(data)
                print(f"[queue] Loaded job from {fname}", flush=True)
            except Exception as e:
                print(f"[queue] Error loading {fname}: {e}", flush=True)
    print(f"[queue] Loaded {len(job_queue)} initial jobs", flush=True)


def handle_enqueue(conn):
    """Handle an enqueue connection - receive a job and add to queue."""
    global job_queue
    try:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        job = json.loads(data.decode("utf-8"))
        with lock:
            job_queue.append(job)
        conn.sendall(b"OK\n")
    except Exception as e:
        print(f"[queue] Enqueue error: {e}", flush=True)
        try:
            conn.sendall(f"ERROR: {e}\n".encode())
        except:
            pass
    finally:
        conn.close()


def handle_dequeue(conn):
    """Handle a dequeue connection - send a job from queue."""
    global job_queue
    try:
        with lock:
            if job_queue:
                job = job_queue.pop(0)
                conn.sendall(json.dumps(job).encode("utf-8"))
            else:
                conn.sendall(b"EMPTY\n")
    except Exception as e:
        print(f"[queue] Dequeue error: {e}", flush=True)
    finally:
        conn.close()


def handle_stats(conn):
    """Handle a stats connection - return queue statistics."""
    global processed_count
    try:
        with lock:
            stats = {
                "pending": len(job_queue),
                "processed": processed_count,
                "status": "running"
            }
        conn.sendall(json.dumps(stats).encode("utf-8"))
    except Exception as e:
        print(f"[queue] Stats error: {e}", flush=True)
    finally:
        conn.close()


def run_tcp_server(port, handler, name):
    """Run a TCP server on the given port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(2.0)
    try:
        sock.bind((BIND_ADDR, port))
    except OSError as e:
        print(f"[queue] Failed to bind {name} on {BIND_ADDR}:{port}: {e}", flush=True)
        sys.exit(1)
    sock.listen(5)
    print(f"[queue] {name} listening on {BIND_ADDR}:{port}", flush=True)

    while running:
        try:
            conn, addr = sock.accept()
            t = threading.Thread(target=handler, args=(conn,), daemon=True)
            t.start()
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"[queue] {name} accept error: {e}", flush=True)
    sock.close()


def run_unix_socket_server():
    """Run a Unix socket server for local IPC."""
    os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(SOCKET_PATH)
    # BUG: Socket permissions are too restrictive - only owner can connect
    os.chmod(SOCKET_PATH, 0o600)
    sock.listen(5)
    sock.settimeout(2.0)
    print(f"[queue] Unix socket listening on {SOCKET_PATH}", flush=True)

    while running:
        try:
            conn, _ = sock.accept()
            # Unix socket dequeue handler
            handle_dequeue(conn)
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"[queue] Unix socket error: {e}", flush=True)
    sock.close()


def signal_handler(sig, frame):
    global running
    print("[queue] Shutting down...", flush=True)
    running = False


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print(f"[queue] Starting queue server (PID {os.getpid()})", flush=True)
    print(f"[queue] Config: BIND={BIND_ADDR} ENQUEUE={ENQUEUE_PORT} DEQUEUE={DEQUEUE_PORT} STATS={STATS_PORT}", flush=True)

    load_initial_jobs()

    threads = [
        threading.Thread(target=run_tcp_server, args=(ENQUEUE_PORT, handle_enqueue, "enqueue"), daemon=True),
        threading.Thread(target=run_tcp_server, args=(DEQUEUE_PORT, handle_dequeue, "dequeue"), daemon=True),
        threading.Thread(target=run_tcp_server, args=(STATS_PORT, handle_stats, "stats"), daemon=True),
        threading.Thread(target=run_unix_socket_server, daemon=True),
    ]

    for t in threads:
        t.start()

    # Write PID file
    os.makedirs("/run/pipeline", exist_ok=True)
    with open("/run/pipeline/queue.pid", "w") as f:
        f.write(str(os.getpid()))

    while running:
        time.sleep(1)

    print("[queue] Server stopped.", flush=True)


if __name__ == "__main__":
    main()
