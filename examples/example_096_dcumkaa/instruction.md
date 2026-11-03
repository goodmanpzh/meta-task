# Phantom Transactions Investigation

I'm an internal auditor at Meridian Financial Services. Something is very wrong with our transaction records and I can't figure out what happened.

Last week, our reconciliation process flagged a significant discrepancy between our primary ledger database and our settlement system — the numbers just don't add up. I started digging and it got worse — I'm now finding mismatched records all over the place. Here's what I know:

Our financial data lives in several systems:
- A SQLite database at `/app/data/ledger.db` — this is our primary transaction ledger
- Settlement batch files in `/app/data/settlements/` — CSVs exported from our clearing house
- Employee access logs in `/app/data/audit/access.log` — shows who accessed what and when
- A configuration dump at `/app/data/config/system_state.json` — snapshot of system settings
- Some kind of binary checkpoint files in `/app/data/checkpoints/` — I think these are periodic state snapshots from the transaction engine

When I run a basic query on the ledger like `SELECT SUM(amount) FROM transactions WHERE status='settled'`, I get a number that doesn't match what the settlement files say. Some transactions appear to have been modified after settlement. I also noticed that certain employee access patterns look suspicious — there are off-hours logins that correlate with the modified records — but I can't figure out who's behind it because the access log uses encoded session tokens instead of plain employee IDs.

The checkpoint files are in some binary format I don't understand. Our system architect said they're "delta-encoded state snapshots" but didn't explain what that means before going on leave. I think they might contain the original transaction values before they were tampered with.

I need you to investigate this thoroughly and produce a forensic report at `/app/output/report.json` with the following structure:

```json
{
  "suspect_employee_id": "<the employee ID behind the tampering>",
  "tampered_transactions": [
    {
      "transaction_id": "<id>",
      "original_amount": <amount before tampering>,
      "tampered_amount": <current amount in ledger>,
      "difference": <tampered - original>,
      "tampering_timestamp": "<ISO 8601 timestamp of when it was modified>"
    }
  ],
  "total_discrepancy": <sum of all differences>,
  "timeline": [
    {
      "timestamp": "<ISO 8601>",
      "event": "<description of what happened>"
    }
  ],
  "evidence_sources": ["<list of files that contributed evidence>"]
}
```

The `tampered_transactions` list should be sorted by `transaction_id`, the `timeline` should be sorted chronologically, and amounts should be numbers (not strings). The `tampering_timestamp` for each transaction should be the timestamp from the access log when that transaction was modified.

I need this figured out. The board wants answers.
