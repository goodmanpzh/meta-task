"""
Test suite for distributed gradient compression trainer.

Verifies correctness of the CompressedTrainer implementation against
the reference uncompressed trainer.
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, "/app")

from utils import (
    generate_synthetic_data, partition_data, init_model_params,
    forward_pass, backward_pass, compute_loss,
    flatten_grads, unflatten_grads, get_param_shapes
)
from reference_trainer import ReferenceTrainer
from distributed_trainer import CompressedTrainer


# ──────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────

@pytest.fixture
def setup_data():
    """Generate reproducible data and parameters."""
    X, Y = generate_synthetic_data()
    shards = partition_data(X, Y, 4)
    params = init_model_params()
    return X, Y, shards, params


# ──────────────────────────────────────────────────────────────────
# Test 1: Error feedback state correctness
# ──────────────────────────────────────────────────────────────────

def test_error_feedback_persistence(setup_data):
    """Error feedback buffers must retain state across training iterations."""
    _, _, shards, params = setup_data

    trainer = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, compression_ratio=0.1
    )

    # After 1 step with 10% compression, error feedback should be non-trivial
    trainer.train_step(shards)
    ef_after_1 = trainer.get_error_feedback()

    ef_norms = [np.linalg.norm(ef) for ef in ef_after_1]
    for w, norm in enumerate(ef_norms):
        assert norm > 1e-10, (
            f"Worker {w} error feedback has zero norm after step 1 "
            f"(norm={norm:.2e})."
        )

    # After step 2, error feedback should still be non-zero and different
    trainer.train_step(shards)
    ef_after_2 = trainer.get_error_feedback()

    ef_norms_2 = [np.linalg.norm(ef) for ef in ef_after_2]
    for w in range(4):
        assert ef_norms_2[w] > 1e-10, (
            f"Worker {w} error feedback has zero norm after step 2."
        )
        diff = np.linalg.norm(ef_after_2[w] - ef_after_1[w])
        assert diff > 1e-10, (
            f"Worker {w} error feedback unchanged between steps 1 and 2 "
            f"(diff={diff:.2e})."
        )


# ──────────────────────────────────────────────────────────────────
# Test 2: Determinism across runs
# ──────────────────────────────────────────────────────────────────

def test_determinism(setup_data):
    """Two runs with identical inputs must produce identical loss curves."""
    _, _, shards, params = setup_data

    trainer1 = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, compression_ratio=0.1
    )
    losses1 = trainer1.train(shards, 30)

    trainer2 = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, compression_ratio=0.1
    )
    losses2 = trainer2.train(shards, 30)

    for i, (l1, l2) in enumerate(zip(losses1, losses2)):
        assert l1 == l2, (
            f"Non-deterministic result at iteration {i}: "
            f"loss1={l1:.10e}, loss2={l2:.10e}."
        )


# ──────────────────────────────────────────────────────────────────
# Test 3: Full compression matches reference trainer
# ──────────────────────────────────────────────────────────────────

def test_full_compression_matches_reference(setup_data):
    """With compression_ratio=1.0 (no sparsification), the compressed
    trainer must exactly match the reference trainer."""
    _, _, shards, params = setup_data

    ref = ReferenceTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, lr=0.01, momentum=0.9
    )
    comp = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, lr=0.01, momentum=0.9,
        compression_ratio=1.0
    )

    num_steps = 20
    for step in range(num_steps):
        ref_loss = ref.train_step(shards)
        comp_loss = comp.train_step(shards)

        assert abs(ref_loss - comp_loss) < 1e-10, (
            f"Step {step}: reference loss={ref_loss:.12e}, "
            f"compressed loss={comp_loss:.12e}, "
            f"diff={abs(ref_loss - comp_loss):.2e}."
        )

    # Also check parameter values match
    ref_params = ref.get_params()
    comp_params = comp.get_params()
    for k in ['W1', 'b1', 'W2', 'b2']:
        diff = np.max(np.abs(ref_params[k] - comp_params[k]))
        assert diff < 1e-10, (
            f"Parameter {k} diverged: max diff={diff:.2e}."
        )


# ──────────────────────────────────────────────────────────────────
# Test 4: Training convergence
# ──────────────────────────────────────────────────────────────────

def test_training_convergence(setup_data):
    """Compressed training must converge to a low loss within 200 iterations."""
    _, _, shards, params = setup_data

    trainer = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, compression_ratio=0.1
    )
    losses = trainer.train(shards, 200)

    # Final loss should be below threshold
    assert losses[-1] < 0.05, (
        f"Final loss after 200 iterations: {losses[-1]:.6f}. "
        f"Expected < 0.05."
    )

    # Loss should generally decrease
    early_avg = np.mean(losses[:50])
    late_avg = np.mean(losses[150:])
    assert late_avg < early_avg * 0.5, (
        f"Training not decreasing: early avg={early_avg:.6f}, "
        f"late avg={late_avg:.6f}."
    )


# ──────────────────────────────────────────────────────────────────
# Test 5: Communication efficiency
# ──────────────────────────────────────────────────────────────────

def test_communication_efficiency(setup_data):
    """Compressed communication must use <= 10% of full gradient size."""
    _, _, shards, params = setup_data

    trainer = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, compression_ratio=0.1
    )
    stats = trainer.get_compression_stats()

    assert stats['communication_fraction'] <= 0.1 + 1e-9, (
        f"Communication fraction {stats['communication_fraction']:.4f} "
        f"exceeds 10% limit."
    )
    assert stats['entries_communicated_per_worker'] <= stats['total_params'] * 0.1 + 1, (
        f"Entries communicated ({stats['entries_communicated_per_worker']}) "
        f"exceeds 10% of total params ({stats['total_params']})."
    )


# ──────────────────────────────────────────────────────────────────
# Test 6: All-reduce aggregation correctness
# ──────────────────────────────────────────────────────────────────

def test_allreduce_averaging(setup_data):
    """All-reduce of sparse gradients must produce correct averaged values."""
    _, _, shards, params = setup_data

    trainer = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, compression_ratio=0.1
    )

    # Construct test sparse gradients with known overlapping indices
    test_sparse = [
        (np.array([0, 1, 2]), np.array([4.0, 8.0, 12.0])),
        (np.array([1, 2, 3]), np.array([2.0, 6.0, 10.0])),
        (np.array([2, 3, 4]), np.array([1.0, 3.0, 5.0])),
        (np.array([0, 4, 5]), np.array([3.0, 7.0, 9.0])),
    ]

    agg_idx, agg_val = trainer._allreduce_compressed(test_sparse)

    # Compute expected: for each unique index, the correct aggregated value
    # is the sum of all contributions at that index divided by num_workers
    all_idx = np.concatenate([s[0] for s in test_sparse])
    all_val = np.concatenate([s[1] for s in test_sparse])
    expected_idx = np.unique(all_idx)
    expected_val = np.zeros(len(expected_idx), dtype=np.float64)
    for i, idx in enumerate(expected_idx):
        expected_val[i] = np.sum(all_val[all_idx == idx]) / trainer.num_workers

    np.testing.assert_array_equal(agg_idx, expected_idx)
    np.testing.assert_allclose(agg_val, expected_val, atol=1e-12, err_msg=(
        "All-reduce aggregation produced incorrect values."
    ))


# ──────────────────────────────────────────────────────────────────
# Test 7: Momentum buffer correctness
# ──────────────────────────────────────────────────────────────────

def test_momentum_uses_correct_gradient(setup_data):
    """Momentum buffers must match the reference trainer when using
    full compression (no sparsification)."""
    _, _, shards, params = setup_data

    comp = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, lr=0.01, momentum=0.9,
        compression_ratio=1.0
    )
    ref = ReferenceTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, lr=0.01, momentum=0.9
    )

    for step in range(5):
        comp.train_step(shards)
        ref.train_step(shards)

    comp_mom = comp.get_momentum_buffers()
    ref_mom_dict = ref.get_momentum_buffers()
    ref_mom = np.concatenate([ref_mom_dict[k].ravel() for k in ['W1', 'b1', 'W2', 'b2']])

    diff = np.max(np.abs(comp_mom - ref_mom))
    assert diff < 1e-10, (
        f"Momentum buffer diverged from reference after 5 steps: "
        f"max diff={diff:.2e}."
    )


# ──────────────────────────────────────────────────────────────────
# Test 8: Error feedback bounded norm
# ──────────────────────────────────────────────────────────────────

def test_error_feedback_convergence_guarantee(setup_data):
    """Error feedback norm should remain bounded over many iterations,
    not diverge."""
    _, _, shards, params = setup_data

    trainer = CompressedTrainer(
        {k: v.copy() for k, v in params.items()},
        num_workers=4, compression_ratio=0.1
    )

    num_iters = 100
    trainer.train(shards, num_iters)

    ef = trainer.get_error_feedback()
    for w in range(4):
        ef_norm = np.linalg.norm(ef[w])
        assert ef_norm < 100.0, (
            f"Worker {w} error feedback norm is {ef_norm:.2e} after "
            f"{num_iters} iterations. Norm should remain bounded."
        )
