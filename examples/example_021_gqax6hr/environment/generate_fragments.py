#!/usr/bin/env python3
"""
Generate shredded log fragments for the WAL recovery task.

Format of each log line:
  STREAM_ID|SEQ_NUM|CRC32|PAYLOAD

Where:
  - STREAM_ID: alphanumeric stream identifier (e.g., "txn_alpha", "txn_beta")
  - SEQ_NUM: zero-padded 6-digit sequence number within the stream
  - CRC32: hex CRC32 of "STREAM_ID|SEQ_NUM|PAYLOAD" (without trailing newline)
  - PAYLOAD: the actual log data (may contain pipes, special chars, etc.)

The fragments are scattered across multiple directories with various corruptions:
  - Some lines have bad CRC (tampered payload or CRC)
  - Some lines are duplicated across fragments (simulating partial writes)
  - Some lines are truncated (incomplete writes)
  - Some lines have mangled format (missing fields)
  - Fragment files have random names and are in subdirectories
"""

import os
import random
import zlib
import string
import json

random.seed(42)

BASE_DIR = "/app/warehouse"
MANIFEST_PATH = "/app/.generation_manifest.json"

# Define streams with their content
STREAMS = {
    "txn_alpha": {
        "count": 150,
        "prefix": "ALPHA transaction record",
    },
    "txn_beta": {
        "count": 120,
        "prefix": "BETA ledger entry",
    },
    "sys_gamma": {
        "count": 80,
        "prefix": "GAMMA system event",
    },
    "audit_delta": {
        "count": 200,
        "prefix": "DELTA audit log",
    },
    "err_epsilon": {
        "count": 60,
        "prefix": "EPSILON error report",
    },
}

# Characters for payloads - include tricky ones
SPECIAL_CHARS = ['|', '$', '`', '"', "'", '\\', '&', ';', '(', ')', '<', '>', '{', '}', '!', '#', '*', '?', '[', ']', '~', '\t']


def compute_crc(stream_id, seq_num, payload):
    """Compute CRC32 of the canonical form."""
    data = f"{stream_id}|{seq_num:06d}|{payload}"
    return zlib.crc32(data.encode('utf-8')) & 0xFFFFFFFF


def generate_payload(prefix, seq_num):
    """Generate a payload with some special characters mixed in."""
    base = f"{prefix} #{seq_num}: "
    # Add some random content
    words = []
    for _ in range(random.randint(3, 12)):
        word_len = random.randint(2, 10)
        word = ''.join(random.choices(string.ascii_lowercase, k=word_len))
        # 15% chance to inject a special character
        if random.random() < 0.15:
            special = random.choice(SPECIAL_CHARS)
            pos = random.randint(0, len(word))
            word = word[:pos] + special + word[pos:]
        words.append(word)
    return base + ' '.join(words)


def format_line(stream_id, seq_num, payload):
    """Format a valid log line."""
    crc = compute_crc(stream_id, seq_num, payload)
    return f"{stream_id}|{seq_num:06d}|{crc:08x}|{payload}"


def corrupt_crc(line):
    """Return line with a bad CRC."""
    parts = line.split('|', 3)
    if len(parts) >= 4:
        # Flip some bits in the CRC
        orig_crc = int(parts[2], 16)
        bad_crc = orig_crc ^ random.randint(1, 0xFFFFFFFF)
        parts[2] = f"{bad_crc & 0xFFFFFFFF:08x}"
        return '|'.join(parts)
    return line


def corrupt_payload(line):
    """Return line with modified payload but original CRC."""
    parts = line.split('|', 3)
    if len(parts) >= 4:
        # Modify the payload slightly
        payload = parts[3]
        if len(payload) > 5:
            pos = random.randint(0, len(payload) - 1)
            char = random.choice(string.ascii_letters)
            payload = payload[:pos] + char + payload[pos+1:]
            parts[3] = payload
        return '|'.join(parts)
    return line


def truncate_line(line):
    """Return a truncated version of the line."""
    cut_point = random.randint(5, len(line) // 2)
    return line[:cut_point]


def mangle_format(line):
    """Return a line with missing fields."""
    parts = line.split('|', 3)
    if len(parts) >= 4:
        # Remove one of the middle fields
        which = random.choice([1, 2])
        del parts[which]
        return '|'.join(parts)
    return line


def generate_all_lines():
    """Generate all valid log lines for all streams."""
    all_lines = {}  # (stream_id, seq_num) -> formatted_line
    stream_data = {}  # stream_id -> [(seq_num, payload)]

    for stream_id, config in STREAMS.items():
        stream_data[stream_id] = []
        for seq in range(1, config["count"] + 1):
            payload = generate_payload(config["prefix"], seq)
            line = format_line(stream_id, seq, payload)
            all_lines[(stream_id, seq)] = line
            stream_data[stream_id].append((seq, payload))

    return all_lines, stream_data


def shard_into_fragments(all_lines):
    """
    Distribute lines across fragment files in various subdirectories.
    Add corruptions, duplicates, and noise.
    """
    # Create subdirectory structure
    subdirs = [
        "node1/shard_a",
        "node1/shard_b",
        "node2/primary",
        "node2/replica",
        "node3/segments",
        "overflow",
        "recovery_tmp",
        "node1/shard_a/subseg",
    ]

    for d in subdirs:
        os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)

    # Fragment file names - mix of patterns
    frag_names = []
    for i in range(25):
        subdir = random.choice(subdirs)
        # Various naming patterns
        patterns = [
            f"wal_{i:03d}.frag",
            f"segment.{i}.log",
            f"chunk_{random.randint(1000,9999)}.dat",
            f"part-{i:05d}",
            f"recovery_{i}.wal",
        ]
        name = random.choice(patterns)
        frag_names.append(os.path.join(subdir, name))

    # Also add some decoy files that look like fragments but aren't
    decoy_subdirs = ["node1/shard_a", "node2/primary", "overflow"]
    for i in range(5):
        subdir = random.choice(decoy_subdirs)
        name = random.choice([
            f"wal_{i}_backup.old",
            f"segment.{i}.log.bak",
            f"README.txt",
            f".metadata",
            f"index.json",
        ])
        decoy_path = os.path.join(BASE_DIR, subdir, name)
        with open(decoy_path, 'w') as f:
            if name.endswith('.json'):
                f.write('{"type": "index", "version": 2}\n')
            elif name.endswith('.txt'):
                f.write('This directory contains WAL fragments.\nDo not modify manually.\n')
            else:
                f.write(f'# Backup created at epoch {random.randint(1700000000, 1710000000)}\n')
                # Write some garbage that looks like log lines but isn't valid
                for _ in range(random.randint(2, 8)):
                    f.write(f"BACKUP|{random.randint(0,999):06d}|{'0'*8}|stale data\n")

    # Distribute valid lines
    all_keys = list(all_lines.keys())
    random.shuffle(all_keys)

    fragments = {name: [] for name in frag_names}

    for key in all_keys:
        # Each line goes to 1-2 fragments (duplicates for ~20% of lines)
        n_copies = 2 if random.random() < 0.20 else 1
        targets = random.sample(frag_names, min(n_copies, len(frag_names)))
        for target in targets:
            fragments[target].append(all_lines[key])

    # Now add corruptions to each fragment
    corrupted_count = 0
    for fname, lines in fragments.items():
        new_lines = []
        for line in lines:
            r = random.random()
            if r < 0.05:
                # Bad CRC
                new_lines.append(corrupt_crc(line))
                corrupted_count += 1
            elif r < 0.08:
                # Corrupted payload (CRC won't match)
                new_lines.append(corrupt_payload(line))
                corrupted_count += 1
            elif r < 0.10:
                # Truncated line
                new_lines.append(truncate_line(line))
                corrupted_count += 1
            elif r < 0.12:
                # Mangled format
                new_lines.append(mangle_format(line))
                corrupted_count += 1
            else:
                new_lines.append(line)

        # Add some completely garbage lines (~5% noise)
        n_garbage = max(1, len(new_lines) // 20)
        for _ in range(n_garbage):
            garbage_type = random.choice(['random', 'almost_valid', 'empty', 'binary_ish'])
            if garbage_type == 'random':
                garbage = ''.join(random.choices(string.printable.strip(), k=random.randint(10, 80)))
            elif garbage_type == 'almost_valid':
                # Looks like a valid line but stream_id doesn't exist
                fake_stream = random.choice(["txn_FAKE", "BAD_stream", "null", "undefined"])
                garbage = f"{fake_stream}|{random.randint(0,999):06d}|{'a'*8}|fake data here"
            elif garbage_type == 'empty':
                garbage = ''
            else:
                garbage = '\x00' * random.randint(5, 20) + 'corrupted'
            pos = random.randint(0, len(new_lines))
            new_lines.insert(pos, garbage)

        # Shuffle lines within the fragment (they're not in order)
        random.shuffle(new_lines)
        fragments[fname] = new_lines

    # Write fragments
    for fname, lines in fragments.items():
        fpath = os.path.join(BASE_DIR, fname)
        with open(fpath, 'w') as f:
            for line in lines:
                f.write(line + '\n')

    return corrupted_count


def write_stream_manifest(stream_data):
    """Write the ground truth manifest (will be deleted after generation)."""
    manifest = {}
    for stream_id, entries in stream_data.items():
        manifest[stream_id] = {
            "total_entries": len(entries),
            "entries": []
        }
        for seq, payload in sorted(entries):
            crc = compute_crc(stream_id, seq, payload)
            manifest[stream_id]["entries"].append({
                "seq": seq,
                "payload": payload,
                "crc": f"{crc:08x}"
            })

    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2)


def write_format_spec():
    """Write the format specification file that the agent will use."""
    spec_path = os.path.join(BASE_DIR, "FORMAT_SPEC.txt")
    with open(spec_path, 'w') as f:
        f.write("""WAL FRAGMENT FORMAT SPECIFICATION
=================================

Each valid log entry is a single line with the following pipe-delimited format:

  STREAM_ID|SEQ_NUM|CRC32_HEX|PAYLOAD

Fields:
  STREAM_ID  - Alphanumeric identifier with underscores (e.g., "txn_alpha")
               Known valid stream IDs: txn_alpha, txn_beta, sys_gamma, audit_delta, err_epsilon
  SEQ_NUM    - Zero-padded 6-digit sequence number (e.g., "000001")
               Sequence numbers start at 1 and are contiguous within each stream
  CRC32_HEX  - 8-character lowercase hex CRC32 checksum
               Computed over: "STREAM_ID|SEQ_NUM|PAYLOAD" (UTF-8 encoded, no trailing newline)
               Uses the standard CRC32 algorithm (same as Python's zlib.crc32 & 0xFFFFFFFF)
  PAYLOAD    - The log data. May contain pipe characters, special characters, etc.
               Split on FIRST THREE pipes only to parse correctly.

Validation rules:
  1. Line must have at least 3 pipe characters
  2. STREAM_ID must be one of the 5 known stream IDs listed above
  3. SEQ_NUM must be exactly 6 digits, zero-padded
  4. CRC32_HEX must be exactly 8 lowercase hex characters
  5. CRC32 must match the computed checksum of "STREAM_ID|SEQ_NUM|PAYLOAD"
  6. Empty lines should be skipped
  7. Lines failing any validation rule are considered corrupted and must be discarded

Fragment files:
  - Scattered across subdirectories under /app/warehouse/
  - Have various file extensions: .frag, .log, .dat, .wal, or no extension
  - EXCLUDE files with extensions: .old, .bak, .txt, .json, .metadata
  - Lines within fragments are NOT in order
  - The same valid entry may appear in multiple fragments (duplicates from partial writes)
  - Fragments contain noise lines (garbage, corrupted entries, entries from unknown streams)

Recovery output:
  For each known stream, produce a file at:
    /app/recovered/<STREAM_ID>.log

  Each recovered log file must contain ONLY the valid payloads, one per line,
  ordered by sequence number (ascending). No duplicates.

  Additionally, produce a recovery report at:
    /app/recovered/REPORT.json

  The report must be a JSON object with this structure:
  {
    "streams": {
      "<STREAM_ID>": {
        "recovered_count": <number of valid unique entries recovered>,
        "missing_sequences": [<list of missing sequence numbers as integers>],
        "first_seq": <first recovered sequence number>,
        "last_seq": <last recovered sequence number>
      },
      ...
    },
    "total_recovered": <total across all streams>,
    "total_corrupted_lines": <number of lines that failed validation across all fragments>,
    "total_duplicate_lines": <number of duplicate valid lines encountered across all fragments>
  }
""")


if __name__ == "__main__":
    print("Generating WAL fragments...")
    all_lines, stream_data = generate_all_lines()
    print(f"Generated {len(all_lines)} total valid entries across {len(STREAMS)} streams")

    corrupted = shard_into_fragments(all_lines)
    print(f"Distributed across fragments with ~{corrupted} corrupted entries")

    write_stream_manifest(stream_data)
    print(f"Manifest written to {MANIFEST_PATH}")

    write_format_spec()
    print("Format spec written")

    print("Done!")
