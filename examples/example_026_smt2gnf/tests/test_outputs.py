"""
Tests for ETL Pipeline Corruption Forensics and Recovery task.

These tests verify the solution by recomputing expected values from the
raw evidence data, ensuring no answer leakage.
"""

import json
import hashlib
import os
import re
import subprocess
from datetime import datetime

EVIDENCE_DIR = "/app/evidence"
OUTPUT_DIR = "/app/output"


# ============================================================
# Helper functions - recompute expected values from evidence
# ============================================================

def load_fx_rates():
    with open(f"{EVIDENCE_DIR}/fx_rates.json") as f:
        return json.load(f)


def load_ingested_records():
    records = []
    with open(f"{EVIDENCE_DIR}/staging_area/stage_ingest.jsonl") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def load_loaded_records():
    records = {}
    with open(f"{EVIDENCE_DIR}/staging_area/stage_load.jsonl") as f:
        for line in f:
            r = json.loads(line)
            records[r["record_id"]] = r
    return records


def compute_risk_score(amount, record_id):
    return (int(amount * 7) + record_id * 13) % 100


def compute_checksum(record_id, amount, currency, risk_score):
    s = f"{record_id}:{amount:.2f}:{currency}:{risk_score}"
    return hashlib.md5(s.encode()).hexdigest()


def compute_expected_corrupted_ids():
    """Recompute which records are corrupted from the raw evidence."""
    fx_rates = load_fx_rates()
    ingested = load_ingested_records()
    loaded = load_loaded_records()

    corrupted = []
    valid_count = 0
    for r in ingested:
        if r["amount"] <= 0:
            continue
        valid_count += 1

        rid = r["record_id"]
        risk_score = compute_risk_score(r["amount"], rid)
        rate = fx_rates[r["currency"]]
        correct_amount = round(r["amount"] * rate, 2)
        expected_checksum = compute_checksum(rid, correct_amount, "USD", risk_score)

        if rid in loaded and loaded[rid]["checksum"] != expected_checksum:
            corrupted.append(rid)

    corrupted.sort()
    return corrupted, valid_count


# ============================================================
# Test 1: Timeline file exists and has correct structure
# ============================================================

class TestTimeline:
    def test_timeline_exists(self):
        assert os.path.exists(f"{OUTPUT_DIR}/timeline.jsonl"), \
            "timeline.jsonl must exist in /app/output/"

    def test_timeline_structure(self):
        events = []
        with open(f"{OUTPUT_DIR}/timeline.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                events.append(ev)

        assert len(events) >= 10, \
            f"Timeline should have at least 10 events, got {len(events)}"

        required_fields = {"timestamp", "run_id", "stage", "event", "details"}
        for ev in events:
            assert required_fields.issubset(set(ev.keys())), \
                f"Event missing required fields: {required_fields - set(ev.keys())}"

    def test_timeline_sorted(self):
        events = []
        with open(f"{OUTPUT_DIR}/timeline.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))

        timestamps = [ev["timestamp"] for ev in events]
        assert timestamps == sorted(timestamps), \
            "Timeline events must be sorted by timestamp"

    def test_timeline_has_both_runs(self):
        events = []
        with open(f"{OUTPUT_DIR}/timeline.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))

        run_ids = set(ev["run_id"] for ev in events)
        assert "A" in run_ids, "Timeline must contain events for run A"
        assert "B" in run_ids, "Timeline must contain events for run B"

    def test_timeline_has_conflict_events(self):
        events = []
        with open(f"{OUTPUT_DIR}/timeline.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))

        conflict_events = [ev for ev in events if ev["event"] == "conflict"]
        assert len(conflict_events) >= 1, \
            "Timeline must contain at least one conflict event"

    def test_timeline_valid_event_types(self):
        valid_events = {"start", "complete", "error", "conflict"}
        events = []
        with open(f"{OUTPUT_DIR}/timeline.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))

        for ev in events:
            assert ev["event"] in valid_events, \
                f"Invalid event type: {ev['event']}, must be one of {valid_events}"


# ============================================================
# Test 2: Corrupted records identification
# ============================================================

class TestCorruptedRecords:
    def test_corrupted_records_exists(self):
        assert os.path.exists(f"{OUTPUT_DIR}/corrupted_records.json"), \
            "corrupted_records.json must exist in /app/output/"

    def test_corrupted_records_structure(self):
        with open(f"{OUTPUT_DIR}/corrupted_records.json") as f:
            data = json.load(f)

        required_keys = {
            "total_records_processed",
            "corrupted_record_ids",
            "corruption_stage",
            "corruption_mechanism"
        }
        assert required_keys.issubset(set(data.keys())), \
            f"Missing required keys: {required_keys - set(data.keys())}"

        assert isinstance(data["total_records_processed"], int)
        assert isinstance(data["corrupted_record_ids"], list)
        assert isinstance(data["corruption_stage"], str)
        assert isinstance(data["corruption_mechanism"], str)

    def test_total_records_count(self):
        with open(f"{OUTPUT_DIR}/corrupted_records.json") as f:
            data = json.load(f)

        _, expected_valid = compute_expected_corrupted_ids()
        assert data["total_records_processed"] == expected_valid, \
            f"Expected {expected_valid} total valid records, got {data['total_records_processed']}"

    def test_corrupted_ids_correct(self):
        """Core test: verify the exact set of corrupted record IDs."""
        with open(f"{OUTPUT_DIR}/corrupted_records.json") as f:
            data = json.load(f)

        expected_ids, _ = compute_expected_corrupted_ids()
        actual_ids = sorted(data["corrupted_record_ids"])

        assert actual_ids == expected_ids, \
            f"Corrupted IDs mismatch.\nExpected {len(expected_ids)} records: {expected_ids}\nGot {len(actual_ids)} records: {actual_ids}"

    def test_corrupted_ids_sorted(self):
        with open(f"{OUTPUT_DIR}/corrupted_records.json") as f:
            data = json.load(f)

        ids = data["corrupted_record_ids"]
        assert ids == sorted(ids), "corrupted_record_ids must be sorted ascending"

    def test_corruption_stage_is_transform(self):
        """The corruption manifests in the transform stage where wrong FX rates are applied."""
        with open(f"{OUTPUT_DIR}/corrupted_records.json") as f:
            data = json.load(f)

        assert data["corruption_stage"] == "transform", \
            f"Corruption stage should be 'transform', got '{data['corruption_stage']}'"

    def test_corruption_mechanism_mentions_key_concepts(self):
        with open(f"{OUTPUT_DIR}/corrupted_records.json") as f:
            data = json.load(f)

        mechanism = data["corruption_mechanism"].lower()
        # Must mention FX rates or exchange rates
        assert "rate" in mechanism or "fx" in mechanism or "exchange" in mechanism, \
            "Corruption mechanism must mention FX/exchange rates"


# ============================================================
# Test 3: RCA Report
# ============================================================

class TestRCAReport:
    def test_rca_report_exists(self):
        assert os.path.exists(f"{OUTPUT_DIR}/rca_report.md"), \
            "rca_report.md must exist in /app/output/"

    def test_rca_report_has_required_sections(self):
        with open(f"{OUTPUT_DIR}/rca_report.md") as f:
            content = f.read()

        required_sections = [
            "## Incident Summary",
            "## Timeline of Events",
            "## Root Cause",
            "## Impact Assessment",
            "## Corrective Actions"
        ]

        for section in required_sections:
            assert section in content, \
                f"RCA report missing required section: {section}"

    def test_rca_report_mentions_both_runs(self):
        with open(f"{OUTPUT_DIR}/rca_report.md") as f:
            content = f.read()

        assert "Run A" in content or "run A" in content or "run_id A" in content or "Run-A" in content, \
            "RCA report must reference Run A"
        assert "Run B" in content or "run B" in content or "run_id B" in content or "Run-B" in content, \
            "RCA report must reference Run B"

    def test_rca_report_mentions_corrupted_count(self):
        with open(f"{OUTPUT_DIR}/rca_report.md") as f:
            content = f.read()

        expected_ids, _ = compute_expected_corrupted_ids()
        count_str = str(len(expected_ids))
        assert count_str in content, \
            f"RCA report must mention the number of corrupted records ({count_str})"

    def test_rca_report_mentions_race_condition(self):
        with open(f"{OUTPUT_DIR}/rca_report.md") as f:
            content = f.read().lower()

        has_race = "race condition" in content or "concurrent" in content or "concurrency" in content
        assert has_race, "RCA report must discuss race condition or concurrency issue"


# ============================================================
# Test 4: Recovery Script and Recovered Records
# ============================================================

class TestRecovery:
    def test_reprocess_script_exists(self):
        assert os.path.exists(f"{OUTPUT_DIR}/reprocess.sh"), \
            "reprocess.sh must exist in /app/output/"

    def test_reprocess_script_is_executable(self):
        assert os.access(f"{OUTPUT_DIR}/reprocess.sh", os.X_OK), \
            "reprocess.sh must be executable"

    def test_reprocess_script_runs(self):
        """Run the reprocess script and verify it succeeds."""
        result = subprocess.run(
            ["bash", f"{OUTPUT_DIR}/reprocess.sh"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, \
            f"reprocess.sh failed with:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    def test_recovered_records_exist(self):
        assert os.path.exists(f"{OUTPUT_DIR}/recovered_records.jsonl"), \
            "recovered_records.jsonl must exist in /app/output/"

    def test_recovered_records_count(self):
        expected_ids, _ = compute_expected_corrupted_ids()

        records = []
        with open(f"{OUTPUT_DIR}/recovered_records.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))

        assert len(records) == len(expected_ids), \
            f"Expected {len(expected_ids)} recovered records, got {len(records)}"

    def test_recovered_records_structure(self):
        required_fields = {"record_id", "amount", "currency", "risk_score", "checksum"}
        with open(f"{OUTPUT_DIR}/recovered_records.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                assert required_fields.issubset(set(r.keys())), \
                    f"Record missing fields: {required_fields - set(r.keys())}"

    def test_recovered_records_correctness(self):
        """Verify each recovered record has correct values by recomputing from source."""
        fx_rates = load_fx_rates()
        ingested = {r["record_id"]: r for r in load_ingested_records()}
        expected_ids, _ = compute_expected_corrupted_ids()

        recovered = []
        with open(f"{OUTPUT_DIR}/recovered_records.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                recovered.append(json.loads(line))

        recovered_map = {r["record_id"]: r for r in recovered}

        for rid in expected_ids:
            assert rid in recovered_map, f"Missing recovered record for ID {rid}"

            orig = ingested[rid]
            rec = recovered_map[rid]

            # Verify risk_score
            expected_risk = compute_risk_score(orig["amount"], rid)
            assert rec["risk_score"] == expected_risk, \
                f"Record {rid}: expected risk_score {expected_risk}, got {rec['risk_score']}"

            # Verify amount (correct FX conversion)
            rate = fx_rates[orig["currency"]]
            expected_amount = round(orig["amount"] * rate, 2)
            assert abs(rec["amount"] - expected_amount) < 0.01, \
                f"Record {rid}: expected amount {expected_amount}, got {rec['amount']}"

            # Verify currency
            assert rec["currency"] == "USD", \
                f"Record {rid}: currency should be USD, got {rec['currency']}"

            # Verify checksum
            expected_cksum = compute_checksum(rid, expected_amount, "USD", expected_risk)
            assert rec["checksum"] == expected_cksum, \
                f"Record {rid}: checksum mismatch"

    def test_reprocess_idempotent(self):
        """Run reprocess.sh twice and verify output is identical."""
        # First run
        subprocess.run(["bash", f"{OUTPUT_DIR}/reprocess.sh"],
                       capture_output=True, timeout=30)
        with open(f"{OUTPUT_DIR}/recovered_records.jsonl") as f:
            first_output = f.read()

        # Second run
        subprocess.run(["bash", f"{OUTPUT_DIR}/reprocess.sh"],
                       capture_output=True, timeout=30)
        with open(f"{OUTPUT_DIR}/recovered_records.jsonl") as f:
            second_output = f.read()

        assert first_output == second_output, \
            "reprocess.sh must be idempotent - running twice should produce identical output"

    def test_recovered_only_corrupted_records(self):
        """Ensure only corrupted records are in recovered output, not clean ones."""
        expected_ids, _ = compute_expected_corrupted_ids()
        expected_set = set(expected_ids)

        with open(f"{OUTPUT_DIR}/recovered_records.jsonl") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                assert r["record_id"] in expected_set, \
                    f"Record {r['record_id']} should not be in recovered records (not corrupted)"
