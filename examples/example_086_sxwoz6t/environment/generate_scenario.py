#!/usr/bin/env python3
"""
Generate a realistic message queue crash scenario with:
- Binary WAL files with CRC32 checksums
- Corrupted segments simulating mid-write crash
- Multiple topic partitions
- Consumer offset files (some orphaned)
- Application logs from multiple services
- System logs showing the crash sequence
- Metric snapshots
"""

import struct
import zlib
import json
import os
import time
import random
import hashlib

random.seed(42)

BASE = "/app/mqdata"
WAL_DIR = f"{BASE}/wal"
INDEX_DIR = f"{BASE}/index"
OFFSETS_DIR = f"{BASE}/offsets"
LOGS_DIR = f"{BASE}/logs"
METRICS_DIR = f"{BASE}/metrics"
CONFIG_DIR = f"{BASE}/config"

for d in [WAL_DIR, INDEX_DIR, OFFSETS_DIR, LOGS_DIR, METRICS_DIR, CONFIG_DIR]:
    os.makedirs(d, exist_ok=True)

# ============================================================
# WAL Binary Format Specification (the agent must reverse-engineer this):
#
# WAL File Header (16 bytes):
#   Magic:     4 bytes  = 0x4D514C47 ("MQLG")
#   Version:   2 bytes  = uint16 LE (currently 3)
#   TopicHash: 4 bytes  = uint32 LE (CRC32 of topic name)
#   Partition: 2 bytes  = uint16 LE
#   Reserved:  4 bytes  = 0x00000000
#
# WAL Record (variable length):
#   RecordLen: 4 bytes  = uint32 LE (length of entire record including this field)
#   SeqNum:    8 bytes  = uint64 LE (monotonically increasing)
#   Timestamp: 8 bytes  = uint64 LE (unix epoch microseconds)
#   KeyLen:    2 bytes  = uint16 LE
#   Key:       KeyLen bytes
#   ValueLen:  4 bytes  = uint32 LE
#   Value:     ValueLen bytes
#   Flags:     1 byte   (0x00=normal, 0x01=compressed, 0x02=tombstone, 0x04=txn_begin, 0x08=txn_commit, 0x10=txn_abort)
#   CRC32:     4 bytes  = uint32 LE (CRC32 of everything from SeqNum to Flags inclusive)
#
# ============================================================

MAGIC = 0x4D514C47
VERSION = 3

def write_wal_header(f, topic_name, partition):
    topic_hash = zlib.crc32(topic_name.encode()) & 0xFFFFFFFF
    f.write(struct.pack('<I', MAGIC))
    f.write(struct.pack('<H', VERSION))
    f.write(struct.pack('<I', topic_hash))
    f.write(struct.pack('<H', partition))
    f.write(b'\x00' * 4)  # reserved

def make_record(seq_num, timestamp_us, key, value, flags=0x00):
    """Build a WAL record and return bytes."""
    key_bytes = key.encode() if isinstance(key, str) else key
    value_bytes = value.encode() if isinstance(value, str) else value

    # Build payload (everything that CRC covers)
    payload = struct.pack('<Q', seq_num)
    payload += struct.pack('<Q', timestamp_us)
    payload += struct.pack('<H', len(key_bytes))
    payload += key_bytes
    payload += struct.pack('<I', len(value_bytes))
    payload += value_bytes
    payload += struct.pack('<B', flags)

    crc = zlib.crc32(payload) & 0xFFFFFFFF
    record_len = 4 + len(payload) + 4  # len field + payload + crc
    return struct.pack('<I', record_len) + payload + struct.pack('<I', crc)

def make_corrupted_record(seq_num, timestamp_us, key, value, flags=0x00, corrupt_type="truncated"):
    """Build a corrupted WAL record."""
    good = make_record(seq_num, timestamp_us, key, value, flags)
    if corrupt_type == "truncated":
        # Truncate at a random point past the header
        cut = random.randint(20, len(good) - 8)
        return good[:cut]
    elif corrupt_type == "bad_crc":
        # Flip some bits in the CRC
        data = bytearray(good)
        data[-2] ^= 0xFF
        data[-3] ^= 0xAA
        return bytes(data)
    elif corrupt_type == "bad_data":
        # Corrupt some bytes in the value
        data = bytearray(good)
        mid = len(data) // 2
        for i in range(mid, min(mid + 8, len(data) - 4)):
            data[i] ^= 0x55
        # Recalculate record to have bad data but original CRC (simulates bit flip)
        return bytes(data)
    return good

# ============================================================
# Topics and their messages
# ============================================================

TOPICS = {
    "orders": {
        "partitions": 3,
        "messages_per_partition": [150, 120, 135],
    },
    "payments": {
        "partitions": 2,
        "messages_per_partition": [200, 180],
    },
    "inventory": {
        "partitions": 2,
        "messages_per_partition": [90, 110],
    },
    "notifications": {
        "partitions": 1,
        "messages_per_partition": [250],
    },
}

# The crash happened at this timestamp
CRASH_TIME_US = 1711843200_000000  # 2024-03-31 00:00:00 UTC in microseconds
CRASH_TIME_S = CRASH_TIME_US // 1_000_000

# Track all valid messages for verification
all_valid_messages = {}  # topic -> partition -> [(seq, timestamp, key, value, flags)]
crash_info = {}

# Generate WAL files
for topic_name, topic_cfg in TOPICS.items():
    all_valid_messages[topic_name] = {}
    for partition in range(topic_cfg["partitions"]):
        num_messages = topic_cfg["messages_per_partition"][partition]
        all_valid_messages[topic_name][partition] = []

        wal_path = os.path.join(WAL_DIR, f"{topic_name}-{partition}.wal")
        with open(wal_path, 'wb') as f:
            write_wal_header(f, topic_name, partition)

            base_ts = CRASH_TIME_US - (num_messages * 500_000)  # ~500ms between messages
            seq = partition * 10000 + 1

            for i in range(num_messages):
                ts = base_ts + i * random.randint(400_000, 600_000)
                key = f"{topic_name}-{partition}-{seq}"

                # Generate realistic message values
                if topic_name == "orders":
                    value = json.dumps({
                        "order_id": f"ORD-{seq:06d}",
                        "customer_id": f"CUST-{random.randint(1000, 9999)}",
                        "amount": round(random.uniform(10.0, 5000.0), 2),
                        "status": random.choice(["created", "confirmed", "processing", "shipped"]),
                        "items": random.randint(1, 12)
                    })
                elif topic_name == "payments":
                    value = json.dumps({
                        "payment_id": f"PAY-{seq:06d}",
                        "order_id": f"ORD-{random.randint(1, seq):06d}",
                        "amount": round(random.uniform(10.0, 5000.0), 2),
                        "method": random.choice(["credit_card", "debit_card", "wire", "crypto"]),
                        "status": random.choice(["pending", "completed", "failed"])
                    })
                elif topic_name == "inventory":
                    value = json.dumps({
                        "sku": f"SKU-{random.randint(100, 999)}",
                        "warehouse": random.choice(["US-EAST", "US-WEST", "EU-CENTRAL"]),
                        "delta": random.randint(-50, 200),
                        "reason": random.choice(["sale", "restock", "return", "adjustment"])
                    })
                elif topic_name == "notifications":
                    value = json.dumps({
                        "notification_id": f"NTF-{seq:06d}",
                        "channel": random.choice(["email", "sms", "push", "webhook"]),
                        "recipient": f"user-{random.randint(1, 5000)}@example.com",
                        "type": random.choice(["order_update", "payment_receipt", "shipping_alert", "promo"])
                    })

                # Determine flags
                flags = 0x00
                if random.random() < 0.05:
                    flags = 0x04  # txn_begin
                elif random.random() < 0.05:
                    flags = 0x08  # txn_commit

                # Introduce corruption near the crash point
                is_near_crash = (i >= num_messages - 8)

                if is_near_crash and i >= num_messages - 3:
                    # Last 3 records are corrupted (mid-write crash)
                    if i == num_messages - 3:
                        # Bad CRC - disk write was partial
                        record = make_corrupted_record(seq, ts, key, value, flags, "bad_crc")
                        crash_info[f"{topic_name}-{partition}"] = {
                            "last_valid_seq": seq - 1,
                            "corruption_start_seq": seq,
                            "corruption_type": "bad_crc then truncation"
                        }
                    elif i == num_messages - 2:
                        # Data corruption
                        record = make_corrupted_record(seq, ts, key, value, flags, "bad_data")
                    else:
                        # Truncated record (crash mid-write)
                        record = make_corrupted_record(seq, ts, key, value, flags, "truncated")
                    f.write(record)
                else:
                    record = make_record(seq, ts, key, value, flags)
                    f.write(record)
                    all_valid_messages[topic_name][partition].append({
                        "seq": seq,
                        "timestamp_us": ts,
                        "key": key,
                        "value": value,
                        "flags": flags
                    })

                seq += 1

# ============================================================
# Index files (intentionally stale - last updated before crash)
# The index maps sequence numbers to file offsets for fast lookup
# Index format: sequence of (seq_num: uint64, file_offset: uint64) pairs
# But the index is stale - it was last synced ~50 messages before the crash
# ============================================================

for topic_name, topic_cfg in TOPICS.items():
    for partition in range(topic_cfg["partitions"]):
        idx_path = os.path.join(INDEX_DIR, f"{topic_name}-{partition}.idx")
        valid_msgs = all_valid_messages[topic_name][partition]
        # Only index ~70% of messages (stale)
        indexed_count = int(len(valid_msgs) * 0.7)

        with open(idx_path, 'wb') as f:
            # Index header
            f.write(struct.pack('<I', 0x4D514958))  # "MQIX"
            f.write(struct.pack('<I', indexed_count))

            offset = 16  # WAL header size
            for i, msg in enumerate(valid_msgs[:indexed_count]):
                f.write(struct.pack('<QQ', msg["seq"], offset))
                # Approximate record size for offset tracking
                key_bytes = msg["key"].encode()
                value_bytes = msg["value"].encode()
                record_size = 4 + 8 + 8 + 2 + len(key_bytes) + 4 + len(value_bytes) + 1 + 4
                offset += record_size

# ============================================================
# Consumer offset files
# Some are current, some are orphaned (from consumers that crashed)
# ============================================================

consumers = {
    "order-processor": {
        "topics": {"orders": {0: None, 1: None, 2: None}},
        "status": "active"
    },
    "payment-gateway": {
        "topics": {"payments": {0: None, 1: None}},
        "status": "active"
    },
    "inventory-tracker": {
        "topics": {"inventory": {0: None, 1: None}, "orders": {0: None, 1: None, 2: None}},
        "status": "crashed"
    },
    "notification-sender": {
        "topics": {"notifications": {0: None}},
        "status": "active"
    },
    "analytics-pipeline": {
        "topics": {"orders": {0: None, 1: None, 2: None}, "payments": {0: None, 1: None}},
        "status": "orphaned"
    },
    # Red herring: a consumer that was already decommissioned
    "legacy-exporter": {
        "topics": {"orders": {0: None}},
        "status": "decommissioned"
    }
}

for consumer_name, consumer_cfg in consumers.items():
    consumer_dir = os.path.join(OFFSETS_DIR, consumer_name)
    os.makedirs(consumer_dir, exist_ok=True)

    for topic, partitions in consumer_cfg["topics"].items():
        for part in partitions:
            valid_msgs = all_valid_messages[topic][part]
            if consumer_cfg["status"] == "active":
                # Active consumers have recent offsets (within last 20 messages)
                committed_idx = max(0, len(valid_msgs) - random.randint(5, 20))
            elif consumer_cfg["status"] == "crashed":
                # Crashed consumers have offsets that are ~40% behind
                committed_idx = int(len(valid_msgs) * 0.6)
            elif consumer_cfg["status"] == "orphaned":
                # Orphaned consumers stopped long ago
                committed_idx = int(len(valid_msgs) * 0.3)
            elif consumer_cfg["status"] == "decommissioned":
                committed_idx = int(len(valid_msgs) * 0.1)

            if committed_idx < len(valid_msgs):
                committed_seq = valid_msgs[committed_idx]["seq"]
                committed_ts = valid_msgs[committed_idx]["timestamp_us"]
            else:
                committed_seq = valid_msgs[-1]["seq"]
                committed_ts = valid_msgs[-1]["timestamp_us"]

            offset_data = {
                "consumer_group": consumer_name,
                "topic": topic,
                "partition": part,
                "committed_offset": committed_seq,
                "committed_timestamp_us": committed_ts,
                "last_heartbeat_us": CRASH_TIME_US - random.randint(1_000_000, 60_000_000),
                "consumer_status": consumer_cfg["status"]
            }

            offset_path = os.path.join(consumer_dir, f"{topic}-{part}.offset")
            with open(offset_path, 'w') as f:
                json.dump(offset_data, f, indent=2)

    # Create a lock file for crashed consumers
    if consumer_cfg["status"] == "crashed":
        lock_path = os.path.join(consumer_dir, ".lock")
        with open(lock_path, 'w') as f:
            f.write(f"PID: 28491\nAcquired: {CRASH_TIME_S - 120}\n")

# ============================================================
# Application logs (multiple services, with noise and red herrings)
# ============================================================

def make_log_ts(offset_seconds):
    """Create a log timestamp relative to crash time."""
    t = CRASH_TIME_S + offset_seconds
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))

# MQ Broker logs
broker_logs = []
# Normal operation logs (noise)
for i in range(-3600, -300, random.randint(5, 15)):
    broker_logs.append(f'{make_log_ts(i)} INFO  [broker-main] Processed batch of {random.randint(50, 200)} messages across {random.randint(2, 5)} partitions')
    if random.random() < 0.1:
        broker_logs.append(f'{make_log_ts(i+1)} WARN  [broker-main] Consumer heartbeat delayed for analytics-pipeline (lag: {random.randint(500, 5000)}ms)')
    if random.random() < 0.05:
        broker_logs.append(f'{make_log_ts(i+2)} INFO  [gc-thread] Compacted 3 segments for topic notifications-0, freed {random.randint(1, 50)}MB')

# The critical sequence leading to crash
# ROOT CAUSE: A runaway transaction from the inventory-tracker consumer held a write lock
# on the "orders" WAL partition 2, causing a deadlock with the payment-gateway trying to
# write cross-partition transaction markers. The broker's deadlock detector had a bug where
# it only checked top-level locks, not the nested partition locks acquired during cross-topic
# transactions. The OOM killer then terminated the broker because the backed-up message queue
# exhausted memory.

broker_logs.append(f'{make_log_ts(-300)} INFO  [txn-coordinator] Transaction TXN-8834721 started by inventory-tracker for cross-topic commit [inventory-1, orders-2]')
broker_logs.append(f'{make_log_ts(-295)} DEBUG [lock-manager] Acquired write lock on inventory-1 for TXN-8834721')
broker_logs.append(f'{make_log_ts(-294)} DEBUG [lock-manager] Acquired write lock on orders-2 for TXN-8834721')
broker_logs.append(f'{make_log_ts(-280)} WARN  [txn-coordinator] Transaction TXN-8834721 holding locks for >10s, inventory-tracker consumer appears stalled')
broker_logs.append(f'{make_log_ts(-270)} INFO  [txn-coordinator] Transaction TXN-8834755 started by payment-gateway for cross-topic commit [payments-0, orders-2]')
broker_logs.append(f'{make_log_ts(-269)} DEBUG [lock-manager] Acquired write lock on payments-0 for TXN-8834755')
broker_logs.append(f'{make_log_ts(-268)} DEBUG [lock-manager] Waiting for write lock on orders-2 for TXN-8834755 (held by TXN-8834721)')
broker_logs.append(f'{make_log_ts(-250)} WARN  [lock-manager] Lock wait timeout approaching for TXN-8834755 on orders-2 (waited 18s)')
broker_logs.append(f'{make_log_ts(-240)} ERROR [deadlock-detector] Potential deadlock detected but classified as FALSE POSITIVE: TXN-8834721 (inventory-tracker) and TXN-8834755 (payment-gateway) - reason: different consumer groups, no circular dependency at group level')
broker_logs.append(f'{make_log_ts(-240)} DEBUG [deadlock-detector] Note: nested partition-level lock analysis skipped (feature flag partition_lock_analysis=false)')

# Red herring: unrelated Redis connection issue
broker_logs.append(f'{make_log_ts(-235)} WARN  [cache-layer] Redis connection pool exhausted, falling back to local cache (this is expected during high load)')
broker_logs.append(f'{make_log_ts(-230)} INFO  [cache-layer] Redis connection restored')

broker_logs.append(f'{make_log_ts(-220)} ERROR [lock-manager] Lock wait TIMEOUT for TXN-8834755 on orders-2 after 48s')
broker_logs.append(f'{make_log_ts(-220)} ERROR [txn-coordinator] Transaction TXN-8834755 ABORTED due to lock timeout')
broker_logs.append(f'{make_log_ts(-218)} WARN  [txn-coordinator] Abort handler for TXN-8834755 failed to release all locks cleanly: payments-0 lock release returned EBUSY')
broker_logs.append(f'{make_log_ts(-215)} ERROR [broker-main] Message queue backing up: orders-2 backlog={random.randint(50000, 60000)} messages, payments-0 partially locked')
broker_logs.append(f'{make_log_ts(-200)} ERROR [broker-main] CRITICAL: Memory usage at 94% (7.52GB/8.00GB), message backlog growing')
broker_logs.append(f'{make_log_ts(-180)} ERROR [lock-manager] TXN-8834721 still holding locks after 120s - inventory-tracker appears to be in infinite retry loop')
broker_logs.append(f'{make_log_ts(-170)} WARN  [broker-main] Attempting forced lock release for TXN-8834721')
broker_logs.append(f'{make_log_ts(-168)} ERROR [lock-manager] Forced lock release FAILED for TXN-8834721: lock state corrupted, nested lock reference count mismatch (expected 1, got 3)')

# More red herrings
broker_logs.append(f'{make_log_ts(-165)} INFO  [metrics-reporter] Flushing metrics to Prometheus pushgateway')
broker_logs.append(f'{make_log_ts(-160)} WARN  [metrics-reporter] Prometheus pushgateway slow response (2340ms)')

broker_logs.append(f'{make_log_ts(-150)} ERROR [broker-main] CRITICAL: Memory usage at 98% (7.84GB/8.00GB)')
broker_logs.append(f'{make_log_ts(-120)} ERROR [broker-main] Out of memory: failed to allocate 4194304 bytes for message buffer')
broker_logs.append(f'{make_log_ts(-115)} ERROR [wal-writer] WAL flush failed for partitions: orders-0, orders-1, orders-2, payments-0, payments-1, inventory-0, inventory-1, notifications-0')
broker_logs.append(f'{make_log_ts(-115)} ERROR [wal-writer] Partial write detected on orders-2: wrote 847 of 2048 bytes')
broker_logs.append(f'{make_log_ts(-114)} ERROR [wal-writer] Partial write detected on payments-0: wrote 1203 of 1536 bytes')
broker_logs.append(f'{make_log_ts(-110)} FATAL [broker-main] Unrecoverable error: WAL integrity compromised, initiating emergency shutdown')
broker_logs.append(f'{make_log_ts(-108)} INFO  [broker-main] Emergency shutdown: flushing consumer offsets...')
broker_logs.append(f'{make_log_ts(-107)} ERROR [broker-main] Emergency shutdown: offset flush FAILED for inventory-tracker (connection refused)')
broker_logs.append(f'{make_log_ts(-105)} INFO  [broker-main] Emergency shutdown: closing WAL files...')
broker_logs.append(f'{make_log_ts(-103)} INFO  [broker-main] Broker process exiting with code 137 (OOM killed)')

with open(os.path.join(LOGS_DIR, "mq-broker.log"), 'w') as f:
    f.write('\n'.join(broker_logs) + '\n')

# System logs (dmesg-style)
system_logs = []
for i in range(-7200, -400, random.randint(30, 120)):
    system_logs.append(f'[{CRASH_TIME_S + i}.{random.randint(100000, 999999)}] audit: type=1400 msg=audit({CRASH_TIME_S + i}.{random.randint(100, 999)}): apparmor="STATUS" operation="profile_load" name="mq-broker"')

system_logs.append(f'[{CRASH_TIME_S - 152}.482913] mq-broker invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0, oom_score_adj=0')
system_logs.append(f'[{CRASH_TIME_S - 152}.482920] CPU: 2 PID: 28401 Comm: mq-broker Not tainted 5.15.0-91-generic #101-Ubuntu')
system_logs.append(f'[{CRASH_TIME_S - 152}.482925] Hardware name: QEMU Standard PC (Q35 + ICH9, 2009)')
system_logs.append(f'[{CRASH_TIME_S - 152}.482930] Call Trace:')
system_logs.append(f'[{CRASH_TIME_S - 152}.482933]  dump_stack_lvl+0x44/0x5c')
system_logs.append(f'[{CRASH_TIME_S - 152}.482937]  dump_header+0x4a/0x1fc')
system_logs.append(f'[{CRASH_TIME_S - 152}.482940]  oom_kill_process.cold+0xb/0x10')
system_logs.append(f'[{CRASH_TIME_S - 152}.482945]  out_of_memory+0x106/0x2e0')
system_logs.append(f'[{CRASH_TIME_S - 152}.482950]  mem_cgroup_out_of_memory+0x138/0x158')
system_logs.append(f'[{CRASH_TIME_S - 152}.482960] Memory cgroup out of memory: Killed process 28401 (mq-broker) total-vm:8503216kB, anon-rss:7987456kB, file-rss:3892kB')
system_logs.append(f'[{CRASH_TIME_S - 150}.123456] oom_reaper: reaped process 28401 (mq-broker), now anon-rss:0kB, file-rss:0kB, shmem-rss:0kB')

# Also add some unrelated system noise
system_logs.append(f'[{CRASH_TIME_S - 148}.654321] USB 1-1: USB disconnect, device number 3')
system_logs.append(f'[{CRASH_TIME_S - 145}.111222] EXT4-fs (sda1): re-mounted. Opts: errors=remount-ro')

# Red herring: an unrelated NTP warning
system_logs.append(f'[{CRASH_TIME_S - 100}.999888] ntpd[1234]: time correction of -0.034s applied')

with open(os.path.join(LOGS_DIR, "system.log"), 'w') as f:
    f.write('\n'.join(system_logs) + '\n')

# Inventory-tracker service logs (the problematic consumer)
inv_logs = []
for i in range(-3600, -310, random.randint(8, 20)):
    inv_logs.append(f'{make_log_ts(i)} INFO  [consumer] Consumed batch of {random.randint(5, 30)} messages from inventory-1')
    if random.random() < 0.08:
        inv_logs.append(f'{make_log_ts(i)} WARN  [consumer] Slow message processing: {random.randint(500, 3000)}ms for batch')

# The bug: infinite retry loop on cross-topic transaction
inv_logs.append(f'{make_log_ts(-305)} INFO  [consumer] Starting cross-topic transaction for inventory adjustment ORD-{random.randint(10000, 99999)}')
inv_logs.append(f'{make_log_ts(-300)} INFO  [txn-handler] Acquired partition locks for cross-topic write [inventory-1, orders-2]')
inv_logs.append(f'{make_log_ts(-298)} ERROR [txn-handler] Failed to write to orders-2: partition leader changed during transaction')
inv_logs.append(f'{make_log_ts(-297)} INFO  [txn-handler] Retrying transaction write (attempt 1/infinite, retry_policy=AGGRESSIVE)')
inv_logs.append(f'{make_log_ts(-290)} ERROR [txn-handler] Failed to write to orders-2: partition leader changed during transaction')
inv_logs.append(f'{make_log_ts(-289)} INFO  [txn-handler] Retrying transaction write (attempt 2/infinite, retry_policy=AGGRESSIVE)')

for attempt in range(3, 50):
    offset = -289 + (attempt * 2)
    if offset >= -110:
        break
    inv_logs.append(f'{make_log_ts(offset)} ERROR [txn-handler] Failed to write to orders-2: partition leader changed during transaction')
    inv_logs.append(f'{make_log_ts(offset+1)} INFO  [txn-handler] Retrying transaction write (attempt {attempt}/infinite, retry_policy=AGGRESSIVE)')

inv_logs.append(f'{make_log_ts(-108)} FATAL [consumer] Connection to broker lost: EOF')
inv_logs.append(f'{make_log_ts(-107)} ERROR [consumer] Consumer shutting down due to broker disconnect')

with open(os.path.join(LOGS_DIR, "inventory-tracker.log"), 'w') as f:
    f.write('\n'.join(inv_logs) + '\n')

# Payment gateway logs (victim of the deadlock)
pay_logs = []
for i in range(-3600, -280, random.randint(5, 15)):
    pay_logs.append(f'{make_log_ts(i)} INFO  [gateway] Processed payment PAY-{random.randint(100000, 999999)}: {random.choice(["completed", "completed", "completed", "pending"])}')

pay_logs.append(f'{make_log_ts(-270)} INFO  [gateway] Initiating cross-topic transaction for payment reconciliation')
pay_logs.append(f'{make_log_ts(-268)} WARN  [gateway] Waiting for partition lock on orders-2 (held by another transaction)')
pay_logs.append(f'{make_log_ts(-250)} WARN  [gateway] Still waiting for partition lock on orders-2 (18s elapsed)')
pay_logs.append(f'{make_log_ts(-220)} ERROR [gateway] Transaction TXN-8834755 aborted: lock acquisition timeout')
pay_logs.append(f'{make_log_ts(-219)} ERROR [gateway] Failed to cleanly release lock on payments-0: EBUSY')
pay_logs.append(f'{make_log_ts(-218)} WARN  [gateway] Entering degraded mode: read-only until locks are cleared')
pay_logs.append(f'{make_log_ts(-108)} FATAL [gateway] Lost connection to broker')

with open(os.path.join(LOGS_DIR, "payment-gateway.log"), 'w') as f:
    f.write('\n'.join(pay_logs) + '\n')

# ============================================================
# Metric snapshots (JSON time-series)
# ============================================================

metrics = []
for i in range(-3600, 0, 10):
    ts = CRASH_TIME_S + i
    msg_rate = random.randint(100, 500) if i < -300 else max(10, int(500 * (1 + i/300)))
    memory_pct = 45 + random.uniform(-5, 5) if i < -300 else min(99, 45 + (300 + i) * 0.18 + random.uniform(-2, 2))
    lock_wait = random.uniform(0, 5) if i < -300 else random.uniform(5, 60) if i < -200 else random.uniform(30, 120)

    metrics.append({
        "timestamp": ts,
        "broker_messages_per_sec": msg_rate,
        "broker_memory_pct": round(memory_pct, 1),
        "broker_active_transactions": random.randint(2, 8) if i < -300 else random.randint(8, 25),
        "broker_lock_wait_ms": round(lock_wait, 1),
        "broker_wal_flush_errors": 0 if i < -120 else random.randint(1, 10),
        "consumer_lag_orders": random.randint(0, 100) if i < -300 else random.randint(100, 50000),
        "consumer_lag_payments": random.randint(0, 50) if i < -270 else random.randint(50, 30000),
    })

with open(os.path.join(METRICS_DIR, "broker-metrics.json"), 'w') as f:
    json.dump(metrics, f, indent=2)

# ============================================================
# Configuration files
# ============================================================

broker_config = {
    "broker": {
        "id": "broker-1",
        "listen_addr": "0.0.0.0:9092",
        "data_dir": "/app/mqdata/wal",
        "index_dir": "/app/mqdata/index",
        "max_memory_gb": 8.0,
        "wal_sync_mode": "async",
        "wal_flush_interval_ms": 1000,
        "max_message_size_bytes": 1048576
    },
    "transactions": {
        "enabled": True,
        "max_transaction_timeout_s": 60,
        "deadlock_detection": True,
        "deadlock_check_interval_s": 5,
        "partition_lock_analysis": False,  # <-- THE BUG CONFIG
        "max_lock_wait_s": 50
    },
    "consumers": {
        "heartbeat_interval_s": 10,
        "session_timeout_s": 30,
        "max_poll_interval_s": 300,
        "offset_commit_interval_s": 5
    },
    "topics": {
        "orders": {"partitions": 3, "replication_factor": 1, "retention_hours": 168},
        "payments": {"partitions": 2, "replication_factor": 1, "retention_hours": 720},
        "inventory": {"partitions": 2, "replication_factor": 1, "retention_hours": 168},
        "notifications": {"partitions": 1, "replication_factor": 1, "retention_hours": 24}
    }
}

with open(os.path.join(CONFIG_DIR, "broker.json"), 'w') as f:
    json.dump(broker_config, f, indent=2)

consumer_configs = {
    "order-processor": {"group_id": "order-processor", "topics": ["orders"], "auto_commit": True, "retry_policy": "exponential_backoff", "max_retries": 5},
    "payment-gateway": {"group_id": "payment-gateway", "topics": ["payments"], "auto_commit": True, "retry_policy": "exponential_backoff", "max_retries": 3},
    "inventory-tracker": {"group_id": "inventory-tracker", "topics": ["inventory", "orders"], "auto_commit": False, "retry_policy": "aggressive_infinite", "max_retries": -1},
    "notification-sender": {"group_id": "notification-sender", "topics": ["notifications"], "auto_commit": True, "retry_policy": "exponential_backoff", "max_retries": 5},
    "analytics-pipeline": {"group_id": "analytics-pipeline", "topics": ["orders", "payments"], "auto_commit": True, "retry_policy": "exponential_backoff", "max_retries": 5},
}

with open(os.path.join(CONFIG_DIR, "consumers.json"), 'w') as f:
    json.dump(consumer_configs, f, indent=2)

# ============================================================
# Save metadata for test verification (hidden from agent)
# This will be used by tests but deleted before agent sees it
# ============================================================

verification_data = {
    "crash_time_utc": "2024-03-31T00:00:00Z",
    "crash_time_us": CRASH_TIME_US,
    "root_cause_chain": [
        "inventory-tracker entered infinite retry loop due to aggressive_infinite retry policy",
        "TXN-8834721 held write locks on inventory-1 and orders-2 indefinitely",
        "payment-gateway TXN-8834755 blocked waiting for orders-2 lock",
        "deadlock detector falsely classified as no circular dependency (partition_lock_analysis=false)",
        "message backlog grew unbounded exhausting broker memory",
        "OOM killer terminated broker process (PID 28401)",
        "WAL writes were partial/corrupted during emergency shutdown"
    ],
    "root_cause_config": "transactions.partition_lock_analysis=false in broker.json",
    "root_cause_consumer": "inventory-tracker with retry_policy=aggressive_infinite",
    "affected_transactions": ["TXN-8834721", "TXN-8834755"],
    "valid_message_counts": {},
    "total_valid_messages": 0,
    "corrupted_partitions": list(crash_info.keys()),
    "consumer_states": {name: cfg["status"] for name, cfg in consumers.items()},
    "stale_consumer": "analytics-pipeline",
    "crashed_consumer": "inventory-tracker",
    "orphaned_lock": "inventory-tracker/.lock"
}

total = 0
for topic, parts in all_valid_messages.items():
    verification_data["valid_message_counts"][topic] = {}
    for part, msgs in parts.items():
        verification_data["valid_message_counts"][topic][str(part)] = len(msgs)
        total += len(msgs)

verification_data["total_valid_messages"] = total

# Write verification data to a temp location (will be moved to /tests/ at build time)
with open("/tmp/verification_data.json", 'w') as f:
    json.dump(verification_data, f, indent=2)

print(f"Generated scenario data in {BASE}")
print(f"Total valid messages: {total}")
print(f"Corrupted partitions: {list(crash_info.keys())}")
print(f"Topics: {list(TOPICS.keys())}")
for topic, parts in all_valid_messages.items():
    for part, msgs in parts.items():
        print(f"  {topic}-{part}: {len(msgs)} valid messages")
