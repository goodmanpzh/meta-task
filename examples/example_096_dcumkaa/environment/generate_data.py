#!/usr/bin/env python3
"""
Generate the Phantom Transactions investigation environment.

This creates a complex, multi-source forensic puzzle where the agent must:
1. Query and analyze a SQLite ledger database
2. Parse settlement CSV files and compare against the ledger
3. Decode session tokens in access logs to identify the suspect
4. Parse binary delta-encoded checkpoint files to find original values
5. Cross-reference all sources to build a complete forensic report

The scenario: Employee E-1047 (Marcus Webb) tampered with 7 transactions
during off-hours access sessions, inflating amounts and skimming the difference.
"""

import sqlite3
import json
import csv
import struct
import hashlib
import os
import base64
import random
from datetime import datetime, timedelta

random.seed(42)

# ============================================================
# CONSTANTS - The "ground truth" of the investigation
# ============================================================

SUSPECT_EMPLOYEE_ID = "E-1047"
SUSPECT_NAME = "Marcus Webb"

EMPLOYEES = [
    {"id": "E-1001", "name": "Sarah Chen", "role": "analyst", "department": "trading"},
    {"id": "E-1015", "name": "David Park", "role": "senior_analyst", "department": "trading"},
    {"id": "E-1023", "name": "Lisa Monroe", "role": "manager", "department": "compliance"},
    {"id": "E-1032", "name": "James Wright", "role": "analyst", "department": "settlements"},
    {"id": "E-1047", "name": "Marcus Webb", "role": "senior_analyst", "department": "settlements"},
    {"id": "E-1058", "name": "Nina Rodriguez", "role": "admin", "department": "IT"},
    {"id": "E-1063", "name": "Tom Baker", "role": "analyst", "department": "trading"},
    {"id": "E-1071", "name": "Amy Foster", "role": "manager", "department": "trading"},
]

TOKEN_ROTATE_KEY = b'\x5a\x3c\x7e\x19\x42\x6b'

def encode_session_token(employee_id):
    """Encode employee ID into an obfuscated session token."""
    id_bytes = employee_id.encode('utf-8')
    xored = bytes(b ^ TOKEN_ROTATE_KEY[i % len(TOKEN_ROTATE_KEY)] for i, b in enumerate(id_bytes))
    part1 = base64.b64encode(xored).decode('ascii')
    crc = 0xFFFF
    for b in employee_id.encode('utf-8'):
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    part2 = format(crc, '04x')
    return f"{part1}.{part2}"

EMPLOYEE_TOKENS = {emp["id"]: encode_session_token(emp["id"]) for emp in EMPLOYEES}

# Tampered transactions
# All tampered transaction dates must be weekdays (Mon-Fri)
# Mar 2024 weekdays: 1(F), 4(M), 5(T), 6(W), 7(Th), 8(F), 11(M), 12(T), 13(W), 14(Th), 15(F),
#   18(M), 19(T), 20(W), 21(Th), 22(F), 25(M), 26(T), 27(W), 28(Th), 29(F)
TAMPERED_TXN_IDS = [
    "TXN-20240312-0042", "TXN-20240318-0108", "TXN-20240319-0067",
    "TXN-20240322-0091", "TXN-20240325-0033", "TXN-20240327-0145",
    "TXN-20240329-0072"
]

ORIGINAL_AMOUNTS = [15400.00, 8750.00, 22100.00, 6300.00, 31500.00, 9800.00, 18200.00]
TAMPERED_AMOUNTS = [22600.00, 13950.00, 28300.00, 11500.00, 38700.00, 15050.00, 23250.00]

# Tampering happens in the early morning after the transaction date
TAMPERING_TIMESTAMPS = [
    "2024-03-13T02:14:33",
    "2024-03-19T01:47:12",
    "2024-03-20T03:22:45",
    "2024-03-23T02:08:19",
    "2024-03-26T01:33:57",
    "2024-03-28T02:55:41",
    "2024-03-30T01:19:08",
]


# ============================================================
# Step 1: Generate the canonical set of transactions ONCE,
# then write them to both ledger and settlements
# ============================================================

def generate_all_transactions():
    """Generate a single canonical transaction list used by all data sources."""
    transactions = []
    base_date = datetime(2024, 3, 1)

    for day_offset in range(31):
        date = base_date + timedelta(days=day_offset)
        if date.weekday() >= 5:
            continue

        date_str = date.strftime("%Y%m%d")
        num_txns = random.randint(5, 8)

        for seq in range(1, num_txns + 1):
            txn_id = f"TXN-{date.strftime('%Y%m%d')}-{seq:04d}"

            is_tampered = txn_id in TAMPERED_TXN_IDS

            if is_tampered:
                idx = TAMPERED_TXN_IDS.index(txn_id)
                original_amount = ORIGINAL_AMOUNTS[idx]
                ledger_amount = TAMPERED_AMOUNTS[idx]
                account = random.choice(["ACC-002", "ACC-003", "ACC-004"])
                last_modified = TAMPERING_TIMESTAMPS[idx]
                modified_by = SUSPECT_EMPLOYEE_ID
                txn_type = "transfer"
                status = "settled"
                notes = random.choice([
                    "Batch reconciliation", "Post-settlement correction",
                    "Amount verified", "Routine processing",
                    "Standard transfer", "Reconciled", "Processed"
                ])
            else:
                original_amount = round(random.uniform(1000, 50000), 2)
                ledger_amount = original_amount  # Not tampered = same in both
                account = random.choice(["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005", "ACC-007"])
                last_modified = date.strftime("%Y-%m-%dT%H:%M:%S")
                modified_by = random.choice([e["id"] for e in EMPLOYEES])
                txn_type = random.choice(["credit", "debit", "transfer"])
                status = random.choice(["settled", "settled", "settled", "pending", "cleared"])
                notes = random.choice([
                    "Batch reconciliation", "Standard transfer",
                    "Routine processing", "Automated entry",
                    "Client instruction", "Wire transfer",
                    "Reconciled", "Processed", "Amount verified"
                ])

            counterparty = f"EXT-{random.randint(1000,9999)}"
            created = date.strftime("%Y-%m-%dT") + f"{random.randint(8,17):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            settled_at = None
            if status == "settled":
                settle_date = date + timedelta(days=random.randint(0, 2))
                settled_at = settle_date.strftime("%Y-%m-%dT") + f"{random.randint(8,17):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"

            transactions.append({
                "transaction_id": txn_id,
                "account_id": account,
                "counterparty_account": counterparty,
                "original_amount": original_amount,  # pre-tampering
                "ledger_amount": ledger_amount,       # in the DB (tampered for 7)
                "currency": "USD",
                "transaction_type": txn_type,
                "status": status,
                "created_at": created,
                "settled_at": settled_at,
                "last_modified": last_modified,
                "modified_by": modified_by,
                "notes": notes,
                "is_tampered": is_tampered,
                "date": date,
            })

    # Ensure all 7 tampered transactions exist
    existing_ids = {t["transaction_id"] for t in transactions}
    for i, txn_id in enumerate(TAMPERED_TXN_IDS):
        if txn_id not in existing_ids:
            date_str = txn_id.split('-')[1]
            date = datetime.strptime(date_str, "%Y%m%d")
            account = random.choice(["ACC-002", "ACC-003", "ACC-004"])
            counterparty = f"EXT-{random.randint(1000,9999)}"
            created = date.strftime("%Y-%m-%dT") + f"{random.randint(8,17):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            settled_at = (date + timedelta(days=1)).strftime("%Y-%m-%dT") + f"{random.randint(8,17):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            transactions.append({
                "transaction_id": txn_id,
                "account_id": account,
                "counterparty_account": counterparty,
                "original_amount": ORIGINAL_AMOUNTS[i],
                "ledger_amount": TAMPERED_AMOUNTS[i],
                "currency": "USD",
                "transaction_type": "transfer",
                "status": "settled",
                "created_at": created,
                "settled_at": settled_at,
                "last_modified": TAMPERING_TIMESTAMPS[i],
                "modified_by": SUSPECT_EMPLOYEE_ID,
                "notes": "Routine processing",
                "is_tampered": True,
                "date": date,
            })

    transactions.sort(key=lambda t: t["transaction_id"])
    return transactions


# ============================================================
# GENERATE SQLITE LEDGER DATABASE
# ============================================================

def create_ledger_db(path, transactions):
    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute('''CREATE TABLE employees (
        employee_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        hire_date TEXT,
        clearance_level INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE accounts (
        account_id TEXT PRIMARY KEY,
        account_name TEXT NOT NULL,
        account_type TEXT NOT NULL,
        balance REAL DEFAULT 0.0,
        currency TEXT DEFAULT 'USD',
        status TEXT DEFAULT 'active'
    )''')

    c.execute('''CREATE TABLE transactions (
        transaction_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        counterparty_account TEXT,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'USD',
        transaction_type TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        settled_at TEXT,
        last_modified TEXT,
        modified_by TEXT,
        notes TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
    )''')

    c.execute('''CREATE TABLE audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id TEXT NOT NULL,
        field_name TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        changed_by TEXT,
        changed_at TEXT
    )''')

    for emp in EMPLOYEES:
        c.execute("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?)",
                  (emp["id"], emp["name"], emp["role"], emp["department"],
                   "2022-01-15" if emp["id"] != SUSPECT_EMPLOYEE_ID else "2023-06-01",
                   2 if emp["role"] in ["manager", "admin"] else 1))

    accounts = [
        ("ACC-001", "Meridian Operating", "operating", 2450000.00, "USD", "active"),
        ("ACC-002", "Client Trust Fund A", "trust", 8750000.00, "USD", "active"),
        ("ACC-003", "Client Trust Fund B", "trust", 5200000.00, "USD", "active"),
        ("ACC-004", "Settlement Clearing", "clearing", 1200000.00, "USD", "active"),
        ("ACC-005", "Fee Revenue", "revenue", 340000.00, "USD", "active"),
        ("ACC-006", "Suspense Account", "suspense", 0.00, "USD", "active"),
        ("ACC-007", "External Transfer Pool", "transfer", 780000.00, "USD", "active"),
        ("ACC-008", "Reserve Fund", "reserve", 3100000.00, "USD", "active"),
    ]
    c.executemany("INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?)", accounts)

    for txn in transactions:
        c.execute("""INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (txn["transaction_id"], txn["account_id"], txn["counterparty_account"],
                   txn["ledger_amount"],  # TAMPERED amount for the 7 bad ones
                   txn["currency"], txn["transaction_type"], txn["status"],
                   txn["created_at"], txn["settled_at"], txn["last_modified"],
                   txn["modified_by"], txn["notes"]))

    # Add audit trail for NORMAL modifications only
    # The tamperer deleted their audit trail entries
    for txn in transactions:
        if not txn["is_tampered"] and random.random() < 0.3 and txn["status"] == "settled":
            c.execute("""INSERT INTO audit_trail (table_name, record_id, field_name, old_value, new_value, changed_by, changed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      ("transactions", txn["transaction_id"], "status", "pending", "settled",
                       random.choice([e["id"] for e in EMPLOYEES]),
                       txn["created_at"]))

    conn.commit()
    conn.close()
    print(f"Created ledger database with {len(transactions)} transactions")


# ============================================================
# GENERATE SETTLEMENT CSV FILES
# ============================================================

def create_settlement_files(directory, transactions):
    os.makedirs(directory, exist_ok=True)

    # Only settled transactions appear in settlement files
    settled = [t for t in transactions if t["status"] == "settled"]

    # Group by week
    weeks = {
        "settlement_week11_2024.csv": (datetime(2024, 3, 11), datetime(2024, 3, 15)),
        "settlement_week12_2024.csv": (datetime(2024, 3, 18), datetime(2024, 3, 22)),
        "settlement_week13_2024.csv": (datetime(2024, 3, 25), datetime(2024, 3, 29)),
    }

    for filename, (week_start, week_end) in weeks.items():
        filepath = os.path.join(directory, filename)
        rows = []

        for txn in settled:
            txn_date = txn["date"]
            if week_start <= txn_date <= week_end:
                rows.append({
                    "settlement_ref": f"STL-{random.randint(100000,999999)}",
                    "transaction_ref": txn["transaction_id"],
                    "settled_amount": txn["original_amount"],  # ORIGINAL amount (pre-tampering)
                    "currency": txn["currency"],
                    "settlement_date": (txn_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "batch_reference": f"BATCH-{week_start.strftime('%Y%m%d')}-{random.randint(100,999)}",
                    "status": "CONFIRMED",
                    "counterparty_ref": f"CP-{random.randint(1000,9999)}"
                })

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "settlement_ref", "transaction_ref", "settled_amount",
                "currency", "settlement_date", "batch_reference",
                "status", "counterparty_ref"
            ])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        print(f"Created {filepath} with {len(rows)} records")


# ============================================================
# GENERATE ACCESS LOG (with encoded session tokens)
# ============================================================

def create_access_log(path):
    lines = []
    base_date = datetime(2024, 3, 1)

    for day_offset in range(31):
        date = base_date + timedelta(days=day_offset)

        # Normal business-hours access
        for _ in range(random.randint(10, 25)):
            emp = random.choice(EMPLOYEES)
            token = EMPLOYEE_TOKENS[emp["id"]]
            hour = random.randint(7, 18)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ts = date.replace(hour=hour, minute=minute, second=second)
            action = random.choice([
                "VIEW_TRANSACTION", "LIST_TRANSACTIONS", "VIEW_ACCOUNT",
                "GENERATE_REPORT", "VIEW_SETTLEMENT", "SEARCH_RECORDS",
                "VIEW_DASHBOARD", "EXPORT_DATA"
            ])
            resource = random.choice([
                f"TXN-{date.strftime('%Y%m%d')}-{random.randint(1,200):04d}",
                f"ACC-{random.randint(1,8):03d}",
                "REPORT_MODULE", "DASHBOARD"
            ])
            status_code = random.choice([200, 200, 200, 200, 403, 200])
            lines.append(f"[{ts.strftime('%Y-%m-%dT%H:%M:%S')}] session={token} action={action} resource={resource} status={status_code} ip=10.0.{random.randint(1,5)}.{random.randint(10,250)}")

    # Suspicious off-hours access by the suspect
    for i, ts_str in enumerate(TAMPERING_TIMESTAMPS):
        token = EMPLOYEE_TOKENS[SUSPECT_EMPLOYEE_ID]
        txn_id = TAMPERED_TXN_IDS[i]
        ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")

        login_ts = ts - timedelta(minutes=random.randint(3, 7))
        lines.append(f"[{login_ts.strftime('%Y-%m-%dT%H:%M:%S')}] session={token} action=LOGIN resource=AUTH_SYSTEM status=200 ip=192.168.1.{random.randint(100,200)}")

        view_ts = ts - timedelta(minutes=random.randint(1, 2))
        lines.append(f"[{view_ts.strftime('%Y-%m-%dT%H:%M:%S')}] session={token} action=VIEW_TRANSACTION resource={txn_id} status=200 ip=192.168.1.{random.randint(100,200)}")

        lines.append(f"[{ts_str}] session={token} action=MODIFY_TRANSACTION resource={txn_id} status=200 ip=192.168.1.{random.randint(100,200)}")

        suppress_ts = ts + timedelta(seconds=random.randint(10, 45))
        lines.append(f"[{suppress_ts.strftime('%Y-%m-%dT%H:%M:%S')}] session={token} action=DELETE_AUDIT_ENTRY resource={txn_id} status=200 ip=192.168.1.{random.randint(100,200)}")

        logout_ts = ts + timedelta(minutes=random.randint(2, 8))
        lines.append(f"[{logout_ts.strftime('%Y-%m-%dT%H:%M:%S')}] session={token} action=LOGOUT resource=AUTH_SYSTEM status=200 ip=192.168.1.{random.randint(100,200)}")

    lines.sort(key=lambda l: l.split(']')[0])

    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Created access log with {len(lines)} entries")


# ============================================================
# GENERATE SYSTEM CONFIGURATION
# ============================================================

def create_system_config(path):
    config = {
        "system": {
            "name": "Meridian Transaction Engine",
            "version": "4.2.1",
            "environment": "production",
            "last_restart": "2024-03-01T06:00:00Z"
        },
        "authentication": {
            "provider": "internal",
            "session_timeout_minutes": 480,
            "token_format": "encoded_v2",
            "token_encoding": {
                "method": "xor_rotate_b64",
                "description": "Employee ID bytes XOR with rotating key, then base64. Suffix is CRC16/MODBUS checksum of original ID in hex.",
                "separator": ".",
                "key_length": 6,
                "key_hex": "5a3c7e19426b"
            },
            "max_concurrent_sessions": 3,
            "ip_whitelist": ["10.0.0.0/8"],
            "off_hours_access": {
                "enabled": True,
                "requires_approval": True,
                "notification_email": "security@meridian-fs.com",
                "approved_roles": ["admin", "manager"]
            }
        },
        "database": {
            "engine": "sqlite3",
            "path": "/app/data/ledger.db",
            "wal_mode": True,
            "checkpoint_interval_hours": 6,
            "backup_enabled": True
        },
        "settlements": {
            "batch_directory": "/app/data/settlements/",
            "format": "csv",
            "schedule": "weekly",
            "reconciliation_tolerance": 0.01
        },
        "checkpoints": {
            "directory": "/app/data/checkpoints/",
            "format": "binary_delta_v3",
            "description": "Delta-encoded state snapshots. Each file contains transaction state changes.",
            "encoding_spec": {
                "header": "4 bytes magic (0x44454C54 = 'DELT'), 4 bytes version (uint32 BE), 4 bytes num_records (uint32 BE), 8 bytes timestamp (float64 BE epoch)",
                "record": "32 bytes transaction_id (utf-8 null-padded), 8 bytes previous_amount (float64 BE), 8 bytes current_amount (float64 BE), 4 bytes flags (uint32 BE)"
            },
            "flag_definitions": {
                "0x00000001": "CREATED",
                "0x00000002": "MODIFIED",
                "0x00000004": "SETTLED",
                "0x00000008": "REVERSED",
                "0x00000010": "FLAGGED"
            }
        },
        "audit": {
            "log_path": "/app/data/audit/access.log",
            "retention_days": 90,
            "log_format": "[timestamp] session=token action=type resource=id status=code ip=addr"
        }
    }

    with open(path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Created system configuration at {path}")


# ============================================================
# GENERATE BINARY CHECKPOINT FILES
# ============================================================

def create_checkpoint_files(directory, transactions):
    os.makedirs(directory, exist_ok=True)

    # Build checkpoint data from the canonical transactions
    # Checkpoints are taken at end-of-business (18:00) and contain
    # all settled transactions from that day and the day before.
    # They record the ORIGINAL amounts (pre-tampering).

    settled_txns = {t["transaction_id"]: t for t in transactions if t["status"] == "settled"}

    # Group by date range for each checkpoint
    # Checkpoint date ranges cover 2 consecutive business days each.
    # Each range must cover the tampered transaction dates:
    #   TXN-20240312 -> Mar 11-12 checkpoint
    #   TXN-20240318 -> Mar 18-19 checkpoint
    #   TXN-20240319 -> Mar 19-20 checkpoint
    #   TXN-20240322 -> Mar 21-22 checkpoint
    #   TXN-20240325 -> Mar 25-26 checkpoint
    #   TXN-20240327 -> Mar 27-28 checkpoint
    #   TXN-20240329 -> Mar 29 checkpoint
    checkpoint_dates = [
        ("checkpoint_20240312_180000.bin", datetime(2024, 3, 12, 18, 0, 0),
         datetime(2024, 3, 11), datetime(2024, 3, 12)),
        ("checkpoint_20240319_180000.bin", datetime(2024, 3, 19, 18, 0, 0),
         datetime(2024, 3, 18), datetime(2024, 3, 19)),
        ("checkpoint_20240320_180000.bin", datetime(2024, 3, 20, 18, 0, 0),
         datetime(2024, 3, 19), datetime(2024, 3, 20)),
        ("checkpoint_20240322_180000.bin", datetime(2024, 3, 22, 18, 0, 0),
         datetime(2024, 3, 21), datetime(2024, 3, 22)),
        ("checkpoint_20240326_180000.bin", datetime(2024, 3, 26, 18, 0, 0),
         datetime(2024, 3, 25), datetime(2024, 3, 26)),
        ("checkpoint_20240328_180000.bin", datetime(2024, 3, 28, 18, 0, 0),
         datetime(2024, 3, 27), datetime(2024, 3, 28)),
        ("checkpoint_20240330_060000.bin", datetime(2024, 3, 30, 6, 0, 0),
         datetime(2024, 3, 29), datetime(2024, 3, 29)),
    ]

    MAGIC = b'DELT'
    VERSION = 3

    for filename, cp_ts, range_start, range_end in checkpoint_dates:
        # Collect settled transactions in this date range
        records = []
        for txn_id, txn in settled_txns.items():
            txn_date = txn["date"]
            if range_start <= txn_date <= range_end:
                records.append((
                    txn_id,
                    txn["original_amount"],  # previous = original
                    txn["original_amount"],  # current = original (checkpoint was before tampering)
                    0x00000004  # SETTLED flag
                ))

        # Sort records by txn_id for consistency
        records.sort(key=lambda r: r[0])

        # Limit to ~5 records per checkpoint for readability (keep tampered ones)
        tampered_in_cp = [r for r in records if r[0] in TAMPERED_TXN_IDS]
        normal_in_cp = [r for r in records if r[0] not in TAMPERED_TXN_IDS]
        # Keep all tampered + up to 3 normal
        records = tampered_in_cp + normal_in_cp[:3]
        records.sort(key=lambda r: r[0])

        if not records:
            continue

        filepath = os.path.join(directory, filename)
        with open(filepath, 'wb') as f:
            f.write(MAGIC)
            f.write(struct.pack('>I', VERSION))
            f.write(struct.pack('>I', len(records)))
            f.write(struct.pack('>d', cp_ts.timestamp()))

            for txn_id, prev_amt, curr_amt, flags in records:
                txn_bytes = txn_id.encode('utf-8')
                txn_bytes = txn_bytes + b'\x00' * (32 - len(txn_bytes))
                f.write(txn_bytes)
                f.write(struct.pack('>d', prev_amt))
                f.write(struct.pack('>d', curr_amt))
                f.write(struct.pack('>I', flags))

        print(f"Created checkpoint: {filepath} ({len(records)} records)")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    os.makedirs("/app/data/audit", exist_ok=True)
    os.makedirs("/app/data/config", exist_ok=True)
    os.makedirs("/app/data/settlements", exist_ok=True)
    os.makedirs("/app/data/checkpoints", exist_ok=True)
    os.makedirs("/app/output", exist_ok=True)

    print("=== Generating Phantom Transactions Investigation Data ===\n")

    transactions = generate_all_transactions()
    create_ledger_db("/app/data/ledger.db", transactions)
    create_settlement_files("/app/data/settlements", transactions)
    create_access_log("/app/data/audit/access.log")
    create_system_config("/app/data/config/system_state.json")
    create_checkpoint_files("/app/data/checkpoints", transactions)

    print("\n=== Data generation complete ===")

    # Sanity check: verify exactly 7 discrepancies exist
    tampered = [t for t in transactions if t["is_tampered"]]
    print(f"\nVerification: {len(tampered)} tampered transactions")
    for t in tampered:
        print(f"  {t['transaction_id']}: original={t['original_amount']}, tampered={t['ledger_amount']}, diff={t['ledger_amount']-t['original_amount']}")
    total_disc = sum(t['ledger_amount'] - t['original_amount'] for t in tampered)
    print(f"  Total discrepancy: ${total_disc:,.2f}")
