#!/usr/bin/env python3
"""
reference_trainer.py
--------------------
Reference implementation: standard (uncompressed) data-parallel SGD with momentum.
This serves as the ground-truth baseline for verifying the compressed trainer.

Each worker computes gradients on its own data shard, then gradients are
averaged across all workers (simulated all-reduce) and applied with momentum.

DO NOT MODIFY THIS FILE.
"""

import numpy as np
from utils import (
    forward_pass, backward_pass, compute_loss,
    flatten_grads, unflatten_grads, get_param_shapes
)


class ReferenceTrainer:
    """Standard data-parallel SGD with momentum (no compression)."""

    def __init__(self, params, num_workers=4, lr=0.01, momentum=0.9):
        self.num_workers = num_workers
        self.lr = lr
        self.momentum = momentum

        # Each worker has its own copy of parameters (they stay synchronized)
        self.worker_params = [
            {k: v.copy() for k, v in params.items()}
            for _ in range(num_workers)
        ]
        self.shapes = get_param_shapes(params)

        # Momentum buffers (shared, since params are synchronized)
        self.momentum_buf = {
            k: np.zeros_like(v) for k, v in params.items()
        }

    def train_step(self, data_shards):
        """One training step across all workers.

        Args:
            data_shards: list of (X, Y) tuples, one per worker

        Returns:
            avg_loss: average loss across workers
        """
        all_grads = []
        total_loss = 0.0

        # Each worker computes local gradients
        for w in range(self.num_workers):
            X_w, Y_w = data_shards[w]
            preds, cache = forward_pass(self.worker_params[w], X_w)
            loss = compute_loss(preds, Y_w)
            total_loss += loss
            grads = backward_pass(self.worker_params[w], cache, preds, Y_w)
            all_grads.append(grads)

        avg_loss = total_loss / self.num_workers

        # All-reduce: average gradients across workers
        avg_grads = {}
        for k in ['W1', 'b1', 'W2', 'b2']:
            avg_grads[k] = np.mean(
                [all_grads[w][k] for w in range(self.num_workers)], axis=0
            )

        # Apply SGD with momentum
        for k in ['W1', 'b1', 'W2', 'b2']:
            self.momentum_buf[k] = (
                self.momentum * self.momentum_buf[k] + avg_grads[k]
            )
            update = self.lr * self.momentum_buf[k]
            for w in range(self.num_workers):
                self.worker_params[w][k] -= update

        return avg_loss

    def get_params(self):
        """Return current parameters (from worker 0, all workers are identical)."""
        return {k: v.copy() for k, v in self.worker_params[0].items()}

    def get_momentum_buffers(self):
        """Return current momentum buffers."""
        return {k: v.copy() for k, v in self.momentum_buf.items()}

    def train(self, data_shards, num_iterations):
        """Run multiple training steps, returning loss history."""
        losses = []
        for _ in range(num_iterations):
            loss = self.train_step(data_shards)
            losses.append(loss)
        return losses
