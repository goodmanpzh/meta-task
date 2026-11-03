## Optimizing spatial KNN search — need 10x speedup over my baseline

I have a brute-force K-nearest-neighbors implementation in `/app/knn.py` that's painfully slow on real workloads. It does a naive O(N*M) pairwise distance computation with Python loops to find the K closest reference points for each query point.

**My setup:**
- Python 3.11, numpy 1.24, scipy 1.11 are available
- Ubuntu (Debian slim)
- Single CPU core, 4GB RAM

**What I need:**

Replace the `find_knn` function in `/app/knn.py` with an optimized version. The function signature and return format must stay the same:

```python
def find_knn(query_points, reference_points, k):
    """
    Args:
        query_points: np.ndarray shape (N, D), float64
        reference_points: np.ndarray shape (M, D), float64
        k: int
    Returns:
        indices: np.ndarray shape (N, k), int — indices into reference_points
        distances: np.ndarray shape (N, k), float64 — Euclidean distances
    """
```

Results must be sorted by distance ascending for each query. When distances are tied (equal), sort by index ascending (lower index first).

**Performance target:** The optimized function must be **at least 10x faster** than my baseline when tested with N=10000, M=50000, D=3, K=10.

**Correctness:** Neighbor indices must exactly match the baseline output for any input (with the same tie-breaking). Distances must match within 1e-6 relative tolerance.

**What I've tried so far:**
- Replacing the inner loop with `np.linalg.norm` broadcasting — got maybe 3-4x but then OOM'd on larger inputs because computing the full N×M distance matrix eats all the RAM
- Thought about using C but that seems like overkill for this

There's a benchmark script at `/app/benchmark.py` you can use to test your solution. The baseline code is in `/app/knn_baseline.py` (don't modify this — it's the reference).

You can install additional Python packages if needed, but the entrypoint must remain a Python function `find_knn` in `/app/knn.py`.
