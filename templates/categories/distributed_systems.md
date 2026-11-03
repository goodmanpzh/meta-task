### Category: Distributed Systems

Tasks involving distributed computing, consensus protocols, cluster management, and distributed data processing.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Distributed checkpoint and recovery systems
- Consensus protocol implementations (Raft, Paxos basics)
- Cluster state management (etcd, ZooKeeper)
- Distributed transaction coordination
- Causal ordering and vector clocks
- Quorum-based systems
- Distributed hash tables
- Leader election algorithms
- Distributed lock services
- Cross-datacenter replication
- Partition tolerance and recovery
- Distributed tracing and observability
- Sharding and data distribution strategies

**Skills & Tools** (tag suggestions for your task):
- Core: `distributed-systems`, `consensus`, `cluster`, `replication`
- Protocols: `raft`, `paxos`, `gossip`, `two-phase-commit`
- Tools: `etcd`, `zookeeper`, `consul`
- Concepts: `cap-theorem`, `eventual-consistency`, `quorum`, `vector-clock`
- Languages: `python`, `go`, `java`

**Possible Input Data** (be creative with environment files!):
- Cluster configuration files (YAML, JSON)
- Transaction logs and WAL files
- Snapshot files for state recovery
- Node membership lists
- Network partition scenarios
- Checkpoint metadata (Parquet, JSON)
- Distributed trace data
- Failure injection scripts
- Consensus protocol state dumps

**Verification Approaches**:
- Cluster health and membership verification
- Data consistency checks across nodes
- Causal ordering validation
- Recovery completeness verification
- Leader election correctness
- Partition recovery testing
- Audit hash verification for checkpoints
- Latency and throughput benchmarks

**Remember**: Distributed systems tasks should test understanding of failure modes, consistency models, and recovery procedures. Include realistic failure scenarios and network partitions!
