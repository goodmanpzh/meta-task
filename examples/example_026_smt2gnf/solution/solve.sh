#!/bin/bash
set -euo pipefail

mkdir -p /app/output

# ============================================================
# Step 1: Parse and understand the evidence
# ============================================================

# Read FX rates
FX_RATES_FILE="/app/evidence/fx_rates.json"

# Parse the audit log to reconstruct the timeline
# The audit log has corrupted entries (swapped fields, truncated checksums)
# We need to handle both formats:
#   Normal: [ts] run=X stage=Y event=Z | details | cksum=...
#   Swapped: [ts] run=X event=Y stage=Z | details | cksum=...

python3 << 'PYEOF'
import json
import hashlib
import re
import os

EVIDENCE_DIR = "/app/evidence"
OUTPUT_DIR = "/app/output"

# Load FX rates
with open(f"{EVIDENCE_DIR}/fx_rates.json") as f:
    fx_rates = json.load(f)

# ============================================================
# Step 1: Parse audit log to build timeline
# ============================================================

timeline_events = []
audit_pattern = re.compile(
    r'\[([^\]]+)\]\s+run=(\w+)\s+'
    r'(?:stage=(\w+)\s+event=(\w+)|event=(\w+)\s+stage=(\w+))'
    r'\s*\|\s*(.+?)\s*\|\s*cksum=(.+)'
)

with open(f"{EVIDENCE_DIR}/pipeline_audit.log") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        m = audit_pattern.match(line)
        if m:
            timestamp = m.group(1)
            run_id = m.group(2)
            # Handle both normal and swapped field order
            # Normal: stage=X event=Y -> stage=X, event=Y
            # Swapped: event=X stage=Y -> the labels are swapped, so
            #   what's labeled "event=" is really the stage, and "stage=" is the event
            if m.group(3):
                stage = m.group(3)
                event = m.group(4)
            else:
                # Swapped: event=<val1> stage=<val2>
                # val1 is the stage, val2 is the event
                stage = m.group(5)
                event = m.group(6)
            details = m.group(7)

            # Skip noise entries (run X = monitoring/gc)
            if run_id not in ("A", "B"):
                continue

            timeline_events.append({
                "timestamp": timestamp,
                "run_id": run_id,
                "stage": stage,
                "event": event,
                "details": details
            })

# Also add scheduler events
with open(f"{EVIDENCE_DIR}/scheduler.log") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        # Parse scheduler log: timestamp [LEVEL] scheduler: message
        m = re.match(r'(\S+)\s+\[(\w+)\]\s+scheduler:\s+(.+)', line)
        if m:
            ts = m.group(1)
            level = m.group(2)
            msg = m.group(3)

            # Determine run_id and event type from message
            if "run A" in msg.lower() or "run a" in msg:
                run_id = "A"
            elif "run B" in msg.lower() or "run b" in msg:
                run_id = "B"
            else:
                continue

            if "triggering" in msg:
                event = "start"
            elif "completed" in msg:
                event = "complete"
            elif "failed" in msg:
                event = "error"
            else:
                continue

            timeline_events.append({
                "timestamp": ts,
                "run_id": run_id,
                "stage": "scheduler",
                "event": event,
                "details": msg
            })

# Sort by timestamp
timeline_events.sort(key=lambda x: x["timestamp"])

# Write timeline
with open(f"{OUTPUT_DIR}/timeline.jsonl", "w") as f:
    for ev in timeline_events:
        f.write(json.dumps(ev) + "\n")

# ============================================================
# Step 2: Identify corrupted records
# ============================================================

# The corruption mechanism: need to figure out which records were affected
# by the race condition. From the audit log, we can see:
# - Run B overwrote records 67-112 in the enrich staging file
# - Run A's transform stage read from this partially overwritten file
# - The key insight: Run B used "cached rates" (stale FX rates)
#
# To identify corrupted records, we need to:
# 1. Read the original ingested data
# 2. Apply the correct transformation chain
# 3. Compare with what's in the load stage output
# 4. Records with mismatching checksums are corrupted

# Load ingested records
ingested = []
with open(f"{EVIDENCE_DIR}/staging_area/stage_ingest.jsonl") as f:
    for line in f:
        ingested.append(json.loads(line))

# Load the load stage output (what was actually written)
loaded = {}
with open(f"{EVIDENCE_DIR}/staging_area/stage_load.jsonl") as f:
    for line in f:
        r = json.loads(line)
        loaded[r["record_id"]] = r

# Apply correct transformation chain to each record
def compute_risk_score(amount, record_id):
    return (int(amount * 7) + record_id * 13) % 100

def compute_checksum(record_id, amount, currency, risk_score):
    s = f"{record_id}:{amount:.2f}:{currency}:{risk_score}"
    return hashlib.md5(s.encode()).hexdigest()

corrupted_ids = []
total_valid = 0

for r in ingested:
    # Validate stage: filter amount <= 0
    if r["amount"] <= 0:
        continue
    total_valid += 1

    rid = r["record_id"]

    # Enrich: compute risk score
    risk_score = compute_risk_score(r["amount"], rid)

    # Transform: apply FX rate, convert to USD
    rate = fx_rates[r["currency"]]
    correct_amount = round(r["amount"] * rate, 2)

    # Load: compute expected checksum
    expected_checksum = compute_checksum(rid, correct_amount, "USD", risk_score)

    # Compare with actual loaded record
    if rid in loaded and loaded[rid]["checksum"] != expected_checksum:
        corrupted_ids.append(rid)

corrupted_ids.sort()

# Determine the corruption stage and mechanism from the evidence
# The conflict happened at the enrich stage (overwrite), but the actual
# data corruption manifests in the transform stage (wrong FX rates applied)
corruption_stage = "transform"
corruption_mechanism = (
    "Run B's enrich stage overwrote records 67-112 in the shared staging file, "
    "and Run A's transform stage then processed these records using stale FX rates "
    "from Run B's cached rate snapshot, producing incorrect USD amounts for non-USD currencies."
)

corrupted_output = {
    "total_records_processed": total_valid,
    "corrupted_record_ids": corrupted_ids,
    "corruption_stage": corruption_stage,
    "corruption_mechanism": corruption_mechanism
}

with open(f"{OUTPUT_DIR}/corrupted_records.json", "w") as f:
    json.dump(corrupted_output, f, indent=2)

# ============================================================
# Step 3: Generate RCA Report
# ============================================================

impact_pct = round(len(corrupted_ids) / total_valid * 100, 1)
min_id = min(corrupted_ids)
max_id = max(corrupted_ids)
conflict_range_size = max_id - min_id + 1
usd_in_range = conflict_range_size - len(corrupted_ids)

rca_report = f"""# ETL Pipeline Corruption Incident - Root Cause Analysis

## Incident Summary

On 2026-03-15, a race condition between two concurrent ETL pipeline runs (Run A - scheduled, Run B - manually triggered) caused {len(corrupted_ids)} records to be loaded with incorrect USD amounts. The corruption was caused by Run B's enrich stage overwriting shared staging data that Run A was actively processing, combined with Run B using stale FX rate data.

## Timeline of Events

1. **02:00:00Z** - Scheduler triggers Run A for batch 2026-03-15-02
2. **02:01:55Z** - Operator jsmith manually triggers Run B for the same batch
3. **02:02:00Z** - Scheduler warns: no concurrency guard for duplicate batch
4. **02:01:50Z** - Run A begins enrich stage
5. **02:03:10Z** - Run B begins enrich stage, targeting same staging file
6. **02:03:12Z** - Lock contention detected on stage_enrich.jsonl
7. **02:03:15Z** - Run A begins transform stage, reading partially overwritten enrich data
8. **02:04:08Z** - Run B overwrites records {min_id}-{max_id} in staging file
9. **02:06:35Z** - Run A completes with {len(corrupted_ids)} checksum warnings
10. **02:07:00Z** - Run B fails at load stage (duplicate key constraint)
11. **02:10:00Z** - On-call team alerted
12. **02:15:00Z** - Pipeline paused by operator

## Root Cause

The root cause is a missing concurrency guard in the pipeline scheduler. When operator jsmith manually triggered Run B at 02:01:55Z while Run A was already active for the same batch (2026-03-15-02), both runs were assigned to the same worker node (etl-worker-03) and shared the same staging directory.

Run B's enrich stage (starting 02:03:10Z) acquired a stale lock on `stage_enrich.jsonl` and overwrote records {min_id}-{max_id}. Run A's transform stage (starting 02:03:15Z) then read this contaminated staging file. Critically, Run B used a cached/stale FX rate snapshot from the previous day, so the overwritten records were transformed with incorrect exchange rates, producing wrong USD amounts for all non-USD currencies in the conflict zone.

The corruption specifically affected the **transform** stage output: records {min_id}-{max_id} that had non-USD original currencies received incorrect FX rate conversions.

## Impact Assessment

- **Total records processed**: {total_valid}
- **Corrupted records**: {len(corrupted_ids)}
- **Data quality impact**: {impact_pct}% of loaded records have incorrect amounts
- **Affected record ID range**: {min_id}-{max_id} (non-USD currencies only; {usd_in_range} USD records in this range were unaffected)
- **No data loss**: All original source data is intact in the ingest staging file

## Corrective Actions

1. **Immediate**: Reprocess the {len(corrupted_ids)} corrupted records using the correct FX rates from `/app/evidence/fx_rates.json`
2. **Short-term**: Add a concurrency guard to the pipeline scheduler to prevent duplicate batch runs
3. **Short-term**: Implement file-level locking on staging area files with proper lock acquisition timeouts
4. **Medium-term**: Use per-run isolated staging directories instead of shared staging
5. **Medium-term**: Add FX rate versioning with explicit rate snapshot IDs embedded in each record
6. **Long-term**: Implement end-to-end record checksums validated at each stage boundary
"""

with open(f"{OUTPUT_DIR}/rca_report.md", "w") as f:
    f.write(rca_report)

# ============================================================
# Step 4: Generate Recovery Script
# ============================================================

# Write the corrected records for later reference
recovered = []
for r in ingested:
    if r["amount"] <= 0:
        continue
    if r["record_id"] not in corrupted_ids:
        continue

    rid = r["record_id"]
    risk_score = compute_risk_score(r["amount"], rid)
    rate = fx_rates[r["currency"]]
    correct_amount = round(r["amount"] * rate, 2)
    checksum = compute_checksum(rid, correct_amount, "USD", risk_score)

    recovered.append({
        "record_id": rid,
        "amount": correct_amount,
        "currency": "USD",
        "risk_score": risk_score,
        "checksum": checksum
    })

# Save recovered records (used by reprocess.sh for verification)
# But the actual reprocess.sh should compute them from scratch

print(f"Timeline events: {len(timeline_events)}")
print(f"Total valid records: {total_valid}")
print(f"Corrupted records: {len(corrupted_ids)}")
print(f"Corrupted IDs: {corrupted_ids}")
PYEOF

# ============================================================
# Step 4: Create the reprocessing script
# ============================================================

cat > /app/output/reprocess.sh << 'REPROCESS'
#!/bin/bash
set -euo pipefail

# Idempotent reprocessing script for corrupted ETL records
# Reads original ingested data, identifies corrupted records,
# and reprocesses them with correct FX rates

OUTPUT_FILE="/app/output/recovered_records.jsonl"

python3 << 'INNEREOF'
import json
import hashlib

EVIDENCE_DIR = "/app/evidence"
OUTPUT_FILE = "/app/output/recovered_records.jsonl"

# Load FX rates
with open(f"{EVIDENCE_DIR}/fx_rates.json") as f:
    fx_rates = json.load(f)

# Load corrupted record IDs
with open("/app/output/corrupted_records.json") as f:
    corrupted_data = json.load(f)
corrupted_ids = set(corrupted_data["corrupted_record_ids"])

# Load ingested records
ingested = []
with open(f"{EVIDENCE_DIR}/staging_area/stage_ingest.jsonl") as f:
    for line in f:
        ingested.append(json.loads(line))

def compute_risk_score(amount, record_id):
    return (int(amount * 7) + record_id * 13) % 100

def compute_checksum(record_id, amount, currency, risk_score):
    s = f"{record_id}:{amount:.2f}:{currency}:{risk_score}"
    return hashlib.md5(s.encode()).hexdigest()

# Reprocess only corrupted records
recovered = []
for r in ingested:
    if r["amount"] <= 0:
        continue
    if r["record_id"] not in corrupted_ids:
        continue

    rid = r["record_id"]
    # Enrich
    risk_score = compute_risk_score(r["amount"], rid)
    # Transform with correct FX rates
    rate = fx_rates[r["currency"]]
    correct_amount = round(r["amount"] * rate, 2)
    # Load checksum
    checksum = compute_checksum(rid, correct_amount, "USD", risk_score)

    recovered.append({
        "record_id": rid,
        "amount": correct_amount,
        "currency": "USD",
        "risk_score": risk_score,
        "checksum": checksum
    })

# Sort by record_id for deterministic output
recovered.sort(key=lambda x: x["record_id"])

with open(OUTPUT_FILE, "w") as f:
    for rec in recovered:
        f.write(json.dumps(rec) + "\n")

print(f"Recovered {len(recovered)} records to {OUTPUT_FILE}")
INNEREOF
REPROCESS

chmod +x /app/output/reprocess.sh

# Run the reprocessing script
bash /app/output/reprocess.sh

echo "=== Solution complete ==="
echo "Output files:"
ls -la /app/output/
