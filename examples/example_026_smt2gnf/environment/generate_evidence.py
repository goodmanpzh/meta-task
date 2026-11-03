#!/usr/bin/env python3
"""
Generate realistic ETL pipeline forensic evidence for the incident scenario.

Scenario: Two pipeline runs (A and B) overlap. Run A is the scheduled run,
Run B is a manual run triggered by an operator. The race condition occurs
in the 'enrich' stage where both runs try to write to the same staging file.
Run B's enrich output partially overwrites Run A's, causing some records
to get incorrect fx_rate application in the transform stage (because Run B
used stale fx_rates that were updated between the two runs' enrich stages).

The actual corruption mechanism: During the transform stage, Run A's records
that were overwritten by Run B's enrich output get transformed with Run B's
context (which used a STALE fx_rates snapshot), producing wrong amounts.
"""

import json
import hashlib
import random
import os
import csv
from datetime import datetime, timedelta

random.seed(42)

EVIDENCE_DIR = "/app/evidence"
os.makedirs(f"{EVIDENCE_DIR}/staging_area", exist_ok=True)

# FX rates - the "current" rates that Run A should use
FX_RATES = {
    "USD": 1.0,
    "EUR": 1.0842,
    "GBP": 1.2651,
    "JPY": 0.00667,
    "CAD": 0.7412,
    "AUD": 0.6534,
    "CHF": 1.1203
}

# Stale fx rates - what Run B used (snapshot from previous day)
STALE_FX_RATES = {
    "USD": 1.0,
    "EUR": 1.0791,
    "GBP": 1.2598,
    "JPY": 0.00662,
    "CAD": 0.7389,
    "AUD": 0.6501,
    "CHF": 1.1178
}

# Write fx_rates.json (current rates only - agent must figure out stale rates exist)
with open(f"{EVIDENCE_DIR}/fx_rates.json", "w") as f:
    json.dump(FX_RATES, f, indent=2)

# Generate 200 transaction records
CURRENCIES = list(FX_RATES.keys())
records = []
for i in range(1, 201):
    currency = random.choice(CURRENCIES)
    amount = round(random.uniform(-50, 5000), 2)  # Some negative amounts to be filtered
    records.append({
        "record_id": i,
        "amount": amount,
        "currency": currency,
        "timestamp": f"2026-03-15T01:{random.randint(0,59):02d}:{random.randint(0,59):02d}.{random.randint(0,999):03d}Z",
        "source": random.choice(["wire", "ach", "card", "internal"])
    })

# Records that pass validation (amount > 0)
valid_records = [r for r in records if r["amount"] > 0]

# Run A processes records 1-200, Run B also processes records 1-200
# The conflict: Run B's enrich stage overwrites some of Run A's enriched records
# Specifically, records with IDs that are in the "conflict zone"
# The conflict zone is records 67-112 (46 records) - these get Run B's enrich output
# which later causes wrong transform because Run B used stale FX rates

CONFLICT_START = 67
CONFLICT_END = 112
conflict_ids = set(range(CONFLICT_START, CONFLICT_END + 1))

def compute_risk_score(amount, record_id):
    return (int(amount * 7) + record_id * 13) % 100

def compute_checksum(record_id, amount, currency, risk_score):
    s = f"{record_id}:{amount:.2f}:{currency}:{risk_score}"
    return hashlib.md5(s.encode()).hexdigest()

# === Stage 1: Ingest ===
with open(f"{EVIDENCE_DIR}/staging_area/stage_ingest.jsonl", "w") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

# === Stage 2: Validate ===
with open(f"{EVIDENCE_DIR}/staging_area/stage_validate.jsonl", "w") as f:
    for r in valid_records:
        f.write(json.dumps(r) + "\n")

# === Stage 3: Enrich ===
# This is where the conflict happens - Run B overwrites some records
enriched_records = []
for r in valid_records:
    er = dict(r)
    er["risk_score"] = compute_risk_score(r["amount"], r["record_id"])
    enriched_records.append(er)

# The staging file shows the CONFLICTED state (Run B's overwrites are in place)
with open(f"{EVIDENCE_DIR}/staging_area/stage_enrich.jsonl", "w") as f:
    for er in enriched_records:
        f.write(json.dumps(er) + "\n")

# === Stage 4: Transform ===
# Records in the conflict zone were transformed using STALE fx rates
# Records outside conflict zone used CORRECT fx rates
transformed_records = []
for er in enriched_records:
    tr = dict(er)
    rid = tr["record_id"]
    if rid in conflict_ids:
        # These records got transformed with stale rates (the corruption!)
        rate = STALE_FX_RATES[tr["currency"]]
    else:
        rate = FX_RATES[tr["currency"]]
    tr["amount"] = round(tr["amount"] * rate, 2)
    tr["currency"] = "USD"
    transformed_records.append(tr)

with open(f"{EVIDENCE_DIR}/staging_area/stage_transform.jsonl", "w") as f:
    for tr in transformed_records:
        f.write(json.dumps(tr) + "\n")

# === Stage 5: Load ===
# Compute checksums on the (potentially corrupted) transformed data
loaded_records = []
for tr in transformed_records:
    lr = dict(tr)
    lr["checksum"] = compute_checksum(lr["record_id"], lr["amount"], lr["currency"], lr["risk_score"])
    loaded_records.append(lr)

with open(f"{EVIDENCE_DIR}/staging_area/stage_load.jsonl", "w") as f:
    for lr in loaded_records:
        f.write(json.dumps(lr) + "\n")

# Now compute which records are actually "corrupted" - their load checksum
# doesn't match what it SHOULD be if correct fx_rates were used
corrupted_ids = []
for er in enriched_records:
    rid = er["record_id"]
    if rid in conflict_ids:
        # Compute what the correct amount should be
        correct_rate = FX_RATES[er["currency"]]
        correct_amount = round(er["amount"] * correct_rate, 2)
        correct_checksum = compute_checksum(rid, correct_amount, "USD", er["risk_score"])

        # Compute what was actually stored (stale rate)
        stale_rate = STALE_FX_RATES[er["currency"]]
        actual_amount = round(er["amount"] * stale_rate, 2)
        actual_checksum = compute_checksum(rid, actual_amount, "USD", er["risk_score"])

        if correct_checksum != actual_checksum:
            corrupted_ids.append(rid)

corrupted_ids.sort()

# === Generate Pipeline Audit Log ===
# This log has entries from both runs, with some corruption (truncated checksums, swapped fields)
base_time = datetime(2026, 3, 15, 2, 0, 0)
audit_entries = []

# Run A timeline
run_a_events = [
    (0, "ingest", "start", "Processing 200 records from source queue"),
    (45, "ingest", "complete", "Ingested 200 records"),
    (60, "validate", "start", f"Validating {len(valid_records)} candidate records"),
    (95, "validate", "complete", f"Validated {len(valid_records)} records, filtered {200 - len(valid_records)} invalid"),
    (110, "enrich", "start", f"Enriching {len(valid_records)} records with risk scores"),
    (180, "enrich", "complete", f"Enriched {len(valid_records)} records"),
    (195, "transform", "start", f"Transforming {len(valid_records)} records with FX rates"),
    (290, "transform", "complete", f"Transformed {len(valid_records)} records to USD"),
    (305, "load", "start", f"Loading {len(valid_records)} records to database"),
    (395, "load", "complete", f"Loaded {len(valid_records)} records, {len(corrupted_ids)} checksum warnings"),
]

# Run B timeline (overlaps with Run A starting at enrich stage)
run_b_events = [
    (120, "ingest", "start", "Manual re-run: Processing 200 records from source queue"),
    (155, "ingest", "complete", "Ingested 200 records"),
    (160, "validate", "start", f"Validating {len(valid_records)} candidate records"),
    (185, "validate", "complete", f"Validated {len(valid_records)} records, filtered {200 - len(valid_records)} invalid"),
    (190, "enrich", "start", f"Enriching {len(valid_records)} records with risk scores"),
    # CONFLICT: Run B's enrich overlaps with Run A's transform prep
    (250, "enrich", "complete", f"Enriched {len(valid_records)} records - WARNING: staging file lock contention detected"),
    (260, "transform", "start", f"Transforming {len(valid_records)} records with FX rates (using cached rates)"),
    (340, "transform", "complete", f"Transformed {len(valid_records)} records to USD"),
    (355, "load", "start", f"Loading {len(valid_records)} records to database"),
    (420, "load", "error", "Duplicate key constraint - records already loaded by concurrent run"),
]

for offset_sec, stage, event, details in run_a_events:
    ts = base_time + timedelta(seconds=offset_sec)
    entry = {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{random.randint(100,999)}Z",
        "run_id": "A",
        "stage": stage,
        "event": event,
        "details": details,
        "checksum": hashlib.md5(f"A:{stage}:{event}".encode()).hexdigest()
    }
    audit_entries.append((ts, entry))

for offset_sec, stage, event, details in run_b_events:
    ts = base_time + timedelta(seconds=offset_sec)
    entry = {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{random.randint(100,999)}Z",
        "run_id": "B",
        "stage": stage,
        "event": event,
        "details": details,
        "checksum": hashlib.md5(f"B:{stage}:{event}".encode()).hexdigest()
    }
    audit_entries.append((ts, entry))

# Add conflict events
conflict_events = [
    (192, "A", "enrich", "conflict", f"Lock contention on staging_area/stage_enrich.jsonl - concurrent write detected from run B"),
    (248, "B", "enrich", "conflict", f"Overwrote records {CONFLICT_START}-{CONFLICT_END} in staging file - stale lock acquired"),
    (196, "A", "transform", "conflict", f"Reading enriched data that may contain records from concurrent run B"),
]

for offset_sec, run_id, stage, event, details in conflict_events:
    ts = base_time + timedelta(seconds=offset_sec)
    entry = {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{random.randint(100,999)}Z",
        "run_id": run_id,
        "stage": stage,
        "event": event,
        "details": details,
        "checksum": hashlib.md5(f"{run_id}:{stage}:{event}".encode()).hexdigest()
    }
    audit_entries.append((ts, entry))

# Add noise entries (red herrings)
noise_events = [
    (30, "X", "monitor", "start", "Health check probe - all stages nominal"),
    (75, "X", "monitor", "complete", "Disk usage at 42% - within threshold"),
    (130, "X", "gc", "start", "Garbage collection triggered on staging_area - old runs"),
    (200, "X", "monitor", "complete", "Memory usage spike detected on transform worker - investigating"),
    (270, "X", "monitor", "complete", "Network latency to DB: 2.3ms (normal)"),
    (330, "X", "gc", "complete", "Cleaned 3 stale staging files from previous day"),
    (380, "X", "monitor", "complete", "CPU usage normalized after transform batch completion"),
]

for offset_sec, run_id, stage, event, details in noise_events:
    ts = base_time + timedelta(seconds=offset_sec)
    entry = {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{random.randint(100,999)}Z",
        "run_id": run_id,
        "stage": stage,
        "event": event,
        "details": details,
        "checksum": hashlib.md5(f"{run_id}:{stage}:{event}".encode()).hexdigest()
    }
    audit_entries.append((ts, entry))

# Sort by timestamp and write
audit_entries.sort(key=lambda x: x[0])

# Corrupt some entries (truncated checksums, swapped fields) to add difficulty
with open(f"{EVIDENCE_DIR}/pipeline_audit.log", "w") as f:
    for i, (ts, entry) in enumerate(audit_entries):
        if i % 7 == 3:
            # Truncate checksum
            entry["checksum"] = entry["checksum"][:16] + "..."
        if i % 11 == 5:
            # Swap stage and event fields in the log line (not the JSON)
            line = f"[{entry['timestamp']}] run={entry['run_id']} event={entry['stage']} stage={entry['event']} | {entry['details']} | cksum={entry['checksum']}"
        else:
            line = f"[{entry['timestamp']}] run={entry['run_id']} stage={entry['stage']} event={entry['event']} | {entry['details']} | cksum={entry['checksum']}"
        f.write(line + "\n")

# === Generate Scheduler Log ===
with open(f"{EVIDENCE_DIR}/scheduler.log", "w") as f:
    # Pre-incident entries (noise)
    f.write(f"2026-03-14T23:00:00.001Z [INFO] scheduler: daily cleanup job completed\n")
    f.write(f"2026-03-15T00:00:00.512Z [INFO] scheduler: midnight rollover - resetting counters\n")
    f.write(f"2026-03-15T01:00:00.203Z [INFO] scheduler: hourly pipeline run skipped - no new data\n")
    f.write(f"2026-03-15T01:30:00.100Z [WARN] scheduler: disk space check - 58% used on /data\n")

    # Run A trigger
    f.write(f"2026-03-15T02:00:00.015Z [INFO] scheduler: triggering scheduled pipeline run A for batch 2026-03-15-02\n")
    f.write(f"2026-03-15T02:00:00.018Z [INFO] scheduler: run A assigned worker node etl-worker-03\n")

    # Operator manually triggers Run B (this is the problem!)
    f.write(f"2026-03-15T02:01:55.200Z [WARN] scheduler: manual pipeline trigger received from operator=jsmith via CLI\n")
    f.write(f"2026-03-15T02:02:00.001Z [INFO] scheduler: triggering manual pipeline run B for batch 2026-03-15-02\n")
    f.write(f"2026-03-15T02:02:00.005Z [WARN] scheduler: run B targeting same batch as active run A - no concurrency guard!\n")
    f.write(f"2026-03-15T02:02:00.008Z [INFO] scheduler: run B assigned worker node etl-worker-03\n")

    # Run A completion
    f.write(f"2026-03-15T02:06:35.500Z [INFO] scheduler: run A completed with status=WARNING - {len(corrupted_ids)} checksum mismatches in load stage\n")

    # Run B failure
    f.write(f"2026-03-15T02:07:00.200Z [ERROR] scheduler: run B failed at load stage - duplicate key constraint violation\n")
    f.write(f"2026-03-15T02:07:00.205Z [INFO] scheduler: run B final status=FAILED\n")

    # Post-incident
    f.write(f"2026-03-15T02:10:00.000Z [WARN] scheduler: alerting on-call team - pipeline anomaly detected\n")
    f.write(f"2026-03-15T02:15:00.100Z [INFO] scheduler: pipeline paused by operator=jsmith pending investigation\n")

# === Generate Metrics CSV ===
with open(f"{EVIDENCE_DIR}/metrics.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "cpu_percent", "memory_mb", "disk_io_mbps", "net_io_mbps", "active_threads"])

    for i in range(60):  # 10 minutes of data at 10-second intervals
        ts = base_time + timedelta(seconds=i*10)

        # Baseline with spikes during processing
        cpu = 15 + random.uniform(-5, 5)
        mem = 1200 + random.uniform(-100, 100)
        disk = 5 + random.uniform(-2, 2)
        net = 2 + random.uniform(-1, 1)
        threads = 4

        # Spike during overlapping runs (120-350 seconds)
        if 120 <= i*10 <= 350:
            cpu += 40 + random.uniform(-10, 10)
            mem += 600 + random.uniform(-50, 50)
            disk += 15 + random.uniform(-3, 3)
            threads = 8

        # Extra spike during conflict window (190-260 seconds)
        if 190 <= i*10 <= 260:
            cpu += 20 + random.uniform(-5, 5)
            disk += 10 + random.uniform(-2, 2)
            threads = 12

        writer.writerow([
            ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            f"{cpu:.1f}",
            f"{mem:.0f}",
            f"{disk:.1f}",
            f"{net:.1f}",
            threads
        ])

# === Generate DB WAL Excerpt ===
with open(f"{EVIDENCE_DIR}/db_wal_excerpt.log", "w") as f:
    f.write("# PostgreSQL WAL excerpt - transactions table writes\n")
    f.write("# Format: LSN | timestamp | xid | operation | table | data_summary\n\n")

    wal_base = base_time + timedelta(seconds=305)
    lsn_counter = 0x1A000000
    xid = 84200

    for i, lr in enumerate(loaded_records):
        ts = wal_base + timedelta(milliseconds=i * 50 + random.randint(0, 20))
        lsn_counter += random.randint(100, 500)

        f.write(f"{lsn_counter:08X}/{lsn_counter+64:08X} | {ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | "
                f"xid={xid} | INSERT | transactions | "
                f"record_id={lr['record_id']} amount={lr['amount']:.2f} currency={lr['currency']} "
                f"checksum={lr['checksum'][:12]}...\n")

    xid += 1
    f.write(f"\n# Transaction xid={xid} from run B - ABORTED (duplicate key)\n")

    for i in range(5):
        ts = wal_base + timedelta(seconds=50, milliseconds=i * 30)
        lsn_counter += random.randint(100, 500)
        rid = loaded_records[i]["record_id"]
        f.write(f"{lsn_counter:08X}/{lsn_counter+64:08X} | {ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | "
                f"xid={xid} | INSERT | transactions | "
                f"record_id={rid} amount=... [ABORTED - duplicate_key_violation]\n")

# Write metadata for test verification (will be deleted after generation)
# This is used ONLY during docker build and removed
metadata = {
    "corrupted_ids": corrupted_ids,
    "total_valid_records": len(valid_records),
    "conflict_start": CONFLICT_START,
    "conflict_end": CONFLICT_END,
    "corruption_stage": "transform",
    "fx_rates": FX_RATES,
    "stale_fx_rates": STALE_FX_RATES,
}
with open("/tmp/build_metadata.json", "w") as f:
    json.dump(metadata, f)

print(f"Evidence generated successfully.")
print(f"Total records: 200")
print(f"Valid records (amount > 0): {len(valid_records)}")
print(f"Corrupted records: {len(corrupted_ids)}")
print(f"Conflict zone: records {CONFLICT_START}-{CONFLICT_END}")
print(f"Corrupted IDs: {corrupted_ids}")
