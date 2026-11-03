#!/bin/bash
set -e

# Fix the TCP stream reassembly engine and run it to produce correct output.
# There are 5 bugs to fix in /app/reassemble.py:
#
# 1. Retransmitted packets (flag bit 3) are not filtered - they add duplicate data
# 2. Overlapping segments are not handled - simple concatenation duplicates bytes
# 3. HEARTBEAT parsing reads 4 bytes (uint32) instead of 8 bytes (uint64)
# 4. ERROR parsing reads 4 bytes for error code instead of 2 bytes (uint16)
# 5. Stream 6 has corrupted retransmissions that must not overwrite first-seen data

cat > /app/reassemble.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
TCP Stream Reassembly Engine + Custom Protocol Parser (FIXED)
"""

import struct
import sys
import json
import os


def read_capture(filepath):
    """Read a TCAP capture file and return list of packet records."""
    with open(filepath, 'rb') as f:
        magic = f.read(4)
        if magic != b'TCAP':
            raise ValueError(f"Invalid magic bytes: {magic}")

        version, record_count = struct.unpack('>HI', f.read(6))
        if version != 1:
            raise ValueError(f"Unsupported version: {version}")

        records = []
        for _ in range(record_count):
            rec_len_bytes = f.read(4)
            if len(rec_len_bytes) < 4:
                break
            rec_len = struct.unpack('>I', rec_len_bytes)[0]
            rec_body = f.read(rec_len)

            stream_id = struct.unpack('>I', rec_body[0:4])[0]
            seq_num = struct.unpack('>I', rec_body[4:8])[0]
            flags = rec_body[8]
            timestamp_ms = struct.unpack('>I', rec_body[9:13])[0]
            payload = rec_body[13:]

            records.append({
                'stream_id': stream_id,
                'seq_num': seq_num,
                'flags': flags,
                'timestamp_ms': timestamp_ms,
                'payload': payload,
            })

        return records


class StreamReassembler:
    """Reassemble a single TCP stream from out-of-order packets."""

    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.segments = []  # (seq_num, payload, timestamp)
        self.syn_seen = False
        self.fin_seen = False
        self.rst_seen = False

    def add_packet(self, seq_num, flags, timestamp_ms, payload):
        """Add a packet to this stream."""
        is_syn = flags & 0x01
        is_fin = flags & 0x02
        is_rst = flags & 0x04
        is_retransmit = flags & 0x08

        if is_syn:
            self.syn_seen = True
            return

        if is_fin:
            self.fin_seen = True
            return

        if is_rst:
            self.rst_seen = True
            return

        # FIX 1: Skip retransmitted packets
        if is_retransmit:
            return

        if len(payload) > 0:
            self.segments.append((seq_num, payload, timestamp_ms))

    def reassemble(self):
        """Reassemble the stream from collected segments.

        Returns the reassembled byte stream.
        Handles out-of-order delivery and overlapping segments.
        For overlapping byte ranges, keeps the FIRST data seen (by timestamp).
        """
        if not self.segments:
            return b''

        # Sort by sequence number, then by timestamp for tie-breaking
        self.segments.sort(key=lambda s: (s[0], s[2]))

        # FIX 2: Proper reassembly with overlap handling
        # Track the next expected byte position
        result = bytearray()
        next_byte = 0

        for seq, payload, ts in self.segments:
            seg_end = seq + len(payload)

            if seg_end <= next_byte:
                # Entire segment is before our current position (duplicate/old data)
                continue

            if seq < next_byte:
                # Partial overlap - trim the beginning of this segment
                trim = next_byte - seq
                payload = payload[trim:]
                seq = next_byte

            # There might be a gap - but in a proper capture there shouldn't be
            # If there is a gap, fill with zeros (shouldn't happen with our data)
            if seq > next_byte:
                result.extend(b'\x00' * (seq - next_byte))

            result.extend(payload)
            next_byte = seq + len(payload)

        return bytes(result)


def parse_tlv_messages(data, stream_id):
    """Parse TLV messages from a reassembled byte stream.

    Returns list of parsed messages.
    """
    messages = []
    offset = 0

    while offset < len(data):
        # Need at least 3 bytes for TLV header
        if offset + 3 > len(data):
            break

        msg_type = data[offset]
        payload_len = struct.unpack('>H', data[offset+1:offset+3])[0]

        if offset + 3 + payload_len > len(data):
            # Incomplete message - skip (valid for RST-terminated streams)
            break

        payload = data[offset+3:offset+3+payload_len]
        offset += 3 + payload_len

        if msg_type == 0x01:  # TEXT
            messages.append({
                'type': 'TEXT',
                'content': payload.decode('utf-8')
            })
        elif msg_type == 0x02:  # BINARY
            messages.append({
                'type': 'BINARY',
                'content': payload.hex()
            })
        elif msg_type == 0x03:  # COMMAND
            messages.append({
                'type': 'COMMAND',
                'content': payload.decode('utf-8')
            })
        elif msg_type == 0x04:  # HEARTBEAT
            # FIX 3: Read 8 bytes as uint64, not 4 bytes as uint32
            ts = struct.unpack('>Q', payload[:8])[0]
            messages.append({
                'type': 'HEARTBEAT',
                'content': str(ts)
            })
        elif msg_type == 0x05:  # ERROR
            # FIX 4: Read 2 bytes as uint16, not 4 bytes as uint32
            error_code = struct.unpack('>H', payload[:2])[0]
            error_desc = payload[2:].decode('utf-8')
            messages.append({
                'type': 'ERROR',
                'content': f"{error_code}:{error_desc}"
            })
        else:
            messages.append({
                'type': f'UNKNOWN_0x{msg_type:02x}',
                'content': payload.hex()
            })

    return messages


def process_capture(capture_path, output_dir):
    """Main processing pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    records = read_capture(capture_path)

    # Group records by stream
    streams = {}
    for rec in records:
        sid = rec['stream_id']
        if sid not in streams:
            streams[sid] = StreamReassembler(sid)
        streams[sid].add_packet(
            rec['seq_num'], rec['flags'],
            rec['timestamp_ms'], rec['payload']
        )

    # Reassemble and parse each stream
    results = {}
    summary = {
        'total_streams': len(streams),
        'total_records': len(records),
        'streams': {}
    }

    for sid in sorted(streams.keys()):
        reassembler = streams[sid]
        raw_data = reassembler.reassemble()
        messages = parse_tlv_messages(raw_data, sid)

        termination = 'UNKNOWN'
        if reassembler.fin_seen:
            termination = 'FIN'
        elif reassembler.rst_seen:
            termination = 'RST'

        results[str(sid)] = {
            'messages': messages,
            'termination': termination,
        }

        summary['streams'][str(sid)] = {
            'reassembled_bytes': len(raw_data),
            'message_count': len(messages),
            'termination': termination,
        }

    # Write output
    with open(os.path.join(output_dir, 'streams.json'), 'w') as f:
        json.dump(results, f, indent=2)

    with open(os.path.join(output_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Processed {len(records)} records across {len(streams)} streams")
    print(f"Output written to {output_dir}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <capture.bin> <output_dir>")
        sys.exit(1)

    process_capture(sys.argv[1], sys.argv[2])
PYTHON_SCRIPT

# Run the fixed reassembler
python3 /app/reassemble.py /app/data/capture.bin /app/output/

echo "Solution complete. Output written to /app/output/"
