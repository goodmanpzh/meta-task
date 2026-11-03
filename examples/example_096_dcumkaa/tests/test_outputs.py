#!/usr/bin/env python3
"""
Tests for the Phantom Transactions Investigation.

These tests verify that the agent correctly:
1. Identified the suspect employee
2. Found all tampered transactions
3. Recovered original amounts from checkpoints/settlements
4. Built a chronological timeline
5. Listed evidence sources

Tests compute expected values from the raw data sources rather than
hardcoding answers to avoid leakage.
"""

import json
import os
import sqlite3
import csv
import struct
import base64
from datetime import datetime


def load_report():
    """Load the agent's forensic report."""
    report_path = "/app/output/report.json"
    assert os.path.exists(report_path), f"Report file not found at {report_path}"
    with open(report_path, 'r') as f:
        return json.load(f)


def load_config():
    """Load system configuration."""
    with open('/app/data/config/system_state.json', 'r') as f:
        return json.load(f)


def decode_token(token, key_hex):
    """Decode a session token using the config-specified method."""
    key_bytes = bytes.fromhex(key_hex)
    parts = token.split('.')
    if len(parts) != 2:
        return None
    try:
        xored = base64.b64decode(parts[0])
        decoded = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(xored))
        return decoded.decode('utf-8')
    except Exception:
        return None


def get_settlement_amounts():
    """Read all settlement files and return transaction -> amount mapping."""
    settlement_dir = '/app/data/settlements/'
    amounts = {}
    for filename in os.listdir(settlement_dir):
        if filename.endswith('.csv'):
            with open(os.path.join(settlement_dir, filename), 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    amounts[row['transaction_ref']] = float(row['settled_amount'])
    return amounts


def get_checkpoint_amounts():
    """Parse all checkpoint files and return transaction -> original amount."""
    cp_dir = '/app/data/checkpoints/'
    amounts = {}
    for filename in sorted(os.listdir(cp_dir)):
        filepath = os.path.join(cp_dir, filename)
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            if magic != b'DELT':
                continue
            _ = struct.unpack('>I', f.read(4))[0]  # version
            num_records = struct.unpack('>I', f.read(4))[0]
            _ = struct.unpack('>d', f.read(8))[0]  # timestamp

            for _ in range(num_records):
                txn_id = f.read(32).rstrip(b'\x00').decode('utf-8')
                prev_amt = struct.unpack('>d', f.read(8))[0]
                curr_amt = struct.unpack('>d', f.read(8))[0]
                _ = struct.unpack('>I', f.read(4))[0]  # flags
                if txn_id not in amounts:
                    amounts[txn_id] = curr_amt
    return amounts


def find_tampered_transactions():
    """
    Cross-reference ledger, settlements, and checkpoints to find
    tampered transactions. Returns a dict of txn_id -> (original, tampered).
    """
    conn = sqlite3.connect('/app/data/ledger.db')
    conn.row_factory = sqlite3.Row

    ledger = {}
    for row in conn.execute("SELECT transaction_id, amount FROM transactions WHERE status='settled'"):
        ledger[row['transaction_id']] = row['amount']
    conn.close()

    settlement_amounts = get_settlement_amounts()
    checkpoint_amounts = get_checkpoint_amounts()

    tampered = {}
    for txn_id, ledger_amt in ledger.items():
        original = None
        # Check settlements
        if txn_id in settlement_amounts:
            settle_amt = settlement_amounts[txn_id]
            if abs(ledger_amt - settle_amt) > 0.01:
                original = settle_amt
        # Check checkpoints
        if txn_id in checkpoint_amounts:
            cp_amt = checkpoint_amounts[txn_id]
            if abs(ledger_amt - cp_amt) > 0.01:
                original = cp_amt

        if original is not None:
            tampered[txn_id] = (original, ledger_amt)

    return tampered


def find_suspect_from_logs():
    """
    Parse access logs and decode tokens to find who modified
    tampered transactions during off-hours.
    """
    config = load_config()
    key_hex = config['authentication']['token_encoding']['key_hex']

    tampered = find_tampered_transactions()
    tampered_ids = set(tampered.keys())

    modifier_counts = {}
    with open('/app/data/audit/access.log', 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if 'action=MODIFY_TRANSACTION' not in line:
                continue

            # Extract resource
            parts = line.split(' ')
            resource = None
            token = None
            for part in parts:
                if part.startswith('resource='):
                    resource = part.split('=', 1)[1]
                if part.startswith('session='):
                    token = part.split('=', 1)[1]

            if resource in tampered_ids and token:
                emp_id = decode_token(token, key_hex)
                if emp_id:
                    modifier_counts[emp_id] = modifier_counts.get(emp_id, 0) + 1

    if modifier_counts:
        return max(modifier_counts, key=modifier_counts.get)
    return None


# ============================================================
# TESTS
# ============================================================


def test_report_exists_and_valid_json():
    """Test that the report file exists and is valid JSON."""
    report_path = "/app/output/report.json"
    assert os.path.exists(report_path), "Report file not found"
    with open(report_path, 'r') as f:
        data = json.load(f)
    assert isinstance(data, dict), "Report should be a JSON object"


def test_report_has_required_fields():
    """Test that the report contains all required top-level fields."""
    report = load_report()
    required_fields = [
        "suspect_employee_id",
        "tampered_transactions",
        "total_discrepancy",
        "timeline",
        "evidence_sources"
    ]
    for field in required_fields:
        assert field in report, f"Missing required field: {field}"


def test_suspect_identification():
    """Test that the correct suspect was identified by cross-referencing sources."""
    report = load_report()
    expected_suspect = find_suspect_from_logs()
    assert expected_suspect is not None, "Could not determine suspect from source data"
    assert report['suspect_employee_id'] == expected_suspect, \
        f"Wrong suspect: got {report['suspect_employee_id']}, expected {expected_suspect}"


def test_tampered_transaction_count():
    """Test that all tampered transactions were found."""
    report = load_report()
    expected_tampered = find_tampered_transactions()
    report_txn_ids = {t['transaction_id'] for t in report['tampered_transactions']}
    expected_ids = set(expected_tampered.keys())

    assert report_txn_ids == expected_ids, \
        f"Transaction ID mismatch. Missing: {expected_ids - report_txn_ids}, Extra: {report_txn_ids - expected_ids}"


def test_tampered_transaction_amounts():
    """Test that original and tampered amounts are correct for each transaction."""
    report = load_report()
    expected_tampered = find_tampered_transactions()

    for txn in report['tampered_transactions']:
        txn_id = txn['transaction_id']
        assert txn_id in expected_tampered, f"Unexpected transaction: {txn_id}"

        expected_original, expected_tampered_amt = expected_tampered[txn_id]

        assert abs(txn['original_amount'] - expected_original) < 0.01, \
            f"Wrong original amount for {txn_id}: got {txn['original_amount']}, expected {expected_original}"
        assert abs(txn['tampered_amount'] - expected_tampered_amt) < 0.01, \
            f"Wrong tampered amount for {txn_id}: got {txn['tampered_amount']}, expected {expected_tampered_amt}"
        assert abs(txn['difference'] - (expected_tampered_amt - expected_original)) < 0.01, \
            f"Wrong difference for {txn_id}"


def test_total_discrepancy():
    """Test that total discrepancy matches sum of individual differences."""
    report = load_report()
    expected_tampered = find_tampered_transactions()

    expected_total = sum(tampered - original for original, tampered in expected_tampered.values())

    assert abs(report['total_discrepancy'] - expected_total) < 0.01, \
        f"Wrong total discrepancy: got {report['total_discrepancy']}, expected {expected_total}"


def test_tampered_transactions_sorted():
    """Test that tampered transactions are sorted by transaction_id."""
    report = load_report()
    txn_ids = [t['transaction_id'] for t in report['tampered_transactions']]
    assert txn_ids == sorted(txn_ids), "Tampered transactions must be sorted by transaction_id"


def test_tampering_timestamps_present():
    """Test that each tampered transaction has a valid ISO timestamp."""
    report = load_report()
    for txn in report['tampered_transactions']:
        ts = txn.get('tampering_timestamp', '')
        assert ts, f"Missing tampering_timestamp for {txn['transaction_id']}"
        # Verify it's a valid ISO-ish timestamp
        try:
            datetime.fromisoformat(ts)
        except ValueError:
            assert False, f"Invalid timestamp format for {txn['transaction_id']}: {ts}"


def test_tampering_timestamps_are_off_hours():
    """Test that all tampering timestamps are during off-hours (before 6am)."""
    report = load_report()
    for txn in report['tampered_transactions']:
        ts = txn['tampering_timestamp']
        dt = datetime.fromisoformat(ts)
        hour = dt.hour
        assert hour < 6 or hour >= 22, \
            f"Tampering timestamp for {txn['transaction_id']} is not off-hours: {ts}"


def test_timeline_not_empty():
    """Test that the timeline contains events."""
    report = load_report()
    assert len(report['timeline']) > 0, "Timeline should not be empty"


def test_timeline_chronological():
    """Test that timeline events are in chronological order."""
    report = load_report()
    timestamps = [e['timestamp'] for e in report['timeline']]
    assert timestamps == sorted(timestamps), "Timeline must be in chronological order"


def test_timeline_covers_all_tampering_sessions():
    """Test that the timeline includes events for each tampering session."""
    report = load_report()
    tampered_txn_ids = {t['transaction_id'] for t in report['tampered_transactions']}

    # Check that each tampered transaction has at least one timeline event mentioning it
    timeline_text = ' '.join(e['event'] for e in report['timeline'])
    for txn_id in tampered_txn_ids:
        assert txn_id in timeline_text, \
            f"Timeline should mention tampered transaction {txn_id}"


def test_evidence_sources():
    """Test that evidence sources include the key data files."""
    report = load_report()
    sources = report['evidence_sources']

    assert isinstance(sources, list), "evidence_sources should be a list"
    assert len(sources) >= 3, "Should reference at least 3 evidence sources"

    # Must include the ledger database
    assert any('ledger.db' in s for s in sources), "Must cite ledger.db as evidence"
    # Must include the access log
    assert any('access.log' in s for s in sources), "Must cite access.log as evidence"
    # Must include at least one checkpoint or settlement file
    has_checkpoint = any('checkpoint' in s for s in sources)
    has_settlement = any('settlement' in s for s in sources)
    assert has_checkpoint or has_settlement, \
        "Must cite at least one checkpoint or settlement file as evidence"


def test_amounts_are_numbers():
    """Test that all amount fields are numeric, not strings."""
    report = load_report()
    for txn in report['tampered_transactions']:
        assert isinstance(txn['original_amount'], (int, float)), \
            f"original_amount must be numeric for {txn['transaction_id']}"
        assert isinstance(txn['tampered_amount'], (int, float)), \
            f"tampered_amount must be numeric for {txn['transaction_id']}"
        assert isinstance(txn['difference'], (int, float)), \
            f"difference must be numeric for {txn['transaction_id']}"
    assert isinstance(report['total_discrepancy'], (int, float)), \
        "total_discrepancy must be numeric"
