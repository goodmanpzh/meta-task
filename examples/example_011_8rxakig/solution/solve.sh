#!/bin/bash

# Optimized KNN using scipy's cKDTree for spatial indexing.
# Key insights:
# 1. cKDTree gives O(M log M) build + O(K log M) per query in low dimensions
# 2. Must handle tie-breaking: when distances are equal, lower index wins
# 3. Must return actual Euclidean distances (not squared)
# 4. cKDTree.query doesn't guarantee index-based tie-breaking, so we
#    must post-process ties to enforce the (distance, index) sort order.

cat > /app/knn.py << 'PYEOF'
import numpy as np
from scipy.spatial import cKDTree


def find_knn(query_points, reference_points, k):
    """
    Optimized KNN using scipy cKDTree.

    Args:
        query_points: np.ndarray shape (N, D), float64
        reference_points: np.ndarray shape (M, D), float64
        k: int, number of neighbors

    Returns:
        indices: np.ndarray shape (N, k), int64
        distances: np.ndarray shape (N, k), float64
    """
    query_points = np.ascontiguousarray(query_points, dtype=np.float64)
    reference_points = np.ascontiguousarray(reference_points, dtype=np.float64)

    # Build KD-tree on reference points
    tree = cKDTree(reference_points)

    # Query slightly more neighbors to handle potential ties at the boundary.
    # cKDTree doesn't guarantee stable tie-breaking by index, so we fetch
    # extra candidates and re-sort ties ourselves.
    k_extra = min(k + 10, reference_points.shape[0])
    dists_extra, idxs_extra = tree.query(query_points, k=k_extra)

    # Ensure 2D output even when k_extra == 1
    if k_extra == 1:
        dists_extra = dists_extra.reshape(-1, 1)
        idxs_extra = idxs_extra.reshape(-1, 1)

    n = query_points.shape[0]
    out_indices = np.empty((n, k), dtype=np.int64)
    out_distances = np.empty((n, k), dtype=np.float64)

    for i in range(n):
        d = dists_extra[i]
        ix = idxs_extra[i]

        # Stable sort by (distance, index) to enforce tie-breaking rule
        order = np.lexsort((ix, d))
        sorted_d = d[order]
        sorted_ix = ix[order]

        out_distances[i] = sorted_d[:k]
        out_indices[i] = sorted_ix[:k]

    return out_indices, out_distances
PYEOF

echo "Solution written to /app/knn.py"
echo "Testing with benchmark..."
cd /app && python benchmark.py
