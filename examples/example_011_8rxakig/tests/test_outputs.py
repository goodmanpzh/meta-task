"""
Test suite for KNN optimization task.

Verifies:
1. Correctness on small inputs (exact index match against reference baseline)
2. Correctness on medium inputs
3. Edge case: duplicate reference points (tie-breaking by index)
4. Edge case: query point coincident with reference point (zero distance)
5. Edge case: large coordinate values (numerical stability)
6. Performance: 10x speedup on large inputs
7. Output shape and dtype correctness
"""

import os
import sys
import time
import math
import numpy as np
import pytest

# Capture references before importing candidate code to prevent monkeypatching
_np_random_RandomState = np.random.RandomState
_time_perf_counter = time.perf_counter
_math_sqrt = math.sqrt

os.chdir("/app")
sys.path.insert(0, "/app")


# ── Protected baseline (inline, tamper-proof) ──────────────────────────────

def _baseline_knn(query_points, reference_points, k):
    """Reference KNN — pure Python, identical to knn_baseline.py."""
    n = query_points.shape[0]
    m = reference_points.shape[0]
    d = query_points.shape[1]
    all_indices = []
    all_distances = []
    for i in range(n):
        dists_with_idx = []
        for j in range(m):
            dist_sq = 0.0
            for dim in range(d):
                diff = float(query_points[i, dim]) - float(reference_points[j, dim])
                dist_sq += diff * diff
            dist = _math_sqrt(dist_sq)
            dists_with_idx.append((dist, j))
        dists_with_idx.sort()
        top_k_indices = [idx for _, idx in dists_with_idx[:k]]
        top_k_dists = [dist for dist, _ in dists_with_idx[:k]]
        all_indices.append(top_k_indices)
        all_distances.append(top_k_dists)
    return np.array(all_indices, dtype=np.int64), np.array(all_distances, dtype=np.float64)


# ── Import candidate ────────────────────────────────────────────────────────

from knn import find_knn  # noqa: E402


# ── Helper ──────────────────────────────────────────────────────────────────

def _generate(n_queries, n_refs, n_dims, seed):
    rng = _np_random_RandomState(seed)
    q = rng.randn(n_queries, n_dims).astype(np.float64)
    r = rng.randn(n_refs, n_dims).astype(np.float64)
    return q, r


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1 — Output shape and dtype
# ═══════════════════════════════════════════════════════════════════════════

def test_output_shape_and_dtype():
    """Return arrays must have correct shape and dtype."""
    q, r = _generate(30, 100, 3, seed=1)
    k = 5
    idx, dist = find_knn(q, r, k)

    assert isinstance(idx, np.ndarray), "indices must be a numpy array"
    assert isinstance(dist, np.ndarray), "distances must be a numpy array"
    assert idx.shape == (30, k), f"indices shape {idx.shape} != expected (30, {k})"
    assert dist.shape == (30, k), f"distances shape {dist.shape} != expected (30, {k})"
    assert np.issubdtype(idx.dtype, np.integer), f"indices dtype {idx.dtype} is not integer"
    assert np.issubdtype(dist.dtype, np.floating), f"distances dtype {dist.dtype} is not float"


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2 — Correctness (small inputs)
# ═══════════════════════════════════════════════════════════════════════════

def test_correctness_small():
    """Exact index and distance match on small input."""
    q, r = _generate(50, 300, 3, seed=10)
    k = 5
    ref_idx, ref_dist = _baseline_knn(q, r, k)
    opt_idx, opt_dist = find_knn(q, r, k)

    assert np.array_equal(opt_idx, ref_idx), (
        f"Index mismatch on small input. "
        f"First diff at query {np.where(opt_idx != ref_idx)[0][0]}"
    )
    assert np.allclose(opt_dist, ref_dist, rtol=1e-6, atol=1e-12), (
        f"Distance mismatch. Max diff: {np.abs(opt_dist - ref_dist).max():.2e}"
    )


def test_correctness_medium():
    """Exact match on medium input."""
    q, r = _generate(200, 2000, 3, seed=20)
    k = 10
    ref_idx, ref_dist = _baseline_knn(q, r, k)
    opt_idx, opt_dist = find_knn(q, r, k)

    assert np.array_equal(opt_idx, ref_idx), (
        f"Index mismatch on medium input. "
        f"Mismatches: {np.sum(opt_idx != ref_idx)} entries"
    )
    assert np.allclose(opt_dist, ref_dist, rtol=1e-6, atol=1e-12), (
        f"Distance mismatch. Max diff: {np.abs(opt_dist - ref_dist).max():.2e}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3 — Edge cases
# ═══════════════════════════════════════════════════════════════════════════

def test_duplicate_reference_points():
    """When reference set has exact duplicates, tie-breaking by index matters."""
    rng = _np_random_RandomState(30)
    q = rng.randn(20, 3).astype(np.float64)
    base_refs = rng.randn(40, 3).astype(np.float64)
    # Triple the reference set: indices 0-39, 40-79, 80-119 have same coords
    r = np.vstack([base_refs, base_refs, base_refs])
    k = 8

    ref_idx, ref_dist = _baseline_knn(q, r, k)
    opt_idx, opt_dist = find_knn(q, r, k)

    assert np.array_equal(opt_idx, ref_idx), (
        "Tie-breaking mismatch on duplicate points. "
        "When distances are equal, lower index must come first."
    )
    assert np.allclose(opt_dist, ref_dist, rtol=1e-6, atol=1e-12)


def test_coincident_query_and_reference():
    """Query point that exactly matches a reference point (distance = 0)."""
    rng = _np_random_RandomState(40)
    r = rng.randn(100, 3).astype(np.float64)
    # Make some query points identical to reference points
    q = np.vstack([r[7:8], r[42:43], rng.randn(5, 3)]).astype(np.float64)
    k = 5

    ref_idx, ref_dist = _baseline_knn(q, r, k)
    opt_idx, opt_dist = find_knn(q, r, k)

    # First neighbor of query 0 must be ref index 7 with distance 0
    assert opt_idx[0, 0] == 7, f"Expected ref index 7 as nearest to query 0, got {opt_idx[0, 0]}"
    assert opt_dist[0, 0] < 1e-12, f"Expected zero distance, got {opt_dist[0, 0]}"
    # First neighbor of query 1 must be ref index 42
    assert opt_idx[1, 0] == 42, f"Expected ref index 42 as nearest to query 1, got {opt_idx[1, 0]}"

    assert np.array_equal(opt_idx, ref_idx)
    assert np.allclose(opt_dist, ref_dist, rtol=1e-6, atol=1e-12)


def test_large_coordinates():
    """Points with large coordinate values — test numerical stability."""
    rng = _np_random_RandomState(50)
    offset = np.array([1e7, -5e6, 3e6])
    q = (rng.randn(30, 3) * 0.01 + offset).astype(np.float64)
    r = (rng.randn(200, 3) * 0.01 + offset).astype(np.float64)
    k = 5

    ref_idx, ref_dist = _baseline_knn(q, r, k)
    opt_idx, opt_dist = find_knn(q, r, k)

    assert np.array_equal(opt_idx, ref_idx), "Mismatch with large coordinates"
    assert np.allclose(opt_dist, ref_dist, rtol=1e-6, atol=1e-12)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4 — Distances must be Euclidean (not squared)
# ═══════════════════════════════════════════════════════════════════════════

def test_distances_are_euclidean():
    """Verify returned distances are true Euclidean, not squared distances."""
    rng = _np_random_RandomState(60)
    q = rng.randn(10, 3).astype(np.float64)
    r = rng.randn(50, 3).astype(np.float64)
    k = 3

    idx, dist = find_knn(q, r, k)

    # Independently compute Euclidean distances from returned indices
    for i in range(q.shape[0]):
        for j_pos in range(k):
            j = idx[i, j_pos]
            expected_dist = np.sqrt(np.sum((q[i] - r[j]) ** 2))
            assert abs(dist[i, j_pos] - expected_dist) < 1e-8, (
                f"Distance at ({i},{j_pos}) is {dist[i, j_pos]:.10f} "
                f"but Euclidean distance is {expected_dist:.10f}. "
                f"Are you returning squared distances?"
            )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5 — Performance
# ═══════════════════════════════════════════════════════════════════════════

def test_performance_10x():
    """Optimized must be at least 10x faster than baseline on large input."""
    rng = _np_random_RandomState(70)
    n_queries = 10000
    n_refs = 50000
    d = 3
    k = 10

    q = rng.randn(n_queries, d).astype(np.float64)
    r = rng.randn(n_refs, d).astype(np.float64)

    # Time the baseline on a small subset to estimate full time
    # (running full baseline at this size takes too long for a test)
    subset_n = 100
    q_sub = q[:subset_n]

    t0 = _time_perf_counter()
    _baseline_knn(q_sub, r, k)
    t_base_subset = _time_perf_counter() - t0

    # Extrapolate: baseline is O(N*M) so scales linearly with N
    estimated_baseline_time = t_base_subset * (n_queries / subset_n)
    print(f"\n  Baseline estimated time (full): {estimated_baseline_time:.2f}s")
    print(f"  (measured {t_base_subset:.3f}s on {subset_n} queries, extrapolated)")

    # Time the optimized on full input
    t0 = _time_perf_counter()
    opt_idx, opt_dist = find_knn(q, r, k)
    t_opt = _time_perf_counter() - t0
    print(f"  Optimized time (full): {t_opt:.3f}s")

    # Verify correctness on the subset too
    ref_idx_sub, ref_dist_sub = _baseline_knn(q_sub, r, k)
    assert np.array_equal(opt_idx[:subset_n], ref_idx_sub), (
        "Correctness failure on large input (checked first 100 queries)"
    )
    assert np.allclose(opt_dist[:subset_n], ref_dist_sub, rtol=1e-6, atol=1e-12), (
        "Distance mismatch on large input"
    )

    speedup = estimated_baseline_time / t_opt if t_opt > 0 else float("inf")
    print(f"  Speedup: {speedup:.1f}x")

    assert speedup >= 10.0, (
        f"Speedup is only {speedup:.1f}x, need at least 10x. "
        f"Baseline (est): {estimated_baseline_time:.2f}s, Optimized: {t_opt:.3f}s"
    )


def test_performance_scales_subquadratically():
    """Verify solution doesn't degrade quadratically with M."""
    rng = _np_random_RandomState(80)
    d = 3
    k = 10

    q = rng.randn(1000, d).astype(np.float64)
    r_small = rng.randn(10000, d).astype(np.float64)
    r_large = rng.randn(40000, d).astype(np.float64)

    # Time on small M
    t0 = _time_perf_counter()
    find_knn(q, r_small, k)
    t_small = _time_perf_counter() - t0

    # Time on large M (4x references)
    t0 = _time_perf_counter()
    find_knn(q, r_large, k)
    t_large = _time_perf_counter() - t0

    ratio = t_large / t_small if t_small > 0 else float("inf")
    print(f"\n  Time with M=10000: {t_small:.3f}s")
    print(f"  Time with M=40000: {t_large:.3f}s")
    print(f"  Time ratio (4x refs): {ratio:.1f}x")

    # If solution is O(M log M), ratio should be ~4-5x.
    # If O(M^2), ratio would be ~16x.
    # Allow up to 8x to be generous (accounts for cache effects, etc.)
    assert ratio < 8.0, (
        f"Time ratio is {ratio:.1f}x when M increases 4x. "
        f"This suggests O(M^2) or worse scaling. "
        f"Expected sub-quadratic (< 8x for 4x more references)."
    )
