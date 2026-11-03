"""
KNN Search — optimize this function!

Replace the implementation of find_knn below with something faster.
The function signature and return format must stay the same.
"""

import numpy as np
import math


def find_knn(query_points, reference_points, k):
    """
    For each query point, find the k nearest neighbors in reference_points.

    Args:
        query_points: np.ndarray shape (N, D), float64
        reference_points: np.ndarray shape (M, D), float64
        k: int, number of neighbors

    Returns:
        indices: np.ndarray shape (N, k), int64 — indices into reference_points
        distances: np.ndarray shape (N, k), float64 — Euclidean distances
        Both sorted by distance ascending; ties broken by index ascending.
    """
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
            dist = math.sqrt(dist_sq)
            dists_with_idx.append((dist, j))

        # Python's sort is stable; sorting by (distance, index) gives
        # deterministic tie-breaking: same distance => lower index first
        dists_with_idx.sort()

        top_k_indices = [idx for _, idx in dists_with_idx[:k]]
        top_k_dists = [dist for dist, _ in dists_with_idx[:k]]

        all_indices.append(top_k_indices)
        all_distances.append(top_k_dists)

    return np.array(all_indices, dtype=np.int64), np.array(all_distances, dtype=np.float64)
