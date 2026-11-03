#!/usr/bin/env python3
"""
Generate job data files for the pipeline queue.
This script creates JSON job files that will be loaded by the queue server.
"""

import json
import os
import random
import math

DATA_DIR = "/app/data/queue"
NUM_JOBS = 20

random.seed(42)  # Deterministic for reproducibility


def generate_stats_job(job_id):
    """Generate a statistics computation job."""
    n = random.randint(50, 200)
    # Generate data from different distributions
    dist_type = random.choice(["normal", "uniform", "bimodal"])
    if dist_type == "normal":
        data = [round(random.gauss(100, 25), 4) for _ in range(n)]
    elif dist_type == "uniform":
        low, high = random.uniform(0, 50), random.uniform(50, 200)
        data = [round(random.uniform(low, high), 4) for _ in range(n)]
    else:  # bimodal
        data = []
        for _ in range(n):
            if random.random() < 0.5:
                data.append(round(random.gauss(50, 10), 4))
            else:
                data.append(round(random.gauss(150, 10), 4))

    return {
        "id": f"stats-{job_id:03d}",
        "operation": "stats",
        "dataset": data,
        "distribution": dist_type
    }


def generate_transform_job(job_id):
    """Generate a data transformation job."""
    n = random.randint(30, 100)
    data = [round(random.uniform(-100, 100), 4) for _ in range(n)]
    return {
        "id": f"transform-{job_id:03d}",
        "operation": "transform",
        "dataset": data
    }


def generate_hash_job(job_id):
    """Generate a hash computation job."""
    n = random.randint(10, 50)
    data = [round(random.uniform(0, 1000), 4) for _ in range(n)]
    return {
        "id": f"hash-{job_id:03d}",
        "operation": "hash",
        "dataset": data
    }


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    generators = [generate_stats_job, generate_transform_job, generate_hash_job]
    weights = [0.4, 0.35, 0.25]  # More stats jobs

    for i in range(NUM_JOBS):
        gen = random.choices(generators, weights=weights, k=1)[0]
        job = gen(i)
        fname = f"job-{i:03d}.json"
        fpath = os.path.join(DATA_DIR, fname)
        with open(fpath, "w") as f:
            json.dump(job, f, indent=2)
        print(f"Generated {fname}: {job['operation']} ({len(job['dataset'])} data points)")

    print(f"\nGenerated {NUM_JOBS} jobs in {DATA_DIR}")


if __name__ == "__main__":
    main()
