#!/bin/bash
set -e

# Solution for Phantom Transactions Investigation
# This script investigates the financial data across multiple sources
# to identify the suspect, tampered transactions, and build a forensic report.

cat << 'PYTHON_SOLVE' > /tmp/solve_investigation.py
#!/usr/bin/env python3
"""
Forensic investigation of Meridian Financial Services transaction tampering.

Strategy:
1. Read the system config to understand data formats and token encoding
2. Parse the binary checkpoint files to get original transaction amounts
3. Query the ledger DB to get current (tampered) amounts
4. Compare settlement files against the ledger to identify discrepancies
5. Decode session tokens in access logs to identify the suspect
6. Build a complete forensic report
"""

import sqlite3
import json
import csv
import struct
import base64
import os
from datetime import datetime

# ============================================================
# Step 1: Read system configuration
# ============================================================

with open('/app/data/config/system_state.json', 'r') as f:
    config = json.load(f)

print("=== System Configuration ===")
print(f"System: {config['system']['name']} v{config['system']['version']}")
print(f"Token encoding: {config['authentication']['token_encoding']['method']}")
print(f"Checkpoint format: {config['checkpoints']['format']}")

# Extract token encoding parameters
token_config = config['authentication']['token_encoding']
key_hex = token_config['key_hex']
key_bytes = bytes.fromhex(key_hex)
separator = token_config['separator']

# ============================================================
# Step 2: Build token decoder
# ============================================================

def decode_session_token(token):
    """Decode a session token back to employee ID."""
    parts = token.split('.')
    if len(parts) != 2:
        return None

    b64_part = parts[0]
    crc_part = parts[1]

    try:
        xored = base64.b64decode(b64_part)
        # Reverse XOR with rotating key
        decoded = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(xored))
        employee_id = decoded.decode('utf-8')

        # Verify CRC16
        crc = 0xFFFF
        for b in employee_id.encode('utf-8'):
            crc ^= b
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        expected_crc = format(crc, '04x')

        if expected_crc == crc_part:
            return employee_id
        else:
            return None
    except Exception:
        return None

# ============================================================
# Step 3: Get employee list from DB
# ============================================================

conn = sqlite3.connect('/app/data/ledger.db')
conn.row_factory = sqlite3.Row

employees = {}
for row in conn.execute("SELECT * FROM employees"):
    employees[row['employee_id']] = dict(row)
    print(f"Employee: {row['employee_id']} - {row['name']} ({row['role']}, {row['department']})")

# ============================================================
# Step 4: Parse binary checkpoint files to get original amounts
# ============================================================

print("\n=== Parsing Checkpoint Files ===")
checkpoint_dir = '/app/data/checkpoints/'
checkpoint_records = {}

for filename in sorted(os.listdir(checkpoint_dir)):
    filepath = os.path.join(checkpoint_dir, filename)
    with open(filepath, 'rb') as f:
        # Read header
        magic = f.read(4)
        if magic != b'DELT':
            print(f"  Skipping {filename}: invalid magic")
            continue

        version = struct.unpack('>I', f.read(4))[0]
        num_records = struct.unpack('>I', f.read(4))[0]
        timestamp = struct.unpack('>d', f.read(8))[0]
        ts_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        print(f"\n  Checkpoint: {filename} (v{version}, {num_records} records, {ts_str})")

        for _ in range(num_records):
            txn_id_bytes = f.read(32)
            txn_id = txn_id_bytes.rstrip(b'\x00').decode('utf-8')
            prev_amount = struct.unpack('>d', f.read(8))[0]
            curr_amount = struct.unpack('>d', f.read(8))[0]
            flags = struct.unpack('>I', f.read(4))[0]

            # Store the checkpoint record (earliest snapshot = original value)
            if txn_id not in checkpoint_records:
                checkpoint_records[txn_id] = {
                    'previous_amount': prev_amount,
                    'checkpoint_amount': curr_amount,
                    'flags': flags,
                    'checkpoint_file': filename,
                    'checkpoint_time': ts_str
                }
            print(f"    {txn_id}: prev={prev_amount}, curr={curr_amount}, flags=0x{flags:08x}")

# ============================================================
# Step 5: Query ledger DB for current transaction amounts
# ============================================================

print("\n=== Querying Ledger Database ===")
ledger_transactions = {}
for row in conn.execute("SELECT * FROM transactions WHERE status='settled' ORDER BY transaction_id"):
    txn = dict(row)
    ledger_transactions[txn['transaction_id']] = txn

# ============================================================
# Step 6: Parse settlement files for settlement amounts
# ============================================================

print("\n=== Parsing Settlement Files ===")
settlement_dir = '/app/data/settlements/'
settlement_amounts = {}

for filename in sorted(os.listdir(settlement_dir)):
    filepath = os.path.join(settlement_dir, filename)
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            txn_ref = row['transaction_ref']
            amount = float(row['settled_amount'])
            settlement_amounts[txn_ref] = {
                'amount': amount,
                'file': filename,
                'status': row['status']
            }

# ============================================================
# Step 7: Find discrepancies between ledger and settlements/checkpoints
# ============================================================

print("\n=== Finding Discrepancies ===")
discrepancies = []

for txn_id, ledger_txn in ledger_transactions.items():
    ledger_amount = ledger_txn['amount']

    # Check against settlement records
    if txn_id in settlement_amounts:
        settle_amount = settlement_amounts[txn_id]['amount']
        if abs(ledger_amount - settle_amount) > 0.01:
            discrepancies.append({
                'transaction_id': txn_id,
                'ledger_amount': ledger_amount,
                'settlement_amount': settle_amount,
                'difference': ledger_amount - settle_amount,
                'last_modified': ledger_txn.get('last_modified', ''),
                'modified_by': ledger_txn.get('modified_by', ''),
            })

    # Also check against checkpoint records
    if txn_id in checkpoint_records:
        cp_amount = checkpoint_records[txn_id]['checkpoint_amount']
        if abs(ledger_amount - cp_amount) > 0.01:
            # This transaction was modified after the checkpoint
            existing = next((d for d in discrepancies if d['transaction_id'] == txn_id), None)
            if existing:
                existing['checkpoint_amount'] = cp_amount
            else:
                discrepancies.append({
                    'transaction_id': txn_id,
                    'ledger_amount': ledger_amount,
                    'checkpoint_amount': cp_amount,
                    'difference': ledger_amount - cp_amount,
                    'last_modified': ledger_txn.get('last_modified', ''),
                    'modified_by': ledger_txn.get('modified_by', ''),
                })

for d in discrepancies:
    print(f"  {d['transaction_id']}: ledger={d['ledger_amount']}, "
          f"settlement/checkpoint={d.get('settlement_amount', d.get('checkpoint_amount', '?'))}, "
          f"diff={d['difference']}, modified_by={d.get('modified_by', '?')}")

# ============================================================
# Step 8: Parse access log and decode tokens
# ============================================================

print("\n=== Analyzing Access Log ===")
access_entries = []
tampered_txn_ids = [d['transaction_id'] for d in discrepancies]

with open('/app/data/audit/access.log', 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        # Parse log entry
        ts_end = line.index(']')
        timestamp = line[1:ts_end]

        parts = line[ts_end+2:].split(' ')
        entry = {'timestamp': timestamp}
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                entry[key] = value

        # Decode the session token
        if 'session' in entry:
            emp_id = decode_session_token(entry['session'])
            entry['decoded_employee_id'] = emp_id

        access_entries.append(entry)

# Find MODIFY_TRANSACTION entries for tampered transactions
print("\n=== Suspicious Modifications ===")
modify_events = []
for entry in access_entries:
    if entry.get('action') == 'MODIFY_TRANSACTION' and entry.get('resource') in tampered_txn_ids:
        print(f"  [{entry['timestamp']}] Employee {entry.get('decoded_employee_id', '?')} "
              f"modified {entry['resource']} from IP {entry.get('ip', '?')}")
        modify_events.append(entry)

# Identify the suspect - the employee who made all the modifications
suspect_counts = {}
for event in modify_events:
    emp_id = event.get('decoded_employee_id', 'unknown')
    suspect_counts[emp_id] = suspect_counts.get(emp_id, 0) + 1

suspect_employee_id = max(suspect_counts, key=suspect_counts.get) if suspect_counts else "unknown"
print(f"\nSuspect identified: {suspect_employee_id} ({employees.get(suspect_employee_id, {}).get('name', 'Unknown')})")

# ============================================================
# Step 9: Build tampered transactions list with original amounts
# ============================================================

tampered_transactions = []
for d in sorted(discrepancies, key=lambda x: x['transaction_id']):
    txn_id = d['transaction_id']

    # Get original amount from checkpoint or settlement
    if txn_id in checkpoint_records:
        original = checkpoint_records[txn_id]['checkpoint_amount']
    elif txn_id in settlement_amounts:
        original = settlement_amounts[txn_id]['amount']
    else:
        original = d.get('settlement_amount', d.get('checkpoint_amount', 0))

    tampered_amount = d['ledger_amount']

    # Find the modification timestamp from access log
    mod_event = next((e for e in modify_events if e.get('resource') == txn_id), None)
    mod_timestamp = mod_event['timestamp'] if mod_event else d.get('last_modified', '')

    tampered_transactions.append({
        'transaction_id': txn_id,
        'original_amount': original,
        'tampered_amount': tampered_amount,
        'difference': round(tampered_amount - original, 2),
        'tampering_timestamp': mod_timestamp
    })

total_discrepancy = sum(t['difference'] for t in tampered_transactions)

# ============================================================
# Step 10: Build timeline
# ============================================================

timeline = []

# Add tampering events
for entry in access_entries:
    emp_id = entry.get('decoded_employee_id', '')
    if emp_id == suspect_employee_id:
        resource = entry.get('resource', '')
        action = entry.get('action', '')
        ip = entry.get('ip', '')

        if action in ['LOGIN', 'LOGOUT', 'MODIFY_TRANSACTION', 'VIEW_TRANSACTION', 'DELETE_AUDIT_ENTRY']:
            if resource in tampered_txn_ids or action in ['LOGIN', 'LOGOUT']:
                # Only include off-hours events (before 6am or after 22pm)
                hour = int(entry['timestamp'].split('T')[1].split(':')[0])
                if hour < 6 or hour >= 22:
                    desc = {
                        'LOGIN': f"Suspect {suspect_employee_id} logged in from IP {ip}",
                        'VIEW_TRANSACTION': f"Suspect viewed transaction {resource}",
                        'MODIFY_TRANSACTION': f"Suspect modified transaction {resource}",
                        'DELETE_AUDIT_ENTRY': f"Suspect deleted audit trail entry for {resource}",
                        'LOGOUT': f"Suspect {suspect_employee_id} logged out"
                    }.get(action, f"{action} on {resource}")

                    timeline.append({
                        'timestamp': entry['timestamp'],
                        'event': desc
                    })

# Sort timeline chronologically
timeline.sort(key=lambda x: x['timestamp'])

# ============================================================
# Step 11: Compile evidence sources
# ============================================================

evidence_sources = [
    "/app/data/ledger.db",
    "/app/data/config/system_state.json",
    "/app/data/audit/access.log"
]

# Add specific settlement files
for d in discrepancies:
    txn_id = d['transaction_id']
    if txn_id in settlement_amounts:
        settle_file = f"/app/data/settlements/{settlement_amounts[txn_id]['file']}"
        if settle_file not in evidence_sources:
            evidence_sources.append(settle_file)

# Add checkpoint files
for d in discrepancies:
    txn_id = d['transaction_id']
    if txn_id in checkpoint_records:
        cp_file = f"/app/data/checkpoints/{checkpoint_records[txn_id]['checkpoint_file']}"
        if cp_file not in evidence_sources:
            evidence_sources.append(cp_file)

evidence_sources.sort()

# ============================================================
# Step 12: Generate report
# ============================================================

report = {
    'suspect_employee_id': suspect_employee_id,
    'tampered_transactions': tampered_transactions,
    'total_discrepancy': round(total_discrepancy, 2),
    'timeline': timeline,
    'evidence_sources': evidence_sources
}

os.makedirs('/app/output', exist_ok=True)
with open('/app/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n=== Report Generated ===")
print(f"Suspect: {suspect_employee_id}")
print(f"Tampered transactions: {len(tampered_transactions)}")
print(f"Total discrepancy: ${total_discrepancy:,.2f}")
print(f"Timeline events: {len(timeline)}")
print(f"Evidence sources: {len(evidence_sources)}")
print(f"Report saved to /app/output/report.json")

conn.close()
PYTHON_SOLVE

python3 /tmp/solve_investigation.py
rm /tmp/solve_investigation.py
