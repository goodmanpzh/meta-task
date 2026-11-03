#!/usr/bin/env python3
"""
Generate realistic Prometheus metric snapshots with cardinality explosions.
This script creates a series of .prom files simulating scrape snapshots.
"""
import os
import random
import hashlib

random.seed(42)

SNAPSHOTS_DIR = "/app/data/snapshots"
NUM_SNAPSHOTS = 12

# --- Stable metrics (no explosion) ---
STABLE_SERVICES = ["auth", "gateway", "payments", "inventory"]
STABLE_METHODS = ["GET", "POST", "PUT", "DELETE"]
STABLE_ENDPOINTS = ["/api/v1/users", "/api/v1/orders", "/api/v1/products", "/api/v1/health"]
STABLE_STATUS_CODES = ["200", "201", "400", "404", "500"]

# --- Explosion metric 1: http_request_duration_seconds (histogram) ---
# Label "client_id" will explode with UUID-like values
# Starts with 5 client IDs, grows to 500+

# --- Explosion metric 2: grpc_server_handled_total (counter) ---
# Label "peer_address" will explode with IP:port combinations
# Starts with 8 peers, grows to 400+

# --- Explosion metric 3: app_cache_operations_total (counter) ---
# Label "cache_key_prefix" will explode with dynamic key patterns
# Starts with 10 prefixes, grows to 300+

HISTOGRAM_BUCKETS = ["0.005", "0.01", "0.025", "0.05", "0.1", "0.25", "0.5", "1", "2.5", "5", "10", "+Inf"]
SUMMARY_QUANTILES = ["0.5", "0.9", "0.95", "0.99"]

def gen_uuid_like(seed_val):
    """Generate a UUID-like string from a seed."""
    h = hashlib.md5(str(seed_val).encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

def gen_ip_port(seed_val):
    """Generate an IP:port string."""
    random.seed(seed_val + 99999)
    return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}:{random.randint(10000,65535)}"

def gen_cache_key(seed_val):
    """Generate cache key prefix with special characters."""
    random.seed(seed_val + 77777)
    namespaces = ["user", "session", "product", "order", "cart", "search", "config"]
    ns = namespaces[seed_val % len(namespaces)]
    h = hashlib.md5(str(seed_val).encode()).hexdigest()[:12]
    # Include special chars: colons, slashes, dots
    patterns = [
        f"{ns}:v2/{h}.data",
        f"{ns}/cache:{h}.tmp",
        f"{ns}.{h}:latest/rev",
        f"ns:{ns}/{h}.v1.snapshot",
    ]
    return patterns[seed_val % len(patterns)]

def get_explosion_client_ids(snapshot_idx):
    """Return client IDs for this snapshot. Explodes starting at snapshot 4."""
    base_ids = [gen_uuid_like(i) for i in range(5)]
    if snapshot_idx <= 3:
        return base_ids
    elif snapshot_idx <= 6:
        extra = [gen_uuid_like(100 + i) for i in range((snapshot_idx - 3) * 40)]
        return base_ids + extra
    else:
        extra = [gen_uuid_like(100 + i) for i in range(120 + (snapshot_idx - 6) * 100)]
        return base_ids + extra

def get_explosion_peer_addresses(snapshot_idx):
    """Return peer addresses. Explodes starting at snapshot 5."""
    base_peers = [gen_ip_port(i) for i in range(8)]
    if snapshot_idx <= 4:
        return base_peers
    elif snapshot_idx <= 7:
        extra = [gen_ip_port(200 + i) for i in range((snapshot_idx - 4) * 35)]
        return base_peers + extra
    else:
        extra = [gen_ip_port(200 + i) for i in range(105 + (snapshot_idx - 7) * 80)]
        return base_peers + extra

def get_explosion_cache_keys(snapshot_idx):
    """Return cache key prefixes. Explodes starting at snapshot 3."""
    base_keys = [gen_cache_key(i) for i in range(10)]
    if snapshot_idx <= 2:
        return base_keys
    elif snapshot_idx <= 5:
        extra = [gen_cache_key(300 + i) for i in range((snapshot_idx - 2) * 30)]
        return base_keys + extra
    else:
        extra = [gen_cache_key(300 + i) for i in range(90 + (snapshot_idx - 5) * 55)]
        return base_keys + extra

def write_snapshot(snapshot_idx, filepath, skip_metrics=None):
    """Write a single Prometheus exposition format snapshot."""
    lines = []
    if skip_metrics is None:
        skip_metrics = set()

    # ========== STABLE METRICS ==========

    # 1. process_cpu_seconds_total (counter) - per service
    if "process_cpu_seconds_total" not in skip_metrics:
        lines.append("# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.")
        lines.append("# TYPE process_cpu_seconds_total counter")
        for svc in STABLE_SERVICES:
            val = 1000 + snapshot_idx * 50 + hash(svc) % 100
            lines.append(f'process_cpu_seconds_total{{service="{svc}"}} {val}')

    # 2. process_resident_memory_bytes (gauge) - per service
    if "process_resident_memory_bytes" not in skip_metrics:
        lines.append("# HELP process_resident_memory_bytes Resident memory size in bytes.")
        lines.append("# TYPE process_resident_memory_bytes gauge")
        for svc in STABLE_SERVICES:
            val = 50000000 + random.randint(-5000000, 5000000)
            lines.append(f'process_resident_memory_bytes{{service="{svc}"}} {val}')

    # 3. http_requests_total (counter) - stable, per service/method/status
    if "http_requests_total" not in skip_metrics:
        lines.append("# HELP http_requests_total Total HTTP requests.")
        lines.append("# TYPE http_requests_total counter")
        for svc in STABLE_SERVICES:
            for method in STABLE_METHODS[:2]:  # Just GET, POST
                for status in STABLE_STATUS_CODES[:3]:  # 200, 201, 400
                    val = 5000 + snapshot_idx * 200 + hash(svc + method + status) % 500
                    lines.append(f'http_requests_total{{service="{svc}",method="{method}",status="{status}"}} {val}')

    # 4. up (gauge) - per service
    if "up" not in skip_metrics:
        lines.append("# HELP up Whether the target is up.")
        lines.append("# TYPE up gauge")
        for svc in STABLE_SERVICES:
            lines.append(f'up{{service="{svc}"}} 1')

    # 5. go_goroutines (gauge) - per service
    if "go_goroutines" not in skip_metrics:
        lines.append("# HELP go_goroutines Number of goroutines.")
        lines.append("# TYPE go_goroutines gauge")
        for svc in STABLE_SERVICES:
            val = 30 + random.randint(-5, 20)
            lines.append(f'go_goroutines{{service="{svc}"}} {val}')

    # 6. node_filesystem_avail_bytes (gauge) - per mountpoint
    if "node_filesystem_avail_bytes" not in skip_metrics:
        lines.append("# HELP node_filesystem_avail_bytes Available filesystem bytes.")
        lines.append("# TYPE node_filesystem_avail_bytes gauge")
        mounts = ["/", "/var", "/tmp", "/data"]
        for mount in mounts:
            val = 100000000000 - snapshot_idx * 1000000000 + random.randint(-500000000, 500000000)
            lines.append(f'node_filesystem_avail_bytes{{mountpoint="{mount}",fstype="ext4"}} {val}')

    # ========== EXPLOSION METRIC 1: http_request_duration_seconds (histogram) ==========
    if "http_request_duration_seconds" not in skip_metrics:
        lines.append("# HELP http_request_duration_seconds Duration of HTTP requests in seconds.")
        lines.append("# TYPE http_request_duration_seconds histogram")
        client_ids = get_explosion_client_ids(snapshot_idx)
        for cid in client_ids:
            for endpoint in ["/api/v1/users", "/api/v1/orders"]:
                cumulative = 0
                for bucket in HISTOGRAM_BUCKETS:
                    cumulative += random.randint(0, 100)
                    lines.append(f'http_request_duration_seconds_bucket{{client_id="{cid}",endpoint="{endpoint}",le="{bucket}"}} {cumulative}')
                lines.append(f'http_request_duration_seconds_count{{client_id="{cid}",endpoint="{endpoint}"}} {cumulative}')
                lines.append(f'http_request_duration_seconds_sum{{client_id="{cid}",endpoint="{endpoint}"}} {cumulative * 0.05:.3f}')

    # ========== EXPLOSION METRIC 2: grpc_server_handled_total (counter) ==========
    if "grpc_server_handled_total" not in skip_metrics:
        lines.append("# HELP grpc_server_handled_total Total number of RPCs handled on the server.")
        lines.append("# TYPE grpc_server_handled_total counter")
        peers = get_explosion_peer_addresses(snapshot_idx)
        for peer in peers:
            for grpc_method in ["GetUser", "CreateOrder", "UpdateInventory"]:
                for code in ["OK", "Internal", "NotFound"]:
                    val = 100 + snapshot_idx * 20 + hash(peer + grpc_method) % 200
                    lines.append(f'grpc_server_handled_total{{peer_address="{peer}",grpc_method="{grpc_method}",grpc_code="{code}"}} {val}')

    # ========== EXPLOSION METRIC 3: app_cache_operations_total (counter) ==========
    if "app_cache_operations_total" not in skip_metrics:
        lines.append("# HELP app_cache_operations_total Total cache operations.")
        lines.append("# TYPE app_cache_operations_total counter")
        cache_keys = get_explosion_cache_keys(snapshot_idx)
        for key in cache_keys:
            for op in ["get", "set", "delete"]:
                val = 500 + snapshot_idx * 30 + hash(key + op) % 300
                lines.append(f'app_cache_operations_total{{cache_key_prefix="{key}",operation="{op}"}} {val}')

    # 7. A summary metric (stable) - request_latency_seconds
    if "request_latency_seconds" not in skip_metrics:
        lines.append("# HELP request_latency_seconds Request latency distribution.")
        lines.append("# TYPE request_latency_seconds summary")
        for svc in STABLE_SERVICES:
            for q in SUMMARY_QUANTILES:
                val = float(q) * 0.5 + random.random() * 0.1
                lines.append(f'request_latency_seconds{{service="{svc}",quantile="{q}"}} {val:.6f}')
            lines.append(f'request_latency_seconds_count{{service="{svc}"}} {1000 + snapshot_idx * 100}')
            lines.append(f'request_latency_seconds_sum{{service="{svc}"}} {500 + snapshot_idx * 50 + random.random() * 10:.3f}')

    # 8. Another stable counter: database_queries_total
    if "database_queries_total" not in skip_metrics:
        lines.append("# HELP database_queries_total Total database queries executed.")
        lines.append("# TYPE database_queries_total counter")
        for svc in ["auth", "payments", "inventory"]:
            for query_type in ["select", "insert", "update"]:
                val = 10000 + snapshot_idx * 500 + hash(svc + query_type) % 1000
                lines.append(f'database_queries_total{{service="{svc}",query_type="{query_type}"}} {val}')

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines) + '\n')

def main():
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

    # Define which snapshots have "scrape failures" (missing specific metrics)
    # Snapshot 6: http_request_duration_seconds missing (scrape failure)
    # Snapshot 9: grpc_server_handled_total missing (scrape failure)
    scrape_failures = {
        6: {"http_request_duration_seconds"},
        9: {"grpc_server_handled_total"},
    }

    for i in range(NUM_SNAPSHOTS):
        filepath = os.path.join(SNAPSHOTS_DIR, f"t_{i}.prom")
        skip = scrape_failures.get(i, set())
        write_snapshot(i, filepath, skip_metrics=skip)

        # Count lines for verification
        with open(filepath) as f:
            line_count = sum(1 for l in f if l.strip())
        print(f"Snapshot t_{i}.prom: {line_count} lines, skipped: {skip or 'none'}")

    print(f"\nGenerated {NUM_SNAPSHOTS} snapshots in {SNAPSHOTS_DIR}")

if __name__ == "__main__":
    main()
