#!/usr/bin/env python3
"""
utils.py
--------
Utility functions for synthetic data generation and seed management.
Used by both the distributed trainer and the reference trainer.

DO NOT MODIFY THIS FILE.
"""

import numpy as np


def generate_synthetic_data(num_samples=400, input_dim=64, output_dim=10, seed=12345):
    """Generate a synthetic regression dataset with fixed seed.

    Returns:
        X: (num_samples, input_dim) input features
        Y: (num_samples, output_dim) targets
    """
    rng = np.random.RandomState(seed)
    # Ground-truth weight matrix
    W_true = rng.randn(input_dim, output_dim) * 0.3
    b_true = rng.randn(output_dim) * 0.1

    X = rng.randn(num_samples, input_dim).astype(np.float64)
    noise = rng.randn(num_samples, output_dim).astype(np.float64) * 0.05
    Y = (X @ W_true + b_true + noise).astype(np.float64)
    return X, Y


def partition_data(X, Y, num_workers):
    """Partition data evenly across workers (each gets a disjoint shard).

    Returns:
        list of (X_shard, Y_shard) tuples, one per worker.
    """
    n = X.shape[0]
    shard_size = n // num_workers
    shards = []
    for w in range(num_workers):
        start = w * shard_size
        end = start + shard_size
        shards.append((X[start:end], Y[start:end]))
    return shards


def init_model_params(input_dim=64, hidden_dim=128, output_dim=10, seed=42):
    """Initialize 2-layer MLP parameters with fixed seed.

    Architecture: input -> Linear(hidden) -> ReLU -> Linear(output)

    Returns:
        params: dict with keys 'W1', 'b1', 'W2', 'b2'
    """
    rng = np.random.RandomState(seed)
    # Xavier-like initialization
    scale1 = np.sqrt(2.0 / (input_dim + hidden_dim))
    scale2 = np.sqrt(2.0 / (hidden_dim + output_dim))

    params = {
        'W1': rng.randn(input_dim, hidden_dim).astype(np.float64) * scale1,
        'b1': np.zeros(hidden_dim, dtype=np.float64),
        'W2': rng.randn(hidden_dim, output_dim).astype(np.float64) * scale2,
        'b2': np.zeros(output_dim, dtype=np.float64),
    }
    return params


def forward_pass(params, X):
    """Forward pass through 2-layer MLP.

    Returns:
        output: (batch, output_dim) predictions
        cache: intermediate values needed for backprop
    """
    # Layer 1
    z1 = X @ params['W1'] + params['b1']  # (batch, hidden)
    a1 = np.maximum(z1, 0)  # ReLU

    # Layer 2
    z2 = a1 @ params['W2'] + params['b2']  # (batch, output)

    cache = {'X': X, 'z1': z1, 'a1': a1}
    return z2, cache


def backward_pass(params, cache, predictions, targets):
    """Backward pass computing gradients for all parameters.

    Loss = 0.5 * mean((predictions - targets)^2)

    Returns:
        grads: dict with keys 'W1', 'b1', 'W2', 'b2' matching params
    """
    batch_size = targets.shape[0]
    X = cache['X']
    z1 = cache['z1']
    a1 = cache['a1']

    # Output layer gradient
    dz2 = (predictions - targets) / batch_size  # (batch, output)

    dW2 = a1.T @ dz2        # (hidden, output)
    db2 = dz2.sum(axis=0)    # (output,)

    # Hidden layer gradient (through ReLU)
    da1 = dz2 @ params['W2'].T   # (batch, hidden)
    dz1 = da1 * (z1 > 0)         # ReLU derivative

    dW1 = X.T @ dz1              # (input, hidden)
    db1 = dz1.sum(axis=0)        # (hidden,)

    grads = {'W1': dW1, 'b1': db1, 'W2': dW2, 'b2': db2}
    return grads


def compute_loss(predictions, targets):
    """MSE loss: 0.5 * mean((pred - target)^2)"""
    return 0.5 * np.mean((predictions - targets) ** 2)


def flatten_grads(grads):
    """Flatten gradient dict into a single 1D array.

    Order: W1, b1, W2, b2
    """
    return np.concatenate([grads[k].ravel() for k in ['W1', 'b1', 'W2', 'b2']])


def unflatten_grads(flat, shapes):
    """Unflatten a 1D array back to gradient dict.

    Args:
        flat: 1D array
        shapes: dict with keys 'W1', 'b1', 'W2', 'b2' mapping to shape tuples
    """
    grads = {}
    offset = 0
    for k in ['W1', 'b1', 'W2', 'b2']:
        size = 1
        for d in shapes[k]:
            size *= d
        grads[k] = flat[offset:offset + size].reshape(shapes[k])
        offset += size
    return grads


def get_param_shapes(params):
    """Get shapes dict from params dict."""
    return {k: v.shape for k, v in params.items()}
