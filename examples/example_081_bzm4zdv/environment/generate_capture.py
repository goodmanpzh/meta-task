#!/usr/bin/env python3
"""
Generate a binary capture file containing raw TCP-like packet records
with multiple interleaved streams, out-of-order delivery, retransmissions,
overlapping segments, and a custom application-layer binary protocol.

Binary capture format (per packet record):
  - 4 bytes: record_length (uint32 big-endian, length of everything after this field)
  - 4 bytes: stream_id (uint32 big-endian)
  - 4 bytes: seq_num (uint32 big-endian) - byte-offset in stream
  - 1 byte:  flags (bit 0=SYN, bit 1=FIN, bit 2=RST, bit 3=retransmission)
  - 4 bytes: timestamp_ms (uint32 big-endian)
  - N bytes: payload

Application-layer protocol (carried within reassembled TCP stream):
  Each message is TLV-encoded:
  - 1 byte:  message_type
  - 2 bytes: payload_length (uint16 big-endian)
  - N bytes: payload data

  Message types:
    0x01 = TEXT     (payload is UTF-8 text)
    0x02 = BINARY   (payload is raw binary data, report as hex)
    0x03 = COMMAND  (payload is UTF-8 command string)
    0x04 = HEARTBEAT (payload is 8 bytes: uint64 big-endian timestamp)
    0x05 = ERROR    (payload is: 2-byte error code (uint16 BE) + UTF-8 description)

Stream descriptions:
  Stream 1 (ports 10001): Control channel - mix of COMMAND and HEARTBEAT messages
  Stream 2 (ports 10002): Data transfer - TEXT and BINARY messages, with retransmissions
  Stream 3 (ports 10003): Error reporting - ERROR messages with specific codes
  Stream 4 (ports 10004): Mixed traffic - all message types, delivered heavily out-of-order
  Stream 5 (ports 10005): Fragmented - messages split across many small segments
  Stream 6 (ports 10006): Overlapping - segments with overlapping byte ranges
  Stream 7 (ports 10007): RST-terminated - stream ends with RST (incomplete final message)
"""

import struct
import random
import json
import os

random.seed(42)

# Collect all packet records
records = []
# Track stream data for verification
stream_messages = {}

def make_record(stream_id, seq_num, flags, timestamp_ms, payload):
    """Create a binary packet record."""
    record_body = struct.pack('>IIBI', stream_id, seq_num, flags, timestamp_ms) + payload
    record_length = len(record_body)
    return struct.pack('>I', record_length) + record_body

def make_tlv_message(msg_type, payload_bytes):
    """Create a TLV-encoded application message."""
    return struct.pack('>BH', msg_type, len(payload_bytes)) + payload_bytes

def add_stream_message(stream_id, msg_type, payload_bytes):
    """Track a message for verification."""
    if stream_id not in stream_messages:
        stream_messages[stream_id] = []

    type_names = {0x01: 'TEXT', 0x02: 'BINARY', 0x03: 'COMMAND', 0x04: 'HEARTBEAT', 0x05: 'ERROR'}

    if msg_type == 0x01:
        content = payload_bytes.decode('utf-8')
    elif msg_type == 0x02:
        content = payload_bytes.hex()
    elif msg_type == 0x03:
        content = payload_bytes.decode('utf-8')
    elif msg_type == 0x04:
        ts = struct.unpack('>Q', payload_bytes)[0]
        content = str(ts)
    elif msg_type == 0x05:
        error_code = struct.unpack('>H', payload_bytes[:2])[0]
        error_desc = payload_bytes[2:].decode('utf-8')
        content = f"{error_code}:{error_desc}"

    stream_messages[stream_id].append({
        'type': type_names[msg_type],
        'content': content
    })

# ============ Stream 1: Control channel ============
stream1_data = b''

# COMMAND messages
commands = [
    "INIT session_id=a3f7b2c1",
    "SET timeout=30000",
    "SET max_retries=5",
    "PING sequence=1",
    "CONFIGURE buffer_size=65536 compression=lz4",
    "AUTH token=eyJhbGciOiJIUzI1NiJ9.dGVzdA.Dk4qcmr7",
    "SUBSCRIBE channel=telemetry.cpu,telemetry.mem",
    "PING sequence=2",
]
for cmd in commands:
    payload = cmd.encode('utf-8')
    msg = make_tlv_message(0x03, payload)
    stream1_data += msg
    add_stream_message(1, 0x03, payload)

# HEARTBEAT messages interspersed
heartbeat_times = [1709000100000, 1709000130000, 1709000160000, 1709000190000]
for ht in heartbeat_times:
    payload = struct.pack('>Q', ht)
    msg = make_tlv_message(0x04, payload)
    stream1_data += msg
    add_stream_message(1, 0x04, payload)

# Deliver stream 1 in ordered chunks with SYN at start and FIN at end
ts = 1000
chunk_size = 50
records.append(make_record(1, 0, 0x01, ts, b''))  # SYN
ts += 10
offset = 0
while offset < len(stream1_data):
    end = min(offset + chunk_size, len(stream1_data))
    chunk = stream1_data[offset:end]
    records.append(make_record(1, offset, 0x00, ts, chunk))
    offset = end
    ts += random.randint(5, 20)
records.append(make_record(1, len(stream1_data), 0x02, ts, b''))  # FIN

# ============ Stream 2: Data transfer with retransmissions ============
stream2_data = b''

texts = [
    "The quick brown fox jumps over the lazy dog.",
    "Pack my box with five dozen liquor jugs.",
    "How vexingly quick daft zebras jump!",
    "The five boxing wizards jump quickly.",
]
for t in texts:
    payload = t.encode('utf-8')
    msg = make_tlv_message(0x01, payload)
    stream2_data += msg
    add_stream_message(2, 0x01, payload)

binary_payloads = [
    bytes(range(0, 64)),
    bytes([0xDE, 0xAD, 0xBE, 0xEF] * 16),
    bytes([0xFF - (i % 256) for i in range(48)]),
]
for bp in binary_payloads:
    msg = make_tlv_message(0x02, bp)
    stream2_data += msg
    add_stream_message(2, 0x02, bp)

# Deliver stream 2 with some retransmissions and out-of-order
ts = 1050
records.append(make_record(2, 0, 0x01, ts, b''))  # SYN
ts += 10

segments_2 = []
offset = 0
seg_size = 40
while offset < len(stream2_data):
    end = min(offset + seg_size, len(stream2_data))
    segments_2.append((offset, stream2_data[offset:end]))
    offset = end

# Shuffle some segments to create out-of-order delivery
# Keep first and last in place, shuffle middle
middle = segments_2[1:-1]
random.shuffle(middle)
segments_2 = [segments_2[0]] + middle + [segments_2[-1]]

for i, (seq, chunk) in enumerate(segments_2):
    records.append(make_record(2, seq, 0x00, ts, chunk))
    ts += random.randint(5, 15)

    # Add retransmissions for some segments (flag bit 3 = retransmission)
    if i in [2, 4, 6]:
        # Retransmit with flag 0x08 and slightly later timestamp
        records.append(make_record(2, seq, 0x08, ts + 50, chunk))

records.append(make_record(2, len(stream2_data), 0x02, ts + 10, b''))  # FIN

# ============ Stream 3: Error reporting ============
stream3_data = b''

errors = [
    (404, "Resource not found: /api/v2/users/12345"),
    (500, "Internal server error: database connection pool exhausted"),
    (403, "Permission denied: insufficient privileges for operation DELETE on /admin/config"),
    (408, "Request timeout: upstream service did not respond within 30000ms"),
    (429, "Rate limit exceeded: 1000 requests per minute (current: 1247)"),
    (503, "Service unavailable: deployment in progress, retry after 60s"),
    (502, "Bad gateway: upstream returned invalid HTTP response"),
]
for code, desc in errors:
    payload = struct.pack('>H', code) + desc.encode('utf-8')
    msg = make_tlv_message(0x05, payload)
    stream3_data += msg
    add_stream_message(3, 0x05, payload)

ts = 1100
records.append(make_record(3, 0, 0x01, ts, b''))  # SYN
ts += 10
offset = 0
seg_size = 60
while offset < len(stream3_data):
    end = min(offset + seg_size, len(stream3_data))
    records.append(make_record(3, offset, 0x00, ts, stream3_data[offset:end]))
    offset = end
    ts += random.randint(8, 25)
records.append(make_record(3, len(stream3_data), 0x02, ts, b''))  # FIN

# ============ Stream 4: Mixed traffic, heavily out-of-order ============
stream4_data = b''
stream4_msgs = []

# Generate a complex mix of messages
stream4_msgs.append((0x03, "START pipeline_id=7f3a"))
stream4_msgs.append((0x01, "Processing batch 1 of 5: 2048 records loaded"))
stream4_msgs.append((0x04, None))  # heartbeat
stream4_msgs.append((0x02, None))  # binary
stream4_msgs.append((0x01, "Processing batch 2 of 5: filtering by timestamp > 2024-01-01"))
stream4_msgs.append((0x05, (409, "Conflict: duplicate key in batch 2, row 847")))
stream4_msgs.append((0x01, "Processing batch 3 of 5: aggregation phase"))
stream4_msgs.append((0x04, None))  # heartbeat
stream4_msgs.append((0x02, None))  # binary
stream4_msgs.append((0x01, "Processing batch 4 of 5: writing results to output buffer"))
stream4_msgs.append((0x03, "CHECKPOINT pipeline_id=7f3a stage=4"))
stream4_msgs.append((0x01, "Processing batch 5 of 5: finalization and cleanup"))
stream4_msgs.append((0x04, None))  # heartbeat
stream4_msgs.append((0x03, "COMPLETE pipeline_id=7f3a status=partial records_ok=9847 records_err=153"))

hb_counter = 1709000200000
bin_counter = 0
binary_data_patterns = [
    bytes([i ^ 0xAA for i in range(32)]),
    bytes([(i * 7 + 13) % 256 for i in range(32)]),
]

for msg_type, content in stream4_msgs:
    if msg_type == 0x01:
        payload = content.encode('utf-8')
        msg = make_tlv_message(0x01, payload)
        stream4_data += msg
        add_stream_message(4, 0x01, payload)
    elif msg_type == 0x02:
        payload = binary_data_patterns[bin_counter % len(binary_data_patterns)]
        bin_counter += 1
        msg = make_tlv_message(0x02, payload)
        stream4_data += msg
        add_stream_message(4, 0x02, payload)
    elif msg_type == 0x03:
        payload = content.encode('utf-8')
        msg = make_tlv_message(0x03, payload)
        stream4_data += msg
        add_stream_message(4, 0x03, payload)
    elif msg_type == 0x04:
        payload = struct.pack('>Q', hb_counter)
        hb_counter += 30000
        msg = make_tlv_message(0x04, payload)
        stream4_data += msg
        add_stream_message(4, 0x04, payload)
    elif msg_type == 0x05:
        code, desc = content
        payload = struct.pack('>H', code) + desc.encode('utf-8')
        msg = make_tlv_message(0x05, payload)
        stream4_data += msg
        add_stream_message(4, 0x05, payload)

# Deliver stream 4 HEAVILY out of order with small segments
ts = 1200
records.append(make_record(4, 0, 0x01, ts, b''))  # SYN
ts += 5

segments_4 = []
offset = 0
seg_size = 25  # Small segments
while offset < len(stream4_data):
    end = min(offset + seg_size, len(stream4_data))
    segments_4.append((offset, stream4_data[offset:end]))
    offset = end

# Heavily shuffle - reverse chunks of 3
shuffled_4 = []
for i in range(0, len(segments_4), 3):
    group = segments_4[i:i+3]
    group.reverse()
    shuffled_4.extend(group)

for seq, chunk in shuffled_4:
    records.append(make_record(4, seq, 0x00, ts, chunk))
    ts += random.randint(2, 10)

records.append(make_record(4, len(stream4_data), 0x02, ts, b''))  # FIN

# ============ Stream 5: Fragmented - very small segments ============
stream5_data = b''

texts5 = [
    "This message is intentionally split across many tiny TCP segments to test reassembly of fragmented TLV boundaries.",
    "Second fragmented message: the TLV header itself may be split across segment boundaries.",
    "Third message with UTF-8: cafe\u0301 na\u00efve re\u0301sume\u0301 \u2014 ensure encoding survives reassembly.",
]
for t in texts5:
    payload = t.encode('utf-8')
    msg = make_tlv_message(0x01, payload)
    stream5_data += msg
    add_stream_message(5, 0x01, payload)

# Add a binary message too
bin_payload = bytes(range(200))  # 200 bytes of binary
msg = make_tlv_message(0x02, bin_payload)
stream5_data += msg
add_stream_message(5, 0x02, bin_payload)

# Deliver in VERY small segments (5-12 bytes each)
ts = 1300
records.append(make_record(5, 0, 0x01, ts, b''))  # SYN
ts += 5

offset = 0
while offset < len(stream5_data):
    seg_sz = random.randint(5, 12)
    end = min(offset + seg_sz, len(stream5_data))
    records.append(make_record(5, offset, 0x00, ts, stream5_data[offset:end]))
    offset = end
    ts += random.randint(1, 5)

records.append(make_record(5, len(stream5_data), 0x02, ts, b''))  # FIN

# ============ Stream 6: Overlapping segments ============
stream6_data = b''

texts6 = [
    "Overlapping segment test: this stream has segments where byte ranges overlap.",
    "The reassembler must prefer the FIRST data seen for any given byte position.",
    "If the reassembler uses later data for overlapping regions, the output will be corrupted.",
]
for t in texts6:
    payload = t.encode('utf-8')
    msg = make_tlv_message(0x01, payload)
    stream6_data += msg
    add_stream_message(6, 0x01, payload)

# Deliver with overlapping segments
ts = 1400
records.append(make_record(6, 0, 0x01, ts, b''))  # SYN
ts += 5

# Create segments with deliberate overlaps
offset = 0
overlap_records = []
seg_size = 45
while offset < len(stream6_data):
    end = min(offset + seg_size, len(stream6_data))
    overlap_records.append((offset, stream6_data[offset:end], ts))
    ts += 10
    # Next segment starts 10 bytes before end (overlap)
    offset = max(offset + 1, end - 10)

for seq, chunk, t in overlap_records:
    records.append(make_record(6, seq, 0x00, t, chunk))

# Also add some retransmissions with CORRUPTED data (flag 0x08)
# The reassembler must use FIRST-seen data, not retransmission data
for seq, chunk, t in overlap_records[2:5]:
    corrupted = bytes([b ^ 0xFF for b in chunk])
    records.append(make_record(6, seq, 0x08, t + 100, corrupted))

records.append(make_record(6, len(stream6_data), 0x02, ts, b''))  # FIN

# ============ Stream 7: RST-terminated (incomplete final message) ============
stream7_data = b''

# Some complete messages
complete_msgs = [
    "RST stream: this message is complete.",
    "RST stream: second complete message.",
    "RST stream: third complete message before connection reset.",
]
for t in complete_msgs:
    payload = t.encode('utf-8')
    msg = make_tlv_message(0x01, payload)
    stream7_data += msg
    add_stream_message(7, 0x01, payload)

# Add an INCOMPLETE message (TLV header says 200 bytes but only 50 delivered before RST)
incomplete_header = struct.pack('>BH', 0x01, 200)
incomplete_partial = b'This message will be truncated by a connection res'
stream7_data += incomplete_header + incomplete_partial
# NOTE: this incomplete message should NOT appear in the output

ts = 1500
records.append(make_record(7, 0, 0x01, ts, b''))  # SYN
ts += 5

offset = 0
seg_size = 35
while offset < len(stream7_data):
    end = min(offset + seg_size, len(stream7_data))
    records.append(make_record(7, offset, 0x00, ts, stream7_data[offset:end]))
    offset = end
    ts += random.randint(5, 15)

# RST instead of FIN
records.append(make_record(7, offset, 0x04, ts + 5, b''))  # RST

# ============ Shuffle all records to interleave streams ============
# Sort by timestamp but add some jitter
def sort_key(rec):
    # Extract timestamp from record: skip 4 (rec_len) + 4 (stream_id) + 4 (seq) + 1 (flags) = 13 bytes in
    ts_bytes = rec[13:17]
    ts = struct.unpack('>I', ts_bytes)[0]
    return ts + random.randint(-3, 3)

records.sort(key=sort_key)

# Write capture file
capture_path = '/app/data/capture.bin'
os.makedirs('/app/data', exist_ok=True)
with open(capture_path, 'wb') as f:
    # File header: magic bytes + version + number of records
    f.write(b'TCAP')  # magic
    f.write(struct.pack('>HI', 1, len(records)))  # version=1, record_count
    for rec in records:
        f.write(rec)

# Write manifest (metadata about what's in the capture, but NOT the answers)
manifest = {
    "format": "TCAP v1",
    "description": "TCP stream capture with custom binary protocol",
    "num_records": len(records),
    "num_streams": 7,
    "stream_info": {
        "1": {"description": "Control channel", "terminated_by": "FIN"},
        "2": {"description": "Data transfer with retransmissions", "terminated_by": "FIN"},
        "3": {"description": "Error reporting", "terminated_by": "FIN"},
        "4": {"description": "Mixed traffic, heavily out-of-order", "terminated_by": "FIN"},
        "5": {"description": "Fragmented small segments", "terminated_by": "FIN"},
        "6": {"description": "Overlapping byte ranges", "terminated_by": "FIN"},
        "7": {"description": "RST-terminated (may have incomplete messages)", "terminated_by": "RST"},
    },
    "protocol": {
        "capture_record": {
            "record_length": "uint32 BE - length of record body",
            "stream_id": "uint32 BE",
            "seq_num": "uint32 BE - byte offset in stream",
            "flags": "uint8 - bit 0=SYN, bit 1=FIN, bit 2=RST, bit 3=retransmission",
            "timestamp_ms": "uint32 BE",
            "payload": "remaining bytes"
        },
        "file_header": {
            "magic": "TCAP (4 bytes)",
            "version": "uint16 BE",
            "record_count": "uint32 BE"
        },
        "application_protocol": {
            "message_format": "TLV: 1-byte type + 2-byte length (BE) + payload",
            "types": {
                "0x01": "TEXT - UTF-8 text payload",
                "0x02": "BINARY - raw binary (report as hex string)",
                "0x03": "COMMAND - UTF-8 command string",
                "0x04": "HEARTBEAT - 8-byte uint64 BE timestamp",
                "0x05": "ERROR - 2-byte uint16 BE error code + UTF-8 description"
            }
        }
    }
}

with open('/app/data/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)

# Write verification data (will be deleted from container, used only for test generation)
verify = {
    "streams": {}
}
for sid in sorted(stream_messages.keys()):
    verify["streams"][str(sid)] = {
        "message_count": len(stream_messages[sid]),
        "messages": stream_messages[sid]
    }

with open('/app/data/.verify.json', 'w') as f:
    json.dump(verify, f, indent=2)

# Also write stream byte counts for verification
stream_sizes = {
    "1": len(stream1_data),
    "2": len(stream2_data),
    "3": len(stream3_data),
    "4": len(stream4_data),
    "5": len(stream5_data),
    "6": len(stream6_data),
    "7": len(stream7_data),
}
with open('/app/data/.stream_sizes.json', 'w') as f:
    json.dump(stream_sizes, f, indent=2)

print(f"Generated capture.bin with {len(records)} records")
print(f"Stream byte counts: {stream_sizes}")
for sid in sorted(stream_messages.keys()):
    print(f"  Stream {sid}: {len(stream_messages[sid])} messages")
print("Verification data written to .verify.json")
