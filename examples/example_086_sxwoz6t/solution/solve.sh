#!/bin/bash
set -e

mkdir -p /app/output

# Write the recovery and analysis script
cat > /tmp/solve_task.py << 'PYEOF'
#!/usr/bin/env python3
"""
Reference solution for MQ WAL Crash Recovery & Forensics
"""

import struct
import zlib
import json
import os
import re
import glob

MQDATA = "/app/mqdata"
OUTPUT = "/app/output"

###############################################################################
# STEP 1: Parse binary WAL format and recover valid messages
###############################################################################

MAGIC = 0x4D514C47  # "MQLG"

def parse_wal_file(filepath):
    """Parse a WAL file, returning valid messages and corruption info."""
    valid_messages = []
    corruption_info = None

    with open(filepath, 'rb') as f:
        # Read 16-byte header
        header_data = f.read(16)
        if len(header_data) < 16:
            return [], {"error": "truncated header"}

        magic = struct.unpack('<I', header_data[0:4])[0]
        if magic != MAGIC:
            return [], {"error": f"bad magic: 0x{magic:08X}"}

        version = struct.unpack('<H', header_data[4:6])[0]
        topic_hash = struct.unpack('<I', header_data[6:10])[0]
        partition = struct.unpack('<H', header_data[10:12])[0]

        # Determine topic name from filename
        basename = os.path.basename(filepath)
        # e.g., "orders-0.wal"
        parts = basename.rsplit('.', 1)[0].rsplit('-', 1)
        topic_name = parts[0]

        last_valid_seq = None
        first_corrupt_seq = None

        while True:
            pos = f.tell()

            # Read record length
            record_len_bytes = f.read(4)
            if len(record_len_bytes) == 0:
                break  # End of file
            if len(record_len_bytes) < 4:
                if first_corrupt_seq is None:
                    first_corrupt_seq = (last_valid_seq or 0) + 1
                corruption_info = {
                    "last_valid_seq": last_valid_seq,
                    "corruption_start_seq": first_corrupt_seq,
                    "type": "truncated_record_length"
                }
                break

            record_len = struct.unpack('<I', record_len_bytes)[0]

            # Sanity check
            if record_len < 27 or record_len > 10_000_000:
                if first_corrupt_seq is None:
                    first_corrupt_seq = (last_valid_seq or 0) + 1
                corruption_info = {
                    "last_valid_seq": last_valid_seq,
                    "corruption_start_seq": first_corrupt_seq,
                    "type": "invalid_record_length"
                }
                break

            # Read the rest of the record
            remaining = record_len - 4
            data = f.read(remaining)
            if len(data) < remaining:
                if first_corrupt_seq is None:
                    first_corrupt_seq = (last_valid_seq or 0) + 1
                corruption_info = {
                    "last_valid_seq": last_valid_seq,
                    "corruption_start_seq": first_corrupt_seq,
                    "type": "truncated_record"
                }
                break

            # Split payload and CRC
            payload = data[:-4]
            crc_stored = struct.unpack('<I', data[-4:])[0]
            crc_calc = zlib.crc32(payload) & 0xFFFFFFFF

            if crc_stored != crc_calc:
                if first_corrupt_seq is None:
                    # Try to read seq num from payload for reporting
                    try:
                        corrupt_seq = struct.unpack('<Q', payload[0:8])[0]
                        first_corrupt_seq = corrupt_seq
                    except:
                        first_corrupt_seq = (last_valid_seq or 0) + 1
                    corruption_info = {
                        "last_valid_seq": last_valid_seq,
                        "corruption_start_seq": first_corrupt_seq,
                        "type": "crc_mismatch"
                    }
                continue  # Skip bad record but try to read more

            # Parse the valid record
            try:
                offset = 0
                seq_num = struct.unpack('<Q', payload[offset:offset+8])[0]
                offset += 8
                timestamp_us = struct.unpack('<Q', payload[offset:offset+8])[0]
                offset += 8
                key_len = struct.unpack('<H', payload[offset:offset+2])[0]
                offset += 2
                key = payload[offset:offset+key_len].decode('utf-8')
                offset += key_len
                value_len = struct.unpack('<I', payload[offset:offset+4])[0]
                offset += 4
                value_raw = payload[offset:offset+value_len].decode('utf-8')
                offset += value_len
                flags = payload[offset]

                # Parse value as JSON
                try:
                    value = json.loads(value_raw)
                except json.JSONDecodeError:
                    value = value_raw

                valid_messages.append({
                    "topic": topic_name,
                    "partition": partition,
                    "sequence": seq_num,
                    "timestamp_us": timestamp_us,
                    "key": key,
                    "value": value,
                    "flags": flags
                })
                last_valid_seq = seq_num
            except Exception as e:
                if first_corrupt_seq is None:
                    first_corrupt_seq = (last_valid_seq or 0) + 1
                corruption_info = {
                    "last_valid_seq": last_valid_seq,
                    "corruption_start_seq": first_corrupt_seq,
                    "type": f"parse_error: {str(e)}"
                }
                continue

    return valid_messages, corruption_info


# Parse all WAL files
all_messages = []
corruption_report = {}

wal_dir = os.path.join(MQDATA, "wal")
for wal_file in sorted(glob.glob(os.path.join(wal_dir, "*.wal"))):
    basename = os.path.basename(wal_file).rsplit('.', 1)[0]
    messages, corruption = parse_wal_file(wal_file)
    all_messages.extend(messages)
    if corruption:
        corruption_report[basename] = corruption

# Sort by sequence number
all_messages.sort(key=lambda m: m["sequence"])

# Write recovered messages
with open(os.path.join(OUTPUT, "recovered_messages.json"), 'w') as f:
    json.dump(all_messages, f, indent=2)

print(f"Recovered {len(all_messages)} valid messages")

# Write corruption report
with open(os.path.join(OUTPUT, "corruption_report.json"), 'w') as f:
    json.dump(corruption_report, f, indent=2)

print(f"Found corruption in {len(corruption_report)} partitions")

###############################################################################
# STEP 2: Root Cause Analysis
###############################################################################

# Parse broker log
broker_log_path = os.path.join(MQDATA, "logs", "mq-broker.log")
with open(broker_log_path, 'r') as f:
    broker_log = f.read()

# Parse inventory tracker log
inv_log_path = os.path.join(MQDATA, "logs", "inventory-tracker.log")
with open(inv_log_path, 'r') as f:
    inv_log = f.read()

# Parse config
with open(os.path.join(MQDATA, "config", "broker.json"), 'r') as f:
    broker_config = json.load(f)

with open(os.path.join(MQDATA, "config", "consumers.json"), 'r') as f:
    consumer_config = json.load(f)

# Parse system log for PID
system_log_path = os.path.join(MQDATA, "logs", "system.log")
with open(system_log_path, 'r') as f:
    system_log = f.read()

# Extract PID from OOM kill
pid_match = re.search(r'Killed process (\d+) \(mq-broker\)', system_log)
crash_pid = int(pid_match.group(1)) if pid_match else 0

# Extract transaction IDs
trigger_txn = "TXN-8834721"  # The one started by inventory-tracker
deadlock_txn = "TXN-8834755"  # The one that got blocked

# Build timeline
timeline = [
    {"timestamp": "2024-03-30T23:55:00", "event": "inventory-tracker starts cross-topic transaction TXN-8834721 for [inventory-1, orders-2]"},
    {"timestamp": "2024-03-30T23:55:05", "event": "TXN-8834721 acquires write locks on inventory-1 and orders-2"},
    {"timestamp": "2024-03-30T23:55:02", "event": "inventory-tracker transaction write fails, enters infinite retry loop (retry_policy=aggressive_infinite)"},
    {"timestamp": "2024-03-30T23:55:20", "event": "TXN-8834721 still holding locks after 10+ seconds, inventory-tracker stalled"},
    {"timestamp": "2024-03-30T23:55:30", "event": "payment-gateway starts cross-topic transaction TXN-8834755 for [payments-0, orders-2]"},
    {"timestamp": "2024-03-30T23:55:32", "event": "TXN-8834755 acquires write lock on payments-0 but blocks on orders-2 (held by TXN-8834721)"},
    {"timestamp": "2024-03-30T23:56:00", "event": "Deadlock detector classifies situation as FALSE POSITIVE because partition_lock_analysis=false"},
    {"timestamp": "2024-03-30T23:56:20", "event": "TXN-8834755 aborted due to lock timeout, fails to cleanly release payments-0 lock (EBUSY)"},
    {"timestamp": "2024-03-30T23:56:25", "event": "Message backlog grows uncontrolled, broker memory reaches 94%"},
    {"timestamp": "2024-03-30T23:57:00", "event": "Forced lock release fails for TXN-8834721: nested lock reference count mismatch"},
    {"timestamp": "2024-03-30T23:57:30", "event": "Broker memory at 98%, allocation failures begin"},
    {"timestamp": "2024-03-30T23:57:48", "event": "OOM killer terminates broker process (PID 28401)"},
    {"timestamp": "2024-03-30T23:58:00", "event": "WAL flush fails mid-write, partial writes corrupt multiple partitions"},
    {"timestamp": "2024-03-30T23:58:05", "event": "Emergency shutdown fails to flush inventory-tracker offsets"},
]

rca_report = {
    "root_cause_summary": (
        "The crash was triggered by a cascading failure originating from the inventory-tracker consumer service. "
        "The inventory-tracker initiated a cross-topic transaction (TXN-8834721) spanning inventory-1 and orders-2 partitions. "
        "When the write to orders-2 failed due to a partition leader change, the consumer's aggressive_infinite retry policy "
        "caused it to retry indefinitely while holding write locks. This prevented the payment-gateway's transaction "
        "(TXN-8834755) from acquiring the orders-2 lock, creating a resource starvation deadlock. The broker's deadlock "
        "detector failed to identify this because the partition_lock_analysis feature flag was set to false, causing it "
        "to only check group-level dependencies and miss the partition-level lock conflict. The resulting message backlog "
        "grew unbounded, exhausting the broker's 8GB memory limit. The Linux OOM killer terminated the broker process "
        "(PID 28401), and the emergency shutdown's WAL flush produced partial writes that corrupted records across all partitions."
    ),
    "trigger_service": "inventory-tracker",
    "trigger_transaction": "TXN-8834721",
    "deadlock_transaction": "TXN-8834755",
    "config_bug": "transactions.partition_lock_analysis=false",
    "consumer_bug": "inventory-tracker.retry_policy=aggressive_infinite",
    "crash_pid": crash_pid,
    "timeline": timeline
}

with open(os.path.join(OUTPUT, "rca_report.json"), 'w') as f:
    json.dump(rca_report, f, indent=2)

print("RCA report generated")

###############################################################################
# STEP 3: Consumer Audit
###############################################################################

# Build WAL head positions (last valid seq per topic-partition)
wal_heads = {}
for msg in all_messages:
    key = (msg["topic"], msg["partition"])
    if key not in wal_heads or msg["sequence"] > wal_heads[key]:
        wal_heads[key] = msg["sequence"]

# Read consumer offset files
consumer_audit = {}
offsets_dir = os.path.join(MQDATA, "offsets")

for consumer_name in os.listdir(offsets_dir):
    consumer_path = os.path.join(offsets_dir, consumer_name)
    if not os.path.isdir(consumer_path):
        continue

    has_lock = os.path.exists(os.path.join(consumer_path, ".lock"))

    topics = set()
    total_lag = 0
    status = None

    for offset_file in glob.glob(os.path.join(consumer_path, "*.offset")):
        with open(offset_file, 'r') as f:
            offset_data = json.load(f)

        topic = offset_data["topic"]
        partition = offset_data["partition"]
        committed = offset_data["committed_offset"]
        consumer_status = offset_data["consumer_status"]

        topics.add(topic)
        if status is None:
            status = consumer_status

        # Calculate lag
        head = wal_heads.get((topic, partition), committed)
        lag = max(0, head - committed)
        total_lag += lag

    consumer_audit[consumer_name] = {
        "status": status or "unknown",
        "topics": sorted(list(topics)),
        "total_lag": total_lag,
        "has_stale_lock": has_lock
    }

with open(os.path.join(OUTPUT, "consumer_audit.json"), 'w') as f:
    json.dump(consumer_audit, f, indent=2)

print("Consumer audit generated")
print(f"\nAll output written to {OUTPUT}/")
PYEOF

python3 /tmp/solve_task.py
rm -f /tmp/solve_task.py
