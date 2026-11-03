# ETL Pipeline Corruption Forensics and Recovery

You are investigating a production incident in a financial data ETL pipeline. The pipeline processes transaction batches through 5 stages: `ingest`, `validate`, `enrich`, `transform`, `load`. Each stage reads from its input queue, processes records, and writes to the next stage's queue, appending entries to an audit log.

On 2026-03-15, the pipeline's monitoring detected checksum mismatches in the `load` stage output. Investigation revealed that two concurrent pipeline runs (Run `A` started by the scheduler, Run `B` triggered manually by an operator) overlapped and created a race condition that corrupted records in the shared staging area.

## Evidence Available

- `/app/evidence/pipeline_audit.log` — Audit trail from all 5 pipeline stages (partially corrupted; some entries have truncated checksums or swapped fields)
- `/app/evidence/scheduler.log` — The job scheduler's log showing pipeline run triggers and completions
- `/app/evidence/staging_area/` — Directory containing the intermediate data files (`stage_*.jsonl`) that each pipeline stage produced
- `/app/evidence/metrics.csv` — System metrics (CPU, memory, disk I/O) sampled every 10 seconds during the incident window
- `/app/evidence/db_wal_excerpt.log` — Database write-ahead log excerpt showing the final `load` stage writes
- `/app/evidence/fx_rates.json` — Current foreign exchange rates used for currency conversion

## Your Tasks

### 1. Timeline Reconstruction (`/app/output/timeline.jsonl`)

Reconstruct the complete timeline of events during the incident window. Each line must be a JSON object with fields:
- `timestamp` (ISO 8601 with milliseconds, e.g. `2026-03-15T02:15:30.123Z`)
- `run_id` (`"A"` or `"B"`)
- `stage` (one of: `ingest`, `validate`, `enrich`, `transform`, `load`, `scheduler`)
- `event` (one of: `start`, `complete`, `error`, `conflict`)
- `details` (string describing what happened)

Events must be sorted by timestamp. Include all stage transitions for both runs and mark points where the two runs conflicted over shared resources.

### 2. Corrupted Record Identification (`/app/output/corrupted_records.json`)

Identify all records that were corrupted by the race condition. Write a JSON file containing:
- `total_records_processed`: int — total records across both runs
- `corrupted_record_ids`: list of int — the `record_id` values of corrupted records, sorted ascending
- `corruption_stage`: string — the pipeline stage where the data values first became incorrect
- `corruption_mechanism`: string — one-sentence explanation of how the race condition caused corruption

A record is considered corrupted if its checksum in the `load` stage output does not match the expected checksum computed by applying the documented transformation chain to the original ingested data. The transformation chain is:
- `validate`: filters records where `amount <= 0`, no data modification
- `enrich`: adds field `risk_score` = `(int(amount * 7) + record_id * 13) % 100`
- `transform`: multiplies `amount` by the `fx_rate` for the record's `currency` (rates are in `/app/evidence/fx_rates.json`), converts `currency` to `"USD"`, rounds `amount` to 2 decimal places
- `load`: computes final checksum as MD5 hex digest of `f"{record_id}:{amount:.2f}:{currency}:{risk_score}"`

### 3. Root Cause Analysis Report (`/app/output/rca_report.md`)

Write a markdown report containing these exact section headers (level 2):
- `## Incident Summary` — 2-3 sentence overview
- `## Timeline of Events` — Key events in chronological order
- `## Root Cause` — Technical explanation of the race condition, referencing specific timestamps and run IDs
- `## Impact Assessment` — Number of corrupted records, affected record ID ranges, estimated data quality impact percentage
- `## Corrective Actions` — Steps to reprocess corrupted records and prevent recurrence

### 4. Recovery Script (`/app/output/reprocess.sh`)

Write an executable bash script that, when run, reads the original ingested data from `/app/evidence/staging_area/stage_ingest.jsonl`, reprocesses ONLY the corrupted records through the correct transformation chain, and writes the corrected records to `/app/output/recovered_records.jsonl` (one JSON object per line, with fields: `record_id`, `amount`, `currency`, `risk_score`, `checksum`). The script must be idempotent — running it multiple times produces identical output.
