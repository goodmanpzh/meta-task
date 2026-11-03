#!/bin/bash
set -euo pipefail

# Create the recovery script at /app/recover.sh
cat > /app/recover.sh << 'SCRIPTEOF'
#!/bin/bash
set -euo pipefail

# Create output directory
mkdir -p /app/recovered

# Use Python for the heavy lifting since it handles CRC32 and special characters reliably
python3 << 'PYEOF'
import os
import sys
import zlib
import json
import re
from collections import defaultdict

WAREHOUSE = "/app/warehouse"
OUTPUT_DIR = "/app/recovered"
KNOWN_STREAMS = {"txn_alpha", "txn_beta", "sys_gamma", "audit_delta", "err_epsilon"}
SKIP_EXTENSIONS = {".old", ".bak", ".txt", ".json", ".metadata"}

def find_fragment_files(base_dir):
    """Find all valid fragment files, excluding backup/index files."""
    fragments = []
    for root, dirs, files in os.walk(base_dir):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext in SKIP_EXTENSIONS:
                continue
            if fname.startswith('.'):
                continue
            fragments.append(os.path.join(root, fname))
    return fragments

def compute_crc(stream_id, seq_num_str, payload):
    """Compute CRC32 matching the generation format."""
    data = f"{stream_id}|{seq_num_str}|{payload}"
    return zlib.crc32(data.encode('utf-8')) & 0xFFFFFFFF

def parse_and_validate_line(line):
    """Parse a log line and validate it. Returns tuple if valid, None otherwise."""
    if not line or line.strip() == '':
        return None

    parts = line.split('|', 3)
    if len(parts) < 4:
        return None

    stream_id, seq_num_str, crc_hex, payload = parts

    if stream_id not in KNOWN_STREAMS:
        return None

    if not re.match(r'^\d{6}$', seq_num_str):
        return None

    seq_num = int(seq_num_str)

    if not re.match(r'^[0-9a-f]{8}$', crc_hex):
        return None

    expected_crc = compute_crc(stream_id, seq_num_str, payload)
    actual_crc = int(crc_hex, 16)

    if expected_crc != actual_crc:
        return None

    return (stream_id, seq_num, payload)

def main():
    fragments = find_fragment_files(WAREHOUSE)
    print(f"Found {len(fragments)} fragment files")

    recovered = defaultdict(dict)
    total_corrupted = 0
    total_duplicates = 0

    for fpath in sorted(fragments):
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.rstrip('\n')

                    result = parse_and_validate_line(line)
                    if result is None:
                        if line.strip():
                            total_corrupted += 1
                        continue

                    stream_id, seq_num, payload = result

                    if seq_num in recovered[stream_id]:
                        total_duplicates += 1
                    else:
                        recovered[stream_id][seq_num] = payload
        except Exception as e:
            print(f"Error reading {fpath}: {e}", file=sys.stderr)
            continue

    for stream_id in KNOWN_STREAMS:
        entries = recovered.get(stream_id, {})
        outpath = os.path.join(OUTPUT_DIR, f"{stream_id}.log")
        with open(outpath, 'w', encoding='utf-8') as f:
            for seq in sorted(entries.keys()):
                f.write(entries[seq] + '\n')
        print(f"  {stream_id}: {len(entries)} entries recovered")

    report = {
        "streams": {},
        "total_recovered": 0,
        "total_corrupted_lines": total_corrupted,
        "total_duplicate_lines": total_duplicates,
    }

    for stream_id in sorted(KNOWN_STREAMS):
        entries = recovered.get(stream_id, {})
        if entries:
            seq_nums = sorted(entries.keys())
            first_seq = seq_nums[0]
            last_seq = seq_nums[-1]
            all_expected = set(range(first_seq, last_seq + 1))
            missing = sorted(all_expected - set(seq_nums))

            report["streams"][stream_id] = {
                "recovered_count": len(entries),
                "missing_sequences": missing,
                "first_seq": first_seq,
                "last_seq": last_seq,
            }
        else:
            report["streams"][stream_id] = {
                "recovered_count": 0,
                "missing_sequences": [],
                "first_seq": 0,
                "last_seq": 0,
            }
        report["total_recovered"] += len(entries)

    report_path = os.path.join(OUTPUT_DIR, "REPORT.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nRecovery complete:")
    print(f"  Total recovered: {report['total_recovered']}")
    print(f"  Total corrupted lines: {report['total_corrupted_lines']}")
    print(f"  Total duplicate lines: {report['total_duplicate_lines']}")
    print(f"  Report written to {report_path}")

if __name__ == "__main__":
    main()
PYEOF

echo "Recovery script completed successfully."
SCRIPTEOF

chmod +x /app/recover.sh

# Run the recovery script
bash /app/recover.sh
