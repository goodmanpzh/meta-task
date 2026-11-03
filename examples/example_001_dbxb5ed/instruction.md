**Problem:** Distributed training with gradient compression diverges; uncompressed baseline converges fine

**System Description:**
A data-parallel training system at `/app/distributed_trainer.py` uses Top-K gradient sparsification with error feedback to reduce communication by 90%. It simulates 4 workers performing synchronous SGD with momentum on a 2-layer MLP regression task. The reference implementation at `/app/reference_trainer.py` uses standard uncompressed gradient averaging and converges correctly.

**Reproduction:**

```
$ cd /app && python3 -c "
from utils import generate_synthetic_data, partition_data, init_model_params
from distributed_trainer import CompressedTrainer
from reference_trainer import ReferenceTrainer

X, Y = generate_synthetic_data()
shards = partition_data(X, Y, 4)
params = init_model_params()

ref = ReferenceTrainer({k: v.copy() for k, v in params.items()})
ref_losses = ref.train(shards, 200)

comp = CompressedTrainer({k: v.copy() for k, v in params.items()})
comp_losses = comp.train(shards, 200)

print(f'Reference final loss: {ref_losses[-1]:.6f}')
print(f'Compressed final loss: {comp_losses[-1]:.6f}')
"
```

| Metric | Expected | Actual |
|--------|----------|--------|
| Reference loss (200 iters) | < 0.005 | ~ 0.002 (OK) |
| Compressed loss (200 iters) | < 0.05 | > 1.0 (divergent) |
| Gradient norm ratio (compressed/reference) | 1.0 ± 0.5 | > 3.0 |

**Additional observations:**
- Setting `compression_ratio=1.0` (no compression, keep all entries) still does NOT match the reference trainer's output. Multiple issues seem to be present.
- With 4 workers and 10% compression, communication per step should be ≤ 10% of full gradient size.

**Expected:** Fix `/app/distributed_trainer.py` so that:
1. Training converges: final loss < 0.05 after 200 iterations
2. Error feedback accumulates correctly across iterations (non-zero after first step)
3. Results are deterministic (identical across runs with same data)
4. With `compression_ratio=1.0`, the compressed trainer matches the reference trainer within tolerance 1e-10

**Constraints:**
- Do NOT modify `/app/reference_trainer.py`, `/app/utils.py`, or any test files
- Only modify `/app/distributed_trainer.py`
- The `CompressedTrainer` class interface (constructor signature, public methods) must remain unchanged
