### Category: Performance Optimization

Tasks focused on making code faster, smaller, or more efficient than a baseline implementation.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Optimize numerical algorithms to beat baseline performance (matrix operations, eigenvalue computation, FFT)
- Rewrite Python/scripting code in C/Rust for significant speedup
- Optimize SQL queries for large datasets (index optimization, query rewriting)
- Reduce memory footprint of data processing pipelines
- Implement SIMD/vectorized computations
- Cache optimization and memory access pattern improvements
- Algorithmic complexity improvements (O(n^2) to O(n log n))
- Parallel/concurrent optimization (threading, multiprocessing)
- GPU acceleration for compute-intensive tasks
- LLM inference throughput optimization (batching schedulers)
- Physics simulation performance tuning (MuJoCo, game engines)

**Skills & Tools** (tag suggestions for your task):
- Core: `optimization`, `performance`, `profiling`
- Languages: `c`, `cpp`, `rust`, `assembly`, `cython`
- Techniques: `simd`, `cache-optimization`, `parallelization`, `vectorization`
- Tools: `perf`, `valgrind`, `gprof`, `benchmark`, `hyperfine`

**Possible Input Data** (be creative with environment files!):
- Baseline implementations (correct but slow Python code)
- Benchmark scripts to measure performance
- Large datasets for testing scalability
- Skeleton files with TODO markers to complete
- Build configurations (setup.py, Makefile for C extensions)
- Profiler output showing bottlenecks
- Reference implementations in different languages
- Test cases with performance thresholds (must be 1.2x, 2x, 10x faster)
- SQL databases with slow queries
- MJCF/physics simulation config files
- LLM inference request batches (JSONL)

**Verification Approaches**:
- Benchmark against baseline (must be X times faster)
- Verify correctness matches baseline (within 1e-10 numerical tolerance)
- Test on multiple input sizes for scalability
- Check memory usage constraints
- Verify code compiles and runs without errors
- Measure throughput for batch processing tasks

**Remember**: Optimization tasks should have clear baselines and measurable targets. Focus on real performance bottlenecks and practical optimization techniques that require understanding of both algorithms and hardware!
