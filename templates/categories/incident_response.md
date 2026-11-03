### Category: Incident Response and Production Debugging

Tasks involving production incident investigation, system forensics, multi-component failure diagnosis, emergency recovery, crash dump analysis, and root cause analysis report generation.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Incident Response & Recovery:*
- Production outage root cause analysis
- Multi-service failure chain reconstruction
- Environment poisoning detection and cleanup
- Deployment rollback and recovery
- Database crash recovery (WAL replay, transaction log forensics)
- Memory leak and resource exhaustion diagnosis
- Configuration drift detection and reconciliation
- Service dependency failure cascades
- Checkpoint-based recovery system implementation

*Forensics & Investigation:*
- Log forensics and timeline reconstruction
- Crash dump analysis and stack trace interpretation
- Binary protocol message stream crash recovery
- Distributed transaction deadlock forensics
- Network packet connection forensics (PCAP analysis)
- Git repository history forensics and secret leak detection
- Container image layer forensic timeline reconstruction
- Process tree forensics and privilege escalation reconstruction
- ETL pipeline audit trail forensic reconstruction
- Build artifact provenance chain forensics

*Security Incident Analysis:*
- Security incident investigation and lateral movement tracing
- SSH key compromise and lateral movement forensics
- Disk image forensic analysis and file recovery
- Privilege escalation chain reconstruction
- Cryptographic vulnerability audit and remediation
- Secret vault rotation and recovery after compromise

*Root Cause Analysis & Reporting:*
- Post-mortem report generation with evidence collection
- Microservice failure chain analysis diagnostic reports
- Database query performance degradation diagnosis
- Network latency degradation diagnosis reports
- CI/CD pipeline failure RCA report generation
- Distributed system split-brain forensics and RCA

**Skills & Tools** (tag suggestions for your task):
- Core: `incident-response`, `forensics`, `troubleshooting`, `debugging`, `rca`
- Analysis: `log-analysis`, `timeline-reconstruction`, `root-cause-analysis`, `crash-dump-analysis`
- Tools: `journalctl`, `dmesg`, `strace`, `lsof`, `netstat`, `gdb`, `tcpdump`, `wireshark`
- Forensics: `volatility`, `sleuthkit`, `binwalk`, `strings`, `hexdump`
- Concepts: `idempotency`, `rollback`, `recovery`, `blast-radius`, `chain-of-custody`
- Related: `monitoring`, `alerting`, `observability`, `audit-trail`

**Possible Input Data** (be creative with environment files!):
- Application logs with errors and warnings (multi-format, multi-service)
- System logs (syslog, journald exports, dmesg)
- Crash dumps and core files
- Network capture files (PCAP)
- Database transaction logs and WAL files
- Git repository with history for forensics
- Container image layers and manifests
- Metrics snapshots (Prometheus, time-series data)
- Configuration files (current and historical versions)
- Deployment manifests and rollout history
- Alert notifications and escalation chains
- Process lists and resource usage snapshots
- Disk images or filesystem snapshots
- Memory dumps for volatile data analysis
- Audit logs (SSH, sudo, application-level)

**Verification Approaches**:
- Service health restoration verification
- Data integrity confirmation (checksums, row counts)
- Root cause identification accuracy (correct component, correct event)
- Recovery procedure completeness
- No regression in functionality
- Incident report accuracy and completeness
- Timeline reconstruction correctness (event ordering)
- Evidence chain integrity
- Prevention measures implementation
- Forensic artifact preservation

**Remember**: Incident response and forensics tasks should include realistic "noise" (unrelated warnings, red herrings), require systematic investigation, and test the ability to distinguish symptoms from root causes. Include multiple evidence sources that need correlation!
