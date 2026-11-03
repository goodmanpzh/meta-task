DISASTER. Our WAL (write-ahead log) system just had a catastrophic failure during a power event and the transaction logs are SHREDDED across dozens of fragment files. We need these logs recovered NOW because the compliance audit is TOMORROW and if we can't produce complete transaction records we're looking at massive fines.

Here's what happened: the WAL writer was mid-flush when power died. The log entries got scattered across fragment files in subdirectories under `/app/warehouse/`. Some entries are corrupted, some are duplicated across multiple fragments from partial writes, there's garbage data mixed in, and the fragments are NOT in any order.

The format spec is at `/app/warehouse/FORMAT_SPEC.txt` — READ IT CAREFULLY. Each valid line has pipe-delimited fields: stream ID, sequence number, CRC32 checksum, and payload. The CRC is critical — you MUST validate every single line's checksum because there are corrupt entries that look valid but have bad CRCs. The payloads contain special characters (pipes, backticks, quotes, dollars, etc.) so be VERY careful with your parsing.

There are 5 known streams: `txn_alpha`, `txn_beta`, `sys_gamma`, `audit_delta`, `err_epsilon`. Fragment files are scattered in subdirectories under `/app/warehouse/` with extensions like .frag, .log, .dat, .wal, or no extension. SKIP files ending in .old, .bak, .txt, .json, or .metadata — those are backups and indexes, not real fragments.

## What you need to produce:

Write a shell script at `/app/recover.sh` that:

1. Finds ALL valid fragment files recursively under `/app/warehouse/`
2. Parses every line, validates the format AND the CRC32 checksum
3. Discards corrupted/invalid lines, tracks how many
4. Deduplicates entries (same stream+sequence = same entry, keep one)
5. For each stream, outputs recovered payloads sorted by sequence number to `/app/recovered/<STREAM_ID>.log` (one payload per line, NO metadata — just the raw payload text)
6. Generates a recovery report at `/app/recovered/REPORT.json`

The REPORT.json must have this structure:
```json
{
  "streams": {
    "<STREAM_ID>": {
      "recovered_count": <int>,
      "missing_sequences": [<list of missing seq nums as ints>],
      "first_seq": <int>,
      "last_seq": <int>
    }
  },
  "total_recovered": <int>,
  "total_corrupted_lines": <int>,
  "total_duplicate_lines": <int>
}
```

For `missing_sequences`: these are gaps in the sequence — if a stream should have seqs 1-100 but seq 47 is missing (corrupted in all fragments), then 47 is in the missing list. The range is from `first_seq` to `last_seq` inclusive.

The CRC32 is computed over `STREAM_ID|SEQ_NUM|PAYLOAD` (UTF-8, no trailing newline) using the standard CRC32 algorithm (same as `python3 -c "import zlib; print(f'{zlib.crc32(data.encode()) & 0xFFFFFFFF:08x}')"`)

IMPORTANT: The script must be executable and run with `bash /app/recover.sh`. You can use python as a helper if needed (it's installed), but the entry point MUST be the shell script. The script should handle the special characters in payloads correctly — there are pipes, backticks, dollar signs, quotes, and backslashes in the data!!

This needs to be FAST too — don't do something insanely slow. The whole recovery should complete in under 60 seconds.

PLEASE get this right. Every recovered entry matters for the audit. We need COMPLETE recovery of every valid entry and ZERO corrupted entries in the output.
