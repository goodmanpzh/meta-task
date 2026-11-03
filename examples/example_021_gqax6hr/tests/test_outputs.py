"""
Tests for WAL fragment recovery task.

These tests verify the recovery by:
1. Re-parsing all fragment files independently to compute ground truth
2. Checking recovered stream files match expected content
3. Validating the recovery report structure and values
"""

import json
import os
import re
import zlib
from collections import defaultdict
from pathlib import Path

WAREHOUSE = "/app/warehouse"
RECOVERED_DIR = "/app/recovered"
KNOWN_STREAMS = {"txn_alpha", "txn_beta", "sys_gamma", "audit_delta", "err_epsilon"}
SKIP_EXTENSIONS = {".old", ".bak", ".txt", ".json", ".metadata"}


def compute_crc(stream_id, seq_num_str, payload):
    """Compute CRC32 of the canonical form."""
    data = f"{stream_id}|{seq_num_str}|{payload}"
    return zlib.crc32(data.encode('utf-8')) & 0xFFFFFFFF


def get_ground_truth():
    """
    Re-parse all fragment files to compute the ground truth recovery.
    Returns (recovered_dict, corrupted_count, duplicate_count)
    """
    recovered = defaultdict(dict)  # stream_id -> {seq_num -> payload}
    total_corrupted = 0
    total_duplicates = 0

    for root, dirs, files in os.walk(WAREHOUSE):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext in SKIP_EXTENSIONS:
                continue
            if fname.startswith('.'):
                continue
            # Skip FORMAT_SPEC.txt explicitly
            if fname == "FORMAT_SPEC.txt":
                continue

            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if not line.strip():
                            continue

                        parts = line.split('|', 3)
                        if len(parts) < 4:
                            total_corrupted += 1
                            continue

                        stream_id, seq_str, crc_hex, payload = parts

                        if stream_id not in KNOWN_STREAMS:
                            total_corrupted += 1
                            continue

                        if not re.match(r'^\d{6}$', seq_str):
                            total_corrupted += 1
                            continue

                        if not re.match(r'^[0-9a-f]{8}$', crc_hex):
                            total_corrupted += 1
                            continue

                        expected_crc = compute_crc(stream_id, seq_str, payload)
                        if expected_crc != int(crc_hex, 16):
                            total_corrupted += 1
                            continue

                        seq_num = int(seq_str)
                        if seq_num in recovered[stream_id]:
                            total_duplicates += 1
                        else:
                            recovered[stream_id][seq_num] = payload
            except Exception:
                continue

    return dict(recovered), total_corrupted, total_duplicates


# Compute ground truth once for all tests
_ground_truth = None


def ground_truth():
    global _ground_truth
    if _ground_truth is None:
        _ground_truth = get_ground_truth()
    return _ground_truth


# === Test: recover.sh exists and is executable ===

def test_recover_script_exists():
    """The recovery script must exist at /app/recover.sh"""
    p = Path("/app/recover.sh")
    assert p.exists(), "recover.sh not found at /app/recover.sh"
    # Check it's a file (not directory)
    assert p.is_file(), "/app/recover.sh is not a regular file"


# === Test: All stream files exist ===

def test_all_stream_files_exist():
    """Each known stream must have a recovered .log file."""
    for stream_id in KNOWN_STREAMS:
        p = Path(RECOVERED_DIR) / f"{stream_id}.log"
        assert p.exists(), f"Missing recovered file: {p}"
        assert p.is_file(), f"{p} is not a regular file"


# === Test: REPORT.json exists and is valid JSON ===

def test_report_exists_and_valid_json():
    """REPORT.json must exist and be parseable JSON."""
    p = Path(RECOVERED_DIR) / "REPORT.json"
    assert p.exists(), "REPORT.json not found"
    content = p.read_text()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"REPORT.json is not valid JSON: {e}")
    assert isinstance(data, dict), "REPORT.json root must be an object"


# === Test: Report structure ===

def test_report_structure():
    """REPORT.json must have the required keys and structure."""
    report = json.loads(Path(RECOVERED_DIR, "REPORT.json").read_text())

    assert "streams" in report, "Missing 'streams' key in report"
    assert "total_recovered" in report, "Missing 'total_recovered' key"
    assert "total_corrupted_lines" in report, "Missing 'total_corrupted_lines' key"
    assert "total_duplicate_lines" in report, "Missing 'total_duplicate_lines' key"

    assert isinstance(report["streams"], dict), "'streams' must be a dict"
    assert isinstance(report["total_recovered"], int), "'total_recovered' must be int"
    assert isinstance(report["total_corrupted_lines"], int), "'total_corrupted_lines' must be int"
    assert isinstance(report["total_duplicate_lines"], int), "'total_duplicate_lines' must be int"

    # Check each stream entry
    for stream_id in KNOWN_STREAMS:
        assert stream_id in report["streams"], f"Stream '{stream_id}' missing from report"
        s = report["streams"][stream_id]
        assert "recovered_count" in s, f"Missing 'recovered_count' for {stream_id}"
        assert "missing_sequences" in s, f"Missing 'missing_sequences' for {stream_id}"
        assert "first_seq" in s, f"Missing 'first_seq' for {stream_id}"
        assert "last_seq" in s, f"Missing 'last_seq' for {stream_id}"
        assert isinstance(s["recovered_count"], int), f"'recovered_count' for {stream_id} must be int"
        assert isinstance(s["missing_sequences"], list), f"'missing_sequences' for {stream_id} must be list"
        assert isinstance(s["first_seq"], int), f"'first_seq' for {stream_id} must be int"
        assert isinstance(s["last_seq"], int), f"'last_seq' for {stream_id} must be int"


# === Test: Recovered counts match ground truth ===

def test_recovered_counts():
    """Number of recovered entries per stream must match ground truth."""
    recovered, _, _ = ground_truth()
    report = json.loads(Path(RECOVERED_DIR, "REPORT.json").read_text())

    for stream_id in KNOWN_STREAMS:
        expected_count = len(recovered.get(stream_id, {}))
        actual_count = report["streams"][stream_id]["recovered_count"]
        assert actual_count == expected_count, (
            f"Stream {stream_id}: expected {expected_count} recovered, got {actual_count}"
        )


# === Test: Total recovered matches ===

def test_total_recovered():
    """total_recovered must be the sum across all streams."""
    recovered, _, _ = ground_truth()
    report = json.loads(Path(RECOVERED_DIR, "REPORT.json").read_text())

    expected_total = sum(len(entries) for entries in recovered.values())
    assert report["total_recovered"] == expected_total, (
        f"Expected total_recovered={expected_total}, got {report['total_recovered']}"
    )


# === Test: Stream file content matches ground truth ===

def test_stream_file_contents():
    """
    Each recovered stream file must contain exactly the correct payloads
    in sequence order.
    """
    recovered, _, _ = ground_truth()

    for stream_id in KNOWN_STREAMS:
        fpath = Path(RECOVERED_DIR) / f"{stream_id}.log"
        if not fpath.exists():
            raise AssertionError(f"Missing file: {fpath}")

        actual_lines = fpath.read_text().rstrip('\n').split('\n') if fpath.read_text().strip() else []

        expected_entries = recovered.get(stream_id, {})
        expected_lines = [expected_entries[seq] for seq in sorted(expected_entries.keys())]

        assert len(actual_lines) == len(expected_lines), (
            f"Stream {stream_id}: expected {len(expected_lines)} lines, got {len(actual_lines)}"
        )

        # Check first 5 and last 5 lines for detailed error messages
        mismatches = []
        for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines)):
            if actual != expected:
                mismatches.append(i)

        if mismatches:
            first_bad = mismatches[0]
            raise AssertionError(
                f"Stream {stream_id}: {len(mismatches)} line mismatches. "
                f"First mismatch at line {first_bad}: "
                f"expected={expected_lines[first_bad][:80]!r}... "
                f"got={actual_lines[first_bad][:80]!r}..."
            )


# === Test: Missing sequences are correct ===

def test_missing_sequences():
    """missing_sequences must list exactly the gaps in the recovered range."""
    recovered, _, _ = ground_truth()
    report = json.loads(Path(RECOVERED_DIR, "REPORT.json").read_text())

    for stream_id in KNOWN_STREAMS:
        entries = recovered.get(stream_id, {})
        if not entries:
            continue

        seq_nums = sorted(entries.keys())
        first_seq = seq_nums[0]
        last_seq = seq_nums[-1]
        expected_missing = sorted(set(range(first_seq, last_seq + 1)) - set(seq_nums))

        actual_missing = sorted(report["streams"][stream_id]["missing_sequences"])

        assert actual_missing == expected_missing, (
            f"Stream {stream_id}: missing_sequences mismatch. "
            f"Expected {expected_missing}, got {actual_missing}"
        )


# === Test: first_seq and last_seq are correct ===

def test_first_last_seq():
    """first_seq and last_seq must match the actual range of recovered entries."""
    recovered, _, _ = ground_truth()
    report = json.loads(Path(RECOVERED_DIR, "REPORT.json").read_text())

    for stream_id in KNOWN_STREAMS:
        entries = recovered.get(stream_id, {})
        if not entries:
            continue

        seq_nums = sorted(entries.keys())
        expected_first = seq_nums[0]
        expected_last = seq_nums[-1]

        s = report["streams"][stream_id]
        assert s["first_seq"] == expected_first, (
            f"Stream {stream_id}: expected first_seq={expected_first}, got {s['first_seq']}"
        )
        assert s["last_seq"] == expected_last, (
            f"Stream {stream_id}: expected last_seq={expected_last}, got {s['last_seq']}"
        )


# === Test: Corrupted line count is reasonable ===

def test_corrupted_lines_count():
    """
    The corrupted line count should match ground truth computation.
    """
    _, expected_corrupted, _ = ground_truth()
    report = json.loads(Path(RECOVERED_DIR, "REPORT.json").read_text())

    actual = report["total_corrupted_lines"]
    assert actual == expected_corrupted, (
        f"total_corrupted_lines: expected {expected_corrupted}, got {actual}"
    )


# === Test: Duplicate line count is reasonable ===

def test_duplicate_lines_count():
    """
    The duplicate line count should match ground truth computation.
    """
    _, _, expected_dupes = ground_truth()
    report = json.loads(Path(RECOVERED_DIR, "REPORT.json").read_text())

    actual = report["total_duplicate_lines"]
    assert actual == expected_dupes, (
        f"total_duplicate_lines: expected {expected_dupes}, got {actual}"
    )


# === Test: No extra files in recovered directory ===

def test_no_extra_files():
    """
    The recovered directory should only contain the expected stream files
    and REPORT.json.
    """
    expected_files = {f"{sid}.log" for sid in KNOWN_STREAMS} | {"REPORT.json"}
    actual_files = set(os.listdir(RECOVERED_DIR))

    extra = actual_files - expected_files
    assert not extra, f"Unexpected files in {RECOVERED_DIR}: {extra}"


# === Test: No corrupted entries in output ===

def test_no_corrupted_in_output():
    """
    Verify that none of the output files contain entries that fail CRC validation.
    Re-check by parsing the output files and verifying each payload exists in ground truth.
    """
    recovered, _, _ = ground_truth()

    for stream_id in KNOWN_STREAMS:
        fpath = Path(RECOVERED_DIR) / f"{stream_id}.log"
        if not fpath.exists():
            continue

        entries = recovered.get(stream_id, {})
        valid_payloads = set(entries.values())

        lines = fpath.read_text().rstrip('\n').split('\n') if fpath.read_text().strip() else []
        for i, line in enumerate(lines):
            assert line in valid_payloads, (
                f"Stream {stream_id} line {i}: payload not in ground truth valid entries. "
                f"Got: {line[:80]!r}..."
            )


# === Test: Payloads with special characters preserved correctly ===

def test_special_characters_preserved():
    """
    Check that payloads containing special shell characters (|, $, `, etc.)
    are preserved exactly.
    """
    recovered, _, _ = ground_truth()

    special_chars = {'|', '$', '`', '"', "'", '\\', '&', ';', '<', '>', '!', '#'}

    for stream_id in KNOWN_STREAMS:
        entries = recovered.get(stream_id, {})
        fpath = Path(RECOVERED_DIR) / f"{stream_id}.log"
        if not fpath.exists():
            continue

        actual_lines = fpath.read_text().rstrip('\n').split('\n') if fpath.read_text().strip() else []
        expected_lines = [entries[seq] for seq in sorted(entries.keys())]

        # Find entries with special characters and verify they match
        special_count = 0
        for actual, expected in zip(actual_lines, expected_lines):
            if any(c in expected for c in special_chars):
                special_count += 1
                assert actual == expected, (
                    f"Special char payload mismatch in {stream_id}: "
                    f"expected={expected[:80]!r}, got={actual[:80]!r}"
                )

        # There should be a reasonable number of entries with special chars
        assert special_count > 0, (
            f"Stream {stream_id}: no entries with special characters found"
        )
