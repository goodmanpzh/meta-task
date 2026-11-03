#!/usr/bin/env python3
"""
Aggregator process for the data processing pipeline.
Watches the results directory for completed job results,
aggregates them, and produces the final output file.
"""

import json
import os
import sys
import time
import signal
import hashlib

RESULTS_DIR = os.environ.get("WORKER_RESULTS_DIR", "/app/data/results")
OUTPUT_FILE = os.environ.get("AGGREGATOR_OUTPUT", "/app/output/results.json")
STATS_PORT = int(os.environ.get("QUEUE_STATS_PORT", "9102"))
QUEUE_HOST = os.environ.get("QUEUE_HOST", "127.0.0.1")
EXPECTED_JOBS = int(os.environ.get("EXPECTED_JOBS", "20"))
LOG_DIR = os.environ.get("AGGREGATOR_LOG_DIR", "/app/logs")

running = True


def signal_handler(sig, frame):
    global running
    print(f"[aggregator] Received signal {sig}, shutting down...", flush=True)
    running = False


def collect_results():
    """Collect all result files from the results directory."""
    results = []
    if not os.path.isdir(RESULTS_DIR):
        return results

    for fname in sorted(os.listdir(RESULTS_DIR)):
        if fname.startswith("result-") and fname.endswith(".json"):
            fpath = os.path.join(RESULTS_DIR, fname)
            try:
                with open(fpath, "r") as f:
                    result = json.load(f)
                results.append(result)
            except Exception as e:
                print(f"[aggregator] Error reading {fname}: {e}", flush=True)

    return results


def aggregate(results):
    """Aggregate all results into a final summary."""
    summary = {
        "pipeline_version": "1.0",
        "total_jobs": len(results),
        "completed_at": time.time(),
        "jobs": {},
        "stats_summary": {},
        "transform_summary": {},
        "hash_summary": {}
    }

    stats_means = []
    stats_stddevs = []
    transform_checksums = []
    hash_values = []

    for r in results:
        job_id = r.get("id", "unknown")
        summary["jobs"][job_id] = r

        if "mean" in r:
            stats_means.append(r["mean"])
            stats_stddevs.append(r["stddev"])
        if "checksum" in r:
            transform_checksums.append(r["checksum"])
        if "sha256" in r:
            hash_values.append(r["sha256"])

    if stats_means:
        summary["stats_summary"] = {
            "num_stats_jobs": len(stats_means),
            "grand_mean": round(sum(stats_means) / len(stats_means), 6),
            "avg_stddev": round(sum(stats_stddevs) / len(stats_stddevs), 6)
        }

    if transform_checksums:
        combined = "".join(sorted(transform_checksums))
        summary["transform_summary"] = {
            "num_transform_jobs": len(transform_checksums),
            "combined_checksum": hashlib.md5(combined.encode()).hexdigest()
        }

    if hash_values:
        summary["hash_summary"] = {
            "num_hash_jobs": len(hash_values),
            "hashes": hash_values
        }

    # Compute overall integrity hash
    content = json.dumps(summary["jobs"], sort_keys=True)
    summary["integrity_hash"] = hashlib.sha256(content.encode()).hexdigest()

    return summary


def write_output(summary):
    """Write the aggregated output to the final output file."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[aggregator] Wrote final output to {OUTPUT_FILE}", flush=True)


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    os.makedirs(LOG_DIR, exist_ok=True)

    print(f"[aggregator] Starting aggregator (PID {os.getpid()})", flush=True)
    print(f"[aggregator] Watching {RESULTS_DIR} for {EXPECTED_JOBS} results", flush=True)
    print(f"[aggregator] Output will be written to {OUTPUT_FILE}", flush=True)

    # Write PID file
    os.makedirs("/run/pipeline", exist_ok=True)
    with open("/run/pipeline/aggregator.pid", "w") as f:
        f.write(str(os.getpid()))

    wait_count = 0
    max_wait = 120  # seconds

    while running and wait_count < max_wait:
        results = collect_results()
        current = len(results)

        if current >= EXPECTED_JOBS:
            print(f"[aggregator] All {EXPECTED_JOBS} results collected. Aggregating...", flush=True)
            summary = aggregate(results)
            write_output(summary)
            print(f"[aggregator] Pipeline complete! {current} jobs aggregated.", flush=True)
            return

        if wait_count % 10 == 0:
            print(f"[aggregator] Waiting for results... ({current}/{EXPECTED_JOBS})", flush=True)

        time.sleep(1)
        wait_count += 1

    # Timeout - write whatever we have
    results = collect_results()
    if results:
        print(f"[aggregator] Timeout reached. Aggregating {len(results)} partial results.", flush=True)
        summary = aggregate(results)
        summary["partial"] = True
        summary["expected_jobs"] = EXPECTED_JOBS
        write_output(summary)
    else:
        print(f"[aggregator] Timeout reached. No results found in {RESULTS_DIR}.", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
