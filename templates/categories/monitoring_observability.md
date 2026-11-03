### Category: Monitoring and Observability

Tasks involving log analysis, distributed tracing, metrics collection, alerting systems, and observability infrastructure implementation.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Build distributed tracing pipelines with span collection and trace reconstruction
- Implement log anomaly detection with pattern recognition and alerting
- Create metrics aggregation systems with time-series analysis
- Build service dependency graph extraction from traces
- Implement SLI/SLO monitoring and compliance reporting
- Create log correlation engines for multi-service request tracking
- Build performance profiling report generators
- Implement alert deduplication and intelligent grouping
- Create dashboard data aggregation pipelines
- Build log shipping pipelines with data loss detection
- Implement trace sampling strategies (head-based, tail-based)
- Create metrics cardinality analysis tools
- Build observability data retention and compaction systems
- Implement cross-service latency analysis pipelines

**Skills & Tools** (tag suggestions for your task):
- Core: `monitoring`, `observability`, `logging`, `tracing`, `metrics`
- Protocols: `opentelemetry`, `jaeger`, `zipkin`, `prometheus`, `statsd`
- Analysis: `anomaly-detection`, `correlation`, `aggregation`, `time-series`
- Concepts: `spans`, `traces`, `cardinality`, `sampling`, `SLI`, `SLO`
- Tools: `elasticsearch`, `grafana`, `prometheus`, `loki`, `fluentd`

**Possible Input Data** (be creative with environment files!):
- Application logs in various formats (JSON, syslog, custom)
- Trace data (spans with parent-child relationships)
- Metrics time-series data (Prometheus format)
- Service topology definitions
- Alert rules and thresholds
- Historical incident data
- Request correlation IDs
- Performance baseline data
- Log schemas and parsing rules
- Retention policies and quotas

**Verification Approaches**:
- Trace reconstruction accuracy (parent-child relationships correct)
- Anomaly detection precision and recall
- Metric aggregation accuracy within tolerance
- Alert firing correctness (no false positives/negatives)
- Service dependency graph completeness
- Query latency meets requirements
- Data retention compliance
- Sampling maintains statistical validity
- Cross-service correlation accuracy

**Remember**: Observability tasks should include realistic noise, high cardinality challenges, and require understanding of distributed systems concepts like causality and sampling bias!