#!/bin/bash
set -euo pipefail

cd /app

# Fix all bugs in distributed_trainer.py
cat > /app/distributed_trainer.py <<'PYEOF'
#!/usr/bin/env python3
"""
distributed_trainer.py
----------------------
Distributed data-parallel training with Top-K gradient sparsification
and error feedback for communication-efficient training.

This module simulates multiple workers performing synchronous data-parallel
SGD with compressed gradient communication. Each worker:
  1. Computes local gradients on its data shard
  2. Adds accumulated error feedback to the gradient
  3. Applies Top-K sparsification to select the most important gradient entries
  4. Participates in all-reduce of the compressed (sparse) gradients
  5. Updates error feedback with the residual (what was NOT communicated)
  6. Applies the averaged compressed gradient with momentum

The compression ratio is controlled by the `compression_ratio` parameter,
which specifies the fraction of gradient entries to keep (e.g., 0.1 = 10%).
"""

import numpy as np
from utils import (
    forward_pass, backward_pass, compute_loss,
    flatten_grads, unflatten_grads, get_param_shapes
)


class CompressedTrainer:
    """Data-parallel SGD with Top-K gradient compression and error feedback."""

    def __init__(self, params, num_workers=4, lr=0.01, momentum=0.9,
                 compression_ratio=0.1):
        """
        Args:
            params: dict of model parameters {'W1', 'b1', 'W2', 'b2'}
            num_workers: number of simulated workers
            lr: learning rate
            momentum: momentum coefficient for SGD
            compression_ratio: fraction of gradient entries to keep (0.0 to 1.0)
        """
        self.num_workers = num_workers
        self.lr = lr
        self.momentum = momentum
        self.compression_ratio = compression_ratio

        # Each worker has its own copy of parameters
        self.worker_params = [
            {k: v.copy() for k, v in params.items()}
            for _ in range(num_workers)
        ]
        self.shapes = get_param_shapes(params)

        # Total number of parameters (for flattened gradient)
        self.total_params = sum(
            v.size for v in params.values()
        )
        self.k = max(1, int(self.total_params * compression_ratio))

        # Error feedback accumulators: one per worker, flattened
        self.error_feedback = [
            np.zeros(self.total_params, dtype=np.float64)
            for _ in range(num_workers)
        ]

        # Momentum buffers: one per worker (all start identical)
        self.momentum_buf = [
            np.zeros(self.total_params, dtype=np.float64)
            for _ in range(num_workers)
        ]

        # Store the accumulated gradient for momentum computation
        self._accumulated_grads = [
            np.zeros(self.total_params, dtype=np.float64)
            for _ in range(num_workers)
        ]

    def _topk_sparsify(self, gradient, k):
        """Select the top-k entries by magnitude from a flattened gradient.

        Args:
            gradient: 1D numpy array
            k: number of entries to keep

        Returns:
            indices: 1D array of selected indices (sorted deterministically)
            values: 1D array of selected values
        """
        abs_grad = np.abs(gradient)
        # Use argpartition for efficient top-k selection
        top_indices = np.argpartition(abs_grad, -k)[-k:]
        # FIX: Sort by magnitude descending, then index ascending for determinism
        sorted_order = np.lexsort((top_indices, -abs_grad[top_indices]))
        top_indices = top_indices[sorted_order]
        return top_indices, gradient[top_indices]

    def _decompress_gradient(self, indices, values, size):
        """Reconstruct a full dense gradient from sparse representation.

        Args:
            indices: 1D array of positions
            values: 1D array of values at those positions
            size: total size of the full gradient

        Returns:
            full_gradient: dense 1D array
        """
        full_gradient = np.zeros(size, dtype=np.float64)
        full_gradient[indices] = values
        return full_gradient

    def _allreduce_compressed(self, worker_sparse_grads):
        """Simulate all-reduce of compressed gradients across workers.

        Each worker contributes (indices, values). We aggregate by summing
        values at matching indices and averaging over total number of workers.

        Args:
            worker_sparse_grads: list of (indices, values) per worker

        Returns:
            (result_indices, result_values): aggregated sparse gradient
        """
        # Gather all indices and values from all workers
        all_indices = np.concatenate([sg[0] for sg in worker_sparse_grads])
        all_values = np.concatenate([sg[1] for sg in worker_sparse_grads])

        # Find unique indices and aggregate values
        unique_indices = np.unique(all_indices)
        aggregated_values = np.zeros(len(unique_indices), dtype=np.float64)

        for i, idx in enumerate(unique_indices):
            mask = all_indices == idx
            # FIX: Always divide by num_workers, not by number of contributors
            aggregated_values[i] = np.sum(all_values[mask]) / self.num_workers

        return unique_indices, aggregated_values

    def train_step(self, data_shards):
        """One training step with compressed gradient communication.

        Args:
            data_shards: list of (X, Y) tuples, one per worker

        Returns:
            avg_loss: average loss across workers
        """
        total_loss = 0.0
        worker_sparse_grads = []

        # Phase 1: Each worker computes and compresses gradients
        for w in range(self.num_workers):
            X_w, Y_w = data_shards[w]
            preds, cache = forward_pass(self.worker_params[w], X_w)
            loss = compute_loss(preds, Y_w)
            total_loss += loss

            # Compute gradient and flatten
            grads = backward_pass(self.worker_params[w], cache, preds, Y_w)
            flat_grad = flatten_grads(grads)

            # Add error feedback from previous iteration
            accumulated = flat_grad + self.error_feedback[w]
            self._accumulated_grads[w] = accumulated.copy()

            # Compress via Top-K sparsification
            indices, values = self._topk_sparsify(accumulated, self.k)

            # Update error feedback: residual = accumulated - what was sent
            compressed_approx = np.zeros_like(accumulated)
            compressed_approx[indices] = values
            self.error_feedback[w] = accumulated - compressed_approx

            worker_sparse_grads.append((indices, values))

        avg_loss = total_loss / self.num_workers

        # Phase 2: All-reduce the compressed gradients
        agg_indices, agg_values = self._allreduce_compressed(worker_sparse_grads)

        # Phase 3: Apply to all workers
        for w in range(self.num_workers):
            # Decompress the aggregated gradient
            full_update = self._decompress_gradient(
                agg_indices, agg_values, self.total_params
            )

            # FIX: Apply SGD with momentum using allreduced gradient, not accumulated
            self.momentum_buf[w] = (
                self.momentum * self.momentum_buf[w]
                + full_update
            )
            update = self.lr * self.momentum_buf[w]

            # Unflatten and apply to parameters
            grad_dict = unflatten_grads(update, self.shapes)
            for k in ['W1', 'b1', 'W2', 'b2']:
                self.worker_params[w][k] -= grad_dict[k]

        # FIX: Removed _finalize_iteration() call that was incorrectly resetting
        # error feedback. Error feedback must persist across iterations.
        # Only reset the temporary accumulated grads buffer.
        self._accumulated_grads = [
            np.zeros(self.total_params, dtype=np.float64)
            for _ in range(self.num_workers)
        ]

        return avg_loss

    def get_params(self):
        """Return current parameters (from worker 0)."""
        return {k: v.copy() for k, v in self.worker_params[0].items()}

    def get_momentum_buffers(self):
        """Return current momentum buffers (from worker 0, flattened)."""
        return self.momentum_buf[0].copy()

    def get_error_feedback(self):
        """Return error feedback vectors for all workers."""
        return [ef.copy() for ef in self.error_feedback]

    def get_compression_stats(self):
        """Return compression statistics."""
        return {
            'total_params': self.total_params,
            'k': self.k,
            'compression_ratio': self.compression_ratio,
            'entries_communicated_per_worker': self.k,
            'communication_fraction': self.k / self.total_params,
        }

    def train(self, data_shards, num_iterations):
        """Run multiple training steps, returning loss history."""
        losses = []
        for _ in range(num_iterations):
            loss = self.train_step(data_shards)
            losses.append(loss)
        return losses
PYEOF

echo "Solution applied successfully."
