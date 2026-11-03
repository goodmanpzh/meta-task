"""
Benchmark script for KNN optimization task.
Compares the optimized find_knn against the baseline.
"""

import time
import numpy as np
import sys
import os

sys.path.insert(0, "/app")

from knn_baseline import find_knn_baseline
from knn import find_knn


def generate_data(n_queries, n_refs, n_dims, seed=42):
    rng = np.random.RandomState(seed)
    queries = rng.randn(n_queries, n_dims).astype(np.float64)
    refs = rng.randn(n_refs, n_dims).astype(np.float64)
    return queries, refs


def check_correctness(queries, refs, k, label=""):
    """Check that optimized matches baseline exactly."""
    print(f"  Checking correctness ({label})...")
    base_idx, base_dist = find_knn_baseline(queries, refs, k)
    opt_idx, opt_dist = find_knn(queries, refs, k)

    idx_match = np.array_equal(base_idx, opt_idx)
    dist_match = np.allclose(base_dist, opt_dist, rtol=1e-6, atol=1e-12)

    if idx_match and dist_match:
        print(f"  PASS: indices and distances match")
    else:
        if not idx_match:
            mismatches = np.where(base_idx != opt_idx)
            n_wrong = len(mismatches[0])
            print(f"  FAIL: {n_wrong} index mismatches")
            if n_wrong > 0:
                i = mismatches[0][0]
                print(f"    First mismatch at query {i}: expected {base_idx[i]}, got {opt_idx[i]}")
        if not dist_match:
            print(f"  FAIL: distances don't match within tolerance")
            diff = np.abs(base_dist - opt_dist)
            print(f"    Max absolute diff: {diff.max():.2e}")
    return idx_match and dist_match


def benchmark_speed(queries, refs, k, label=""):
    """Benchmark optimized vs baseline speed."""
    print(f"\n  Benchmarking ({label}, N={queries.shape[0]}, M={refs.shape[0]}, K={k})...")

    # Time baseline
    t0 = time.perf_counter()
    find_knn_baseline(queries, refs, k)
    t_base = time.perf_counter() - t0
    print(f"  Baseline: {t_base:.3f}s")

    # Time optimized
    t0 = time.perf_counter()
    find_knn(queries, refs, k)
    t_opt = time.perf_counter() - t0
    print(f"  Optimized: {t_opt:.3f}s")

    speedup = t_base / t_opt if t_opt > 0 else float("inf")
    print(f"  Speedup: {speedup:.1f}x")
    return speedup


def main():
    print("=" * 60)
    print("KNN Benchmark")
    print("=" * 60)

    # Small correctness check
    print("\n--- Small Input Correctness ---")
    q, r = generate_data(50, 200, 3, seed=100)
    ok = check_correctness(q, r, 5, "small")
    if not ok:
        print("\nFAILED correctness check on small input. Fix correctness first!")
        return

    # Medium correctness + speed
    print("\n--- Medium Input ---")
    q, r = generate_data(200, 2000, 3, seed=200)
    ok = check_correctness(q, r, 10, "medium")
    if ok:
        benchmark_speed(q, r, 10, "medium")

    # Edge case: duplicates
    print("\n--- Duplicate Points ---")
    rng = np.random.RandomState(300)
    q = rng.randn(20, 3)
    r = np.vstack([rng.randn(50, 3)] * 3)  # tripled reference set
    ok = check_correctness(q, r, 8, "duplicates")

    print("\n--- Performance Target ---")
    print("  For the final test, you need 10x speedup on:")
    print("  N=10000, M=50000, D=3, K=10")
    print("  (this takes too long to run the baseline here)")
    print("  Use the test suite for the full performance check.")

    print("\n" + "=" * 60)
    print("Benchmark complete!")


if __name__ == "__main__":
    main()
