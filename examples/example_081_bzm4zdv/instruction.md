**Problem:** `python3 /app/reassemble.py /app/data/capture.bin /app/output/` produces incorrect stream reassembly and garbled protocol messages.

**Reproduction:**
```
$ python3 /app/reassemble.py /app/data/capture.bin /app/output/
$ cat /app/output/summary.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['streams'], indent=2))"
```

Output shows wrong byte counts per stream, incorrect message counts, and corrupted message content across multiple streams. The ERROR messages have garbled descriptions, HEARTBEAT timestamps are truncated, and streams with retransmissions or overlapping segments have inflated byte counts.

**Context:**

The file `/app/data/capture.bin` is a binary capture in TCAP format containing 7 interleaved TCP streams. The protocol specification is in `/app/data/manifest.json`. The reassembly engine `/app/reassemble.py` reads this capture, reassembles the streams, parses a TLV-based application protocol from the reassembled data, and writes results to JSON files.

**Expected behavior:**
- Retransmitted packets (flag bit 3) should be discarded during reassembly
- Overlapping byte ranges across segments should keep only the first-seen data for each byte position
- Segments must be reassembled in sequence-number order with no gaps or duplicates
- HEARTBEAT messages contain 8-byte uint64 timestamps (not 4-byte)
- ERROR messages contain a 2-byte uint16 error code followed by UTF-8 description (not 4-byte)
- RST-terminated streams may have an incomplete final TLV message that should not appear in output
- FIN-terminated streams should have all messages fully parsed

| Stream | Expected Behavior |
|--------|-------------------|
| 1 | Ordered delivery, COMMAND + HEARTBEAT messages |
| 2 | Out-of-order + retransmissions, TEXT + BINARY messages |
| 3 | Error reports with correct error codes and descriptions |
| 4 | Heavily out-of-order mixed message types |
| 5 | Very small segments fragmenting TLV boundaries |
| 6 | Overlapping segments + corrupted retransmissions |
| 7 | RST-terminated, incomplete final message must be excluded |

**Expected output:**
- `/app/output/streams.json` — JSON object keyed by stream ID (as string), each containing `messages` (list of `{type, content}`) and `termination` (`"FIN"` or `"RST"`)
- `/app/output/summary.json` — JSON object with `total_streams`, `total_records`, and per-stream stats including `reassembled_bytes`, `message_count`, and `termination`

**Constraints:**
- Fix `/app/reassemble.py` so that running `python3 /app/reassemble.py /app/data/capture.bin /app/output/` produces correct output
- Do not modify the capture file `/app/data/capture.bin` or the manifest `/app/data/manifest.json`
- The output JSON format must match the structure described above exactly
