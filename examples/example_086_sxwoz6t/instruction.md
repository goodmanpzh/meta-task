```
$ /opt/mq-broker/bin/broker-ctl status
Error: Could not connect to broker at 0.0.0.0:9092 - Connection refused
Last known state: CRASHED (exit code 137)
Data directory: /app/mqdata

$ dmesg | tail -5
[1711843047.482913] mq-broker invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0, oom_score_adj=0
[1711843047.482920] CPU: 2 PID: 28401 Comm: mq-broker Not tainted 5.15.0-91-generic #101-Ubuntu
[1711843047.482960] Memory cgroup out of memory: Killed process 28401 (mq-broker) total-vm:8503216kB, anon-rss:7987456kB
[1711843050.123456] oom_reaper: reaped process 28401 (mq-broker), now anon-rss:0kB
[1711843050.654321] USB 1-1: USB disconnect, device number 3

$ ls /app/mqdata/wal/
inventory-0.wal  inventory-1.wal  notifications-0.wal  orders-0.wal  orders-1.wal  orders-2.wal  payments-0.wal  payments-1.wal
```

our message queue broker got OOM killed over the weekend. all the WAL files use some custom binary format. we need to recover everything we can before restarting. nobody documented the binary format but the files should be self-describing if you look at the hex.

need you to:

1. figure out the WAL binary format by inspecting the files, then parse all WAL files and extract every message with a valid CRC checksum. write recovered messages to `/app/output/recovered_messages.json` as a JSON array sorted by sequence number. each entry needs: `topic`, `partition`, `sequence`, `timestamp_us`, `key`, `value` (parsed JSON), and `flags`

2. identify which WAL partitions have corruption (bad CRC or truncation), and for each one, report the last valid sequence number. write to `/app/output/corruption_report.json`

3. figure out what actually caused the crash. dig through all the logs in `/app/mqdata/logs/` and metrics in `/app/mqdata/metrics/` and configs in `/app/mqdata/config/`. write a root cause analysis to `/app/output/rca_report.json` with these fields:
   - `root_cause_summary`: one-paragraph description of the chain of events
   - `trigger_service`: which consumer/service triggered the cascade
   - `trigger_transaction`: the transaction ID that started it all
   - `deadlock_transaction`: the transaction ID that got deadlocked
   - `config_bug`: the specific config setting that allowed this to happen (format: "section.key=value")
   - `consumer_bug`: the specific consumer config that made it worse (format: "consumer_name.setting=value")
   - `crash_pid`: PID of the OOM-killed process
   - `timeline`: array of objects with `timestamp` and `event` describing key events in chronological order (minimum 8 events)

4. audit all consumer offset files in `/app/mqdata/offsets/` and determine which consumers are stale/orphaned vs active. calculate how many messages behind each consumer is. write to `/app/output/consumer_audit.json` as an object keyed by consumer name, each with: `status` (active/crashed/orphaned/decommissioned), `topics`, `total_lag` (messages behind the WAL head), and `has_stale_lock` (boolean)

all output goes in `/app/output/`. existing data is in `/app/mqdata/`.
