#!/usr/bin/env python3
"""
Tests for MQ WAL Crash Recovery & Forensics task.
All expected values are computed independently from the raw WAL/log/config files.
"""

import json
import os
import struct
import zlib
import re
import glob
import pytest

OUTPUT_DIR = "/app/output"
MQDATA = "/app/mqdata"

WAL_MAGIC = 0x4D514C47


# ============================================================
# Helper: independently parse WAL files to compute ground truth
# ============================================================

def independently_parse_wal(filepath):
    """Parse a WAL file independently to compute expected values."""
    valid_messages = []
    last_valid_seq = None
    has_corruption = False

    with open(filepath, 'rb') as f:
        header = f.read(16)
        if len(header) < 16:
            return [], None, True

        magic = struct.unpack('<I', header[0:4])[0]
        if magic != WAL_MAGIC:
            return [], None, True

        partition = struct.unpack('<H', header[10:12])[0]
        basename = os.path.basename(filepath).rsplit('.', 1)[0]
        topic_name = basename.rsplit('-', 1)[0]

        while True:
            rl_bytes = f.read(4)
            if len(rl_bytes) == 0:
                break
            if len(rl_bytes) < 4:
                has_corruption = True
                break

            record_len = struct.unpack('<I', rl_bytes)[0]
            if record_len < 27 or record_len > 10_000_000:
                has_corruption = True
                break

            remaining = record_len - 4
            data = f.read(remaining)
            if len(data) < remaining:
                has_corruption = True
                break

            payload = data[:-4]
            crc_stored = struct.unpack('<I', data[-4:])[0]
            crc_calc = zlib.crc32(payload) & 0xFFFFFFFF

            if crc_stored != crc_calc:
                has_corruption = True
                continue

            try:
                off = 0
                seq = struct.unpack('<Q', payload[off:off+8])[0]; off += 8
                ts = struct.unpack('<Q', payload[off:off+8])[0]; off += 8
                kl = struct.unpack('<H', payload[off:off+2])[0]; off += 2
                key = payload[off:off+kl].decode(); off += kl
                vl = struct.unpack('<I', payload[off:off+4])[0]; off += 4
                val = payload[off:off+vl].decode(); off += vl
                flags = payload[off]

                valid_messages.append({
                    "topic": topic_name,
                    "partition": partition,
                    "sequence": seq,
                    "timestamp_us": ts,
                    "key": key,
                    "flags": flags
                })
                last_valid_seq = seq
            except Exception:
                has_corruption = True
                continue

    return valid_messages, last_valid_seq, has_corruption


def get_all_expected():
    """Parse all WAL files to get expected results."""
    all_msgs = []
    corruption = {}
    wal_dir = os.path.join(MQDATA, "wal")
    for wf in sorted(glob.glob(os.path.join(wal_dir, "*.wal"))):
        bn = os.path.basename(wf).rsplit('.', 1)[0]
        msgs, last_seq, has_corr = independently_parse_wal(wf)
        all_msgs.extend(msgs)
        if has_corr:
            corruption[bn] = last_seq
    all_msgs.sort(key=lambda m: m["sequence"])
    return all_msgs, corruption


# ============================================================
# Test 1: recovered_messages.json exists and is valid JSON
# ============================================================

class TestRecoveredMessages:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.path = os.path.join(OUTPUT_DIR, "recovered_messages.json")
        self.expected_msgs, self.expected_corruption = get_all_expected()

    def test_file_exists(self):
        assert os.path.exists(self.path), "recovered_messages.json must exist"

    def test_valid_json(self):
        with open(self.path) as f:
            data = json.load(f)
        assert isinstance(data, list), "recovered_messages.json must be a JSON array"

    def test_correct_message_count(self):
        """Total recovered messages must match independently parsed count."""
        with open(self.path) as f:
            data = json.load(f)
        expected_count = len(self.expected_msgs)
        actual_count = len(data)
        # Allow a small tolerance (agent may parse slightly differently near corruption)
        assert abs(actual_count - expected_count) <= 5, \
            f"Expected ~{expected_count} valid messages, got {actual_count}"

    def test_message_structure(self):
        """Each message must have the required fields."""
        with open(self.path) as f:
            data = json.load(f)
        required_fields = {"topic", "partition", "sequence", "timestamp_us", "key", "value", "flags"}
        for i, msg in enumerate(data[:10]):  # Check first 10
            missing = required_fields - set(msg.keys())
            assert not missing, f"Message {i} missing fields: {missing}"

    def test_sorted_by_sequence(self):
        """Messages must be sorted by sequence number."""
        with open(self.path) as f:
            data = json.load(f)
        seqs = [m["sequence"] for m in data]
        assert seqs == sorted(seqs), "Messages must be sorted by sequence number"

    def test_all_topics_present(self):
        """All 4 topics must have recovered messages."""
        with open(self.path) as f:
            data = json.load(f)
        topics = set(m["topic"] for m in data)
        expected_topics = {"orders", "payments", "inventory", "notifications"}
        assert topics == expected_topics, f"Expected topics {expected_topics}, got {topics}"

    def test_per_partition_counts(self):
        """Per-partition message counts should be approximately correct."""
        with open(self.path) as f:
            data = json.load(f)

        # Group expected by topic-partition
        expected_counts = {}
        for m in self.expected_msgs:
            key = f"{m['topic']}-{m['partition']}"
            expected_counts[key] = expected_counts.get(key, 0) + 1

        actual_counts = {}
        for m in data:
            key = f"{m['topic']}-{m['partition']}"
            actual_counts[key] = actual_counts.get(key, 0) + 1

        for part_key, expected_n in expected_counts.items():
            actual_n = actual_counts.get(part_key, 0)
            assert abs(actual_n - expected_n) <= 3, \
                f"Partition {part_key}: expected ~{expected_n}, got {actual_n}"

    def test_values_are_parsed_json(self):
        """Message values should be parsed JSON objects, not raw strings."""
        with open(self.path) as f:
            data = json.load(f)
        # Check a sample of messages
        dict_count = sum(1 for m in data[:50] if isinstance(m.get("value"), dict))
        assert dict_count >= 45, \
            f"Most message values should be parsed JSON dicts, found {dict_count}/50"

    def test_no_corrupt_messages_included(self):
        """Messages with bad CRC should not be in the output."""
        with open(self.path) as f:
            data = json.load(f)
        # Build set of valid sequences from independent parse
        valid_seqs = set(m["sequence"] for m in self.expected_msgs)
        for msg in data:
            assert msg["sequence"] in valid_seqs, \
                f"Message seq={msg['sequence']} should not be in output (failed CRC)"


# ============================================================
# Test 2: corruption_report.json
# ============================================================

class TestCorruptionReport:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.path = os.path.join(OUTPUT_DIR, "corruption_report.json")
        _, self.expected_corruption = get_all_expected()

    def test_file_exists(self):
        assert os.path.exists(self.path), "corruption_report.json must exist"

    def test_valid_json(self):
        with open(self.path) as f:
            data = json.load(f)
        assert isinstance(data, dict), "corruption_report.json must be a JSON object"

    def test_correct_corrupted_partitions(self):
        """Must identify all corrupted partitions (all 8 have corruption)."""
        with open(self.path) as f:
            data = json.load(f)
        expected_parts = set(self.expected_corruption.keys())
        actual_parts = set(data.keys())
        # Must identify at least 6 of 8 corrupted partitions
        overlap = expected_parts & actual_parts
        assert len(overlap) >= 6, \
            f"Expected corrupted partitions {expected_parts}, got {actual_parts}, overlap={overlap}"

    def test_last_valid_seq_accuracy(self):
        """Last valid sequence numbers must be correct for identified partitions."""
        with open(self.path) as f:
            data = json.load(f)
        for part_key, expected_last_seq in self.expected_corruption.items():
            if part_key in data:
                entry = data[part_key]
                # Handle different key names the agent might use
                actual_last_seq = entry.get("last_valid_seq") or entry.get("last_valid_sequence")
                if actual_last_seq is not None and expected_last_seq is not None:
                    assert actual_last_seq == expected_last_seq, \
                        f"Partition {part_key}: expected last_valid_seq={expected_last_seq}, got {actual_last_seq}"


# ============================================================
# Test 3: rca_report.json - Root Cause Analysis
# ============================================================

class TestRCAReport:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.path = os.path.join(OUTPUT_DIR, "rca_report.json")

    def test_file_exists(self):
        assert os.path.exists(self.path), "rca_report.json must exist"

    def test_valid_json(self):
        with open(self.path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_required_fields(self):
        with open(self.path) as f:
            data = json.load(f)
        required = [
            "root_cause_summary", "trigger_service", "trigger_transaction",
            "deadlock_transaction", "config_bug", "consumer_bug",
            "crash_pid", "timeline"
        ]
        for field in required:
            assert field in data, f"Missing required field: {field}"

    def test_trigger_service(self):
        """Must correctly identify inventory-tracker as the trigger."""
        with open(self.path) as f:
            data = json.load(f)
        trigger = data.get("trigger_service", "").lower()
        assert "inventory" in trigger, \
            f"Trigger service should be inventory-tracker, got '{data.get('trigger_service')}'"

    def test_trigger_transaction(self):
        """Must identify TXN-8834721 as the trigger transaction."""
        with open(self.path) as f:
            data = json.load(f)
        txn = data.get("trigger_transaction", "")
        assert "8834721" in str(txn), \
            f"Trigger transaction should be TXN-8834721, got '{txn}'"

    def test_deadlock_transaction(self):
        """Must identify TXN-8834755 as the deadlocked transaction."""
        with open(self.path) as f:
            data = json.load(f)
        txn = data.get("deadlock_transaction", "")
        assert "8834755" in str(txn), \
            f"Deadlock transaction should be TXN-8834755, got '{txn}'"

    def test_config_bug_identified(self):
        """Must identify partition_lock_analysis=false as the config bug."""
        with open(self.path) as f:
            data = json.load(f)
        config_bug = data.get("config_bug", "").lower()
        assert "partition_lock_analysis" in config_bug, \
            f"Config bug should mention partition_lock_analysis, got '{data.get('config_bug')}'"
        assert "false" in config_bug, \
            f"Config bug should indicate false value, got '{data.get('config_bug')}'"

    def test_consumer_bug_identified(self):
        """Must identify inventory-tracker's aggressive retry policy."""
        with open(self.path) as f:
            data = json.load(f)
        bug = data.get("consumer_bug", "").lower()
        assert "inventory" in bug or "aggressive" in bug or "infinite" in bug, \
            f"Consumer bug should mention inventory-tracker or aggressive/infinite retry, got '{data.get('consumer_bug')}'"

    def test_crash_pid(self):
        """Must correctly identify the OOM-killed PID from system logs."""
        with open(self.path) as f:
            data = json.load(f)
        # Independently extract from system log
        with open(os.path.join(MQDATA, "logs", "system.log")) as sl:
            syslog = sl.read()
        pid_match = re.search(r'Killed process (\d+) \(mq-broker\)', syslog)
        expected_pid = int(pid_match.group(1))
        assert data.get("crash_pid") == expected_pid, \
            f"Crash PID should be {expected_pid}, got {data.get('crash_pid')}"

    def test_timeline_minimum_events(self):
        """Timeline must have at least 8 events."""
        with open(self.path) as f:
            data = json.load(f)
        timeline = data.get("timeline", [])
        assert len(timeline) >= 8, \
            f"Timeline should have >= 8 events, got {len(timeline)}"

    def test_timeline_structure(self):
        """Each timeline event must have timestamp and event fields."""
        with open(self.path) as f:
            data = json.load(f)
        for i, event in enumerate(data.get("timeline", [])):
            assert "timestamp" in event, f"Timeline event {i} missing 'timestamp'"
            assert "event" in event, f"Timeline event {i} missing 'event'"

    def test_root_cause_summary_comprehensiveness(self):
        """Root cause summary must mention key components."""
        with open(self.path) as f:
            data = json.load(f)
        summary = data.get("root_cause_summary", "").lower()
        # Must mention the key players
        checks = [
            ("inventory", "inventory-tracker service"),
            ("deadlock" if "deadlock" in summary else "lock", "lock/deadlock"),
            ("oom" if "oom" in summary else "memory", "OOM/memory exhaustion"),
            ("wal" if "wal" in summary else "corrupt", "WAL corruption"),
        ]
        for keyword, description in checks:
            assert keyword in summary, \
                f"Root cause summary should mention {description}"


# ============================================================
# Test 4: consumer_audit.json
# ============================================================

class TestConsumerAudit:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.path = os.path.join(OUTPUT_DIR, "consumer_audit.json")

    def test_file_exists(self):
        assert os.path.exists(self.path), "consumer_audit.json must exist"

    def test_valid_json(self):
        with open(self.path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_all_consumers_present(self):
        """Must audit all 6 consumers."""
        with open(self.path) as f:
            data = json.load(f)
        # Get consumer names from offsets directory
        offsets_dir = os.path.join(MQDATA, "offsets")
        expected_consumers = set(
            d for d in os.listdir(offsets_dir)
            if os.path.isdir(os.path.join(offsets_dir, d))
        )
        actual_consumers = set(data.keys())
        assert actual_consumers == expected_consumers, \
            f"Expected consumers {expected_consumers}, got {actual_consumers}"

    def test_consumer_status_types(self):
        """Each consumer must have a status field."""
        with open(self.path) as f:
            data = json.load(f)
        valid_statuses = {"active", "crashed", "orphaned", "decommissioned", "unknown"}
        for name, info in data.items():
            assert "status" in info, f"Consumer {name} missing 'status'"
            assert info["status"] in valid_statuses, \
                f"Consumer {name} has invalid status: {info['status']}"

    def test_inventory_tracker_crashed(self):
        """inventory-tracker should be identified as crashed."""
        with open(self.path) as f:
            data = json.load(f)
        assert data.get("inventory-tracker", {}).get("status") == "crashed", \
            "inventory-tracker should have status 'crashed'"

    def test_inventory_tracker_has_lock(self):
        """inventory-tracker should be flagged with a stale lock."""
        with open(self.path) as f:
            data = json.load(f)
        assert data.get("inventory-tracker", {}).get("has_stale_lock") is True, \
            "inventory-tracker should have has_stale_lock=true"

    def test_analytics_pipeline_orphaned(self):
        """analytics-pipeline should be identified as orphaned."""
        with open(self.path) as f:
            data = json.load(f)
        status = data.get("analytics-pipeline", {}).get("status", "")
        assert status == "orphaned", \
            f"analytics-pipeline should have status 'orphaned', got '{status}'"

    def test_consumer_has_topics(self):
        """Each consumer must list its subscribed topics."""
        with open(self.path) as f:
            data = json.load(f)
        for name, info in data.items():
            assert "topics" in info, f"Consumer {name} missing 'topics'"
            assert isinstance(info["topics"], list), \
                f"Consumer {name} 'topics' should be a list"
            assert len(info["topics"]) > 0, \
                f"Consumer {name} should have at least one topic"

    def test_consumer_lag_is_numeric(self):
        """Each consumer must have a numeric total_lag."""
        with open(self.path) as f:
            data = json.load(f)
        for name, info in data.items():
            assert "total_lag" in info, f"Consumer {name} missing 'total_lag'"
            assert isinstance(info["total_lag"], (int, float)), \
                f"Consumer {name} total_lag should be numeric, got {type(info['total_lag'])}"

    def test_orphaned_consumer_has_high_lag(self):
        """Orphaned/decommissioned consumers should have higher lag than active ones."""
        with open(self.path) as f:
            data = json.load(f)
        active_lags = [info["total_lag"] for name, info in data.items()
                       if info.get("status") == "active"]
        orphaned_lags = [info["total_lag"] for name, info in data.items()
                         if info.get("status") in ("orphaned", "decommissioned")]
        if active_lags and orphaned_lags:
            avg_active = sum(active_lags) / len(active_lags)
            avg_orphaned = sum(orphaned_lags) / len(orphaned_lags)
            assert avg_orphaned > avg_active, \
                f"Orphaned consumers should have higher lag ({avg_orphaned}) than active ({avg_active})"

    def test_legacy_exporter_decommissioned(self):
        """legacy-exporter should be identified as decommissioned."""
        with open(self.path) as f:
            data = json.load(f)
        status = data.get("legacy-exporter", {}).get("status", "")
        assert status == "decommissioned", \
            f"legacy-exporter should have status 'decommissioned', got '{status}'"
