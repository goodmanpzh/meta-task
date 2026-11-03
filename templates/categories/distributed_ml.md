### Category: Distributed Machine Learning

Tasks involving distributed training, model parallelism, large-scale ML systems, inference optimization, and ML infrastructure.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Implement tensor parallelism for large models (column/row parallel linear layers)
- Build pipeline parallelism training systems
- Implement data parallel training with gradient synchronization
- Create efficient inference batching and scheduling systems (LLM inference)
- Implement model sharding and checkpointing
- Build distributed embedding tables
- Implement gradient compression or quantization for distributed training
- Create fault-tolerant training loops with checkpoint recovery
- Implement ZeRO-style memory optimization
- Build inference serving systems with dynamic batching
- Implement attention parallelism strategies
- Create distributed data loaders with proper shuffling

**Skills & Tools** (tag suggestions for your task):
- Core: `distributed-ml`, `parallel-computing`, `deep-learning`, `inference`
- Frameworks: `pytorch`, `tensorflow`, `jax`, `deepspeed`, `megatron`
- Concepts: `tensor-parallelism`, `pipeline-parallelism`, `data-parallelism`, `batching`
- Communication: `nccl`, `gloo`, `mpi`, `collective-operations`
- Infrastructure: `gpu`, `multi-node`, `checkpoint`, `fault-tolerance`

**Possible Input Data** (be creative with environment files!):
- Model architecture definitions (PyTorch modules)
- Weight files for sharding/parallelism
- Training data batches (tensors, datasets)
- Baseline single-GPU implementations to parallelize
- Communication topology configurations
- Checkpoint files for recovery testing
- Batch request files for inference scheduling (JSONL)
- Profiling data for optimization
- Memory budget constraints
- Cluster configuration files

**Verification Approaches**:
- Numerical correctness vs single-GPU baseline (within tolerance)
- Training loss convergence matches expected
- Inference throughput meets requirements
- Memory usage within limits
- Checkpoint save/load correctness
- Gradient synchronization correctness
- Batch scheduling efficiency metrics
- Fault recovery works correctly
- Latency constraints for inference

**Remember**: Distributed ML tasks test understanding of parallel computing, communication patterns, and ML system design. Include scenarios with memory constraints, varying batch sizes, or simulated multi-device environments. Verification should ensure numerical correctness alongside performance!
