#!/usr/bin/env python3
"""
TCP Stream Reassembly Engine + Custom Protocol Parser

This tool reads a TCAP capture file, reassembles TCP streams from
interleaved packet records, and parses application-layer TLV messages.

Usage:
    python3 /app/reassemble.py /app/data/capture.bin /app/output/

Output files:
    /app/output/streams.json     - Reassembled messages per stream
    /app/output/summary.json     - Summary statistics

NOTE: Run this tool to generate reassembled stream output.
"""

import struct
import sys
import json
import os


def read_capture(filepath):
    """Read a TCAP capture file and return list of packet records."""
    with open(filepath, 'rb') as f:
        # Read file header
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

        self.segments.append((seq_num, payload, timestamp_ms))

    def reassemble(self):
        """Reassemble the stream from collected segments.

        Returns the reassembled byte stream.
        """
        if not self.segments:
            return b''

        # Sort by sequence number
        self.segments.sort(key=lambda s: s[0])

        result = b''
        for seq, payload, ts in self.segments:
            result += payload

        return result


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
            # Incomplete message
            break

        payload = data[offset+3:offset+3+payload_len]
        offset += 3 + payload_len

        # Parse based on message type
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
            ts = struct.unpack('>I', payload[:4])[0]
            messages.append({
                'type': 'HEARTBEAT',
                'content': str(ts)
            })
        elif msg_type == 0x05:  # ERROR
            error_code = struct.unpack('>I', payload[:4])[0]
            error_desc = payload[4:].decode('utf-8', errors='replace')
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
