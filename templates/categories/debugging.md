### Category: Systems Diagnosis and Resilience

Tasks involving building diagnostic tools, implementing resilient systems, creating monitoring infrastructure, and understanding system internals through analysis and construction.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Diagnostic Tool Building:*
- Build a log analysis engine that classifies error patterns and generates structured reports
- Implement a memory profiling harness that tracks allocations across multiple modules
- Create a dependency conflict resolver that produces a valid lockfile from constraints
- Build a stack trace symbolizer for stripped binaries using debug info
- Implement a system call tracer that captures and replays I/O sequences

*Resilience & Recovery Systems:*
- Build a self-healing service wrapper that detects failures and restarts with backoff
- Implement a WAL (write-ahead log) system with crash recovery guarantees
- Create a checkpoint/restore mechanism for long-running computations
- Build a circuit breaker implementation with configurable failure thresholds
- Implement a data reconciliation system that detects and resolves inconsistencies

*System Internals & Analysis:*
- Reverse-engineer a binary protocol from packet captures and build a parser
- Implement a custom memory allocator with specific performance characteristics
- Build a file format validator that checks structural integrity against a spec
- Create a process monitor that tracks resource usage and detects anomalies
- Implement a lock-free data structure with correctness verification

*Debugging Challenges:*
- Fix code that crashes under specific conditions (Release vs Debug mode differences)
- Debug memory leaks or race conditions in a multi-threaded system
- Repair corrupted files or databases to recover data (SQLite WAL, truncated files)
- Debug environment-specific failures ("works on my machine" issues)

**Skills & Tools** (tag suggestions for your task):
- Core: `systems-programming`, `debugging`, `coding`, `analysis`
- Tools: `gdb`, `valgrind`, `strace`, `perf`, `ltrace`, `lsof`, `tcpdump`
- Environment: `env`, `printenv`, `ldd`, `file`, `nm`, `objdump`
- Languages: `c`, `cpp`, `python`, `rust`, `go`
- Related: `memory-management`, `concurrency`, `networking`, `filesystems`

**Possible Input Data** (be creative with environment files!):
- Source code with complex internal structure to study and extend
- Binary files or packet captures to reverse-engineer
- Database files (SQLite, custom formats) to analyze or build tools for
- Configuration systems with multiple interacting components
- System logs requiring analysis pipeline construction
- Core dumps or memory profiles as input to diagnostic tools
- Network traffic captures for protocol analysis
- Build system configurations (Makefile, CMake) to work with
- Multi-threaded code requiring synchronization analysis

**Verification Approaches**:
- Built tool produces correct output on test inputs
- System handles failure scenarios correctly (crash recovery, graceful degradation)
- Implementation meets performance requirements (latency, throughput)
- Correctness under concurrent access (race-free, deadlock-free)
- Recovered/processed data matches expected output exactly
- Resource usage stays within bounds (no leaks, bounded memory)

**Remember**: Create challenges that test understanding of system internals, the ability to build robust infrastructure, and deep problem-solving. Focus on tasks where the agent must understand how things work before it can build or fix anything!
