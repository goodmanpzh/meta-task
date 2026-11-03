#!/usr/bin/env python3
"""
Tests for TCP stream reassembly engine output.

Verifies that the reassembled streams and parsed protocol messages
are correct by checking structural properties, computing expected
values from the raw capture, and validating protocol compliance.
"""

import json
import os
import struct
import pytest


STREAMS_PATH = "/app/output/streams.json"
SUMMARY_PATH = "/app/output/summary.json"
CAPTURE_PATH = "/app/data/capture.bin"


@pytest.fixture(scope="module")
def streams_data():
    """Load the streams.json output."""
    assert os.path.exists(STREAMS_PATH), f"Missing output file: {STREAMS_PATH}"
    with open(STREAMS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def summary_data():
    """Load the summary.json output."""
    assert os.path.exists(SUMMARY_PATH), f"Missing output file: {SUMMARY_PATH}"
    with open(SUMMARY_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def capture_records():
    """Parse the raw capture file to compute expected values."""
    with open(CAPTURE_PATH, 'rb') as f:
        magic = f.read(4)
        assert magic == b'TCAP'
        version, record_count = struct.unpack('>HI', f.read(6))

        records = []
        for _ in range(record_count):
            rec_len = struct.unpack('>I', f.read(4))[0]
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


def _reassemble_stream_from_capture(capture_records, target_stream_id):
    """Reference reassembly for a single stream (used by tests to compute expected values)."""
    segments = []
    for rec in capture_records:
        if rec['stream_id'] != target_stream_id:
            continue
        flags = rec['flags']
        is_syn = flags & 0x01
        is_fin = flags & 0x02
        is_rst = flags & 0x04
        is_retransmit = flags & 0x08
        if is_syn or is_fin or is_rst or is_retransmit:
            continue
        if len(rec['payload']) > 0:
            segments.append((rec['seq_num'], rec['payload'], rec['timestamp_ms']))

    segments.sort(key=lambda s: (s[0], s[2]))
    result = bytearray()
    next_byte = 0
    for seq, payload, ts in segments:
        seg_end = seq + len(payload)
        if seg_end <= next_byte:
            continue
        if seq < next_byte:
            trim = next_byte - seq
            payload = payload[trim:]
            seq = next_byte
        if seq > next_byte:
            result.extend(b'\x00' * (seq - next_byte))
        result.extend(payload)
        next_byte = seq + len(payload)
    return bytes(result)


def _parse_tlv_messages(data):
    """Reference TLV parser (used by tests to compute expected values)."""
    messages = []
    offset = 0
    while offset < len(data):
        if offset + 3 > len(data):
            break
        msg_type = data[offset]
        payload_len = struct.unpack('>H', data[offset+1:offset+3])[0]
        if offset + 3 + payload_len > len(data):
            break
        payload = data[offset+3:offset+3+payload_len]
        offset += 3 + payload_len

        if msg_type == 0x01:
            messages.append({'type': 'TEXT', 'content': payload.decode('utf-8')})
        elif msg_type == 0x02:
            messages.append({'type': 'BINARY', 'content': payload.hex()})
        elif msg_type == 0x03:
            messages.append({'type': 'COMMAND', 'content': payload.decode('utf-8')})
        elif msg_type == 0x04:
            ts = struct.unpack('>Q', payload[:8])[0]
            messages.append({'type': 'HEARTBEAT', 'content': str(ts)})
        elif msg_type == 0x05:
            error_code = struct.unpack('>H', payload[:2])[0]
            error_desc = payload[2:].decode('utf-8')
            messages.append({'type': 'ERROR', 'content': f"{error_code}:{error_desc}"})
    return messages


# ====== Test 1: Output files exist and have valid JSON structure ======

class TestOutputStructure:
    def test_streams_json_exists(self):
        assert os.path.exists(STREAMS_PATH), "streams.json not found"

    def test_summary_json_exists(self):
        assert os.path.exists(SUMMARY_PATH), "summary.json not found"

    def test_streams_has_all_streams(self, streams_data):
        for sid in ["1", "2", "3", "4", "5", "6", "7"]:
            assert sid in streams_data, f"Missing stream {sid} in streams.json"

    def test_summary_structure(self, summary_data):
        assert 'total_streams' in summary_data
        assert 'total_records' in summary_data
        assert 'streams' in summary_data
        assert summary_data['total_streams'] == 7

    def test_stream_entry_structure(self, streams_data):
        for sid, stream in streams_data.items():
            assert 'messages' in stream, f"Stream {sid} missing 'messages'"
            assert 'termination' in stream, f"Stream {sid} missing 'termination'"
            assert isinstance(stream['messages'], list)
            for msg in stream['messages']:
                assert 'type' in msg, f"Message in stream {sid} missing 'type'"
                assert 'content' in msg, f"Message in stream {sid} missing 'content'"


# ====== Test 2: Correct termination types ======

class TestTermination:
    def test_fin_terminated_streams(self, streams_data):
        for sid in ["1", "2", "3", "4", "5", "6"]:
            assert streams_data[sid]['termination'] == 'FIN', \
                f"Stream {sid} should be FIN-terminated, got {streams_data[sid]['termination']}"

    def test_rst_terminated_stream(self, streams_data):
        assert streams_data["7"]['termination'] == 'RST', \
            f"Stream 7 should be RST-terminated, got {streams_data['7']['termination']}"


# ====== Test 3: Correct message counts per stream ======

class TestMessageCounts:
    def test_message_counts(self, streams_data, capture_records):
        """Verify message counts match what's computed from raw capture."""
        for sid_int in range(1, 8):
            sid = str(sid_int)
            raw = _reassemble_stream_from_capture(capture_records, sid_int)
            expected_msgs = _parse_tlv_messages(raw)
            actual_msgs = streams_data[sid]['messages']
            assert len(actual_msgs) == len(expected_msgs), \
                f"Stream {sid}: expected {len(expected_msgs)} messages, got {len(actual_msgs)}"


# ====== Test 4: Correct reassembled byte counts ======

class TestReassemblyByteCount:
    def test_byte_counts(self, summary_data, capture_records):
        """Verify reassembled byte counts are correct (no duplicates from retransmissions/overlaps)."""
        for sid_int in range(1, 8):
            sid = str(sid_int)
            raw = _reassemble_stream_from_capture(capture_records, sid_int)
            expected_bytes = len(raw)
            actual_bytes = summary_data['streams'][sid]['reassembled_bytes']
            assert actual_bytes == expected_bytes, \
                f"Stream {sid}: expected {expected_bytes} bytes, got {actual_bytes}"


# ====== Test 5: Stream 1 - COMMAND and HEARTBEAT content ======

class TestStream1:
    def test_command_messages(self, streams_data, capture_records):
        """Stream 1 should have COMMAND messages with correct content."""
        raw = _reassemble_stream_from_capture(capture_records, 1)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["1"]["messages"]

        commands = [m for m in actual if m['type'] == 'COMMAND']
        expected_commands = [m for m in expected if m['type'] == 'COMMAND']
        assert len(commands) == len(expected_commands)
        for a, e in zip(commands, expected_commands):
            assert a['content'] == e['content']

    def test_heartbeat_messages(self, streams_data, capture_records):
        """Stream 1 HEARTBEAT timestamps should be uint64 values (>2^32)."""
        heartbeats = [m for m in streams_data["1"]["messages"] if m['type'] == 'HEARTBEAT']
        assert len(heartbeats) >= 4
        for hb in heartbeats:
            ts = int(hb['content'])
            # Timestamps should be > 2^32 (they're millisecond epoch values ~1.7 trillion)
            assert ts > 2**32, \
                f"HEARTBEAT timestamp {ts} is too small - likely parsed as uint32 instead of uint64"
            # Should be in reasonable range (year 2024+ epoch ms)
            assert ts > 1700000000000, f"HEARTBEAT timestamp {ts} out of expected range"


# ====== Test 6: Stream 2 - Retransmission handling ======

class TestStream2Retransmissions:
    def test_no_duplicate_data(self, streams_data, capture_records):
        """Stream 2 has retransmissions - they should be filtered out."""
        raw = _reassemble_stream_from_capture(capture_records, 2)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["2"]["messages"]
        assert len(actual) == len(expected), \
            f"Stream 2: expected {len(expected)} messages, got {len(actual)}"

    def test_text_messages_intact(self, streams_data, capture_records):
        """Verify TEXT messages in stream 2 are not corrupted by retransmissions."""
        raw = _reassemble_stream_from_capture(capture_records, 2)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["2"]["messages"]
        for a, e in zip(actual, expected):
            assert a['type'] == e['type'], f"Type mismatch: {a['type']} != {e['type']}"
            assert a['content'] == e['content'], \
                f"Content mismatch in stream 2 {a['type']}: got '{a['content'][:50]}...'"


# ====== Test 7: Stream 3 - ERROR message parsing ======

class TestStream3Errors:
    def test_error_codes_are_http_status_codes(self, streams_data):
        """ERROR messages should have valid HTTP-like status codes (3-digit numbers)."""
        errors = streams_data["3"]["messages"]
        for msg in errors:
            assert msg['type'] == 'ERROR', f"Stream 3 should only have ERROR messages"
            code_str = msg['content'].split(':')[0]
            code = int(code_str)
            assert 100 <= code <= 599, \
                f"Error code {code} is not a valid HTTP status code - likely parsed wrong number of bytes"

    def test_error_descriptions_readable(self, streams_data, capture_records):
        """ERROR descriptions should be readable UTF-8 text, not garbled."""
        raw = _reassemble_stream_from_capture(capture_records, 3)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["3"]["messages"]
        for a, e in zip(actual, expected):
            assert a['content'] == e['content'], \
                f"ERROR content mismatch: got '{a['content'][:60]}'"


# ====== Test 8: Stream 4 - Heavily out-of-order reassembly ======

class TestStream4OutOfOrder:
    def test_message_types_and_count(self, streams_data, capture_records):
        """Stream 4 has mixed message types delivered heavily out-of-order."""
        raw = _reassemble_stream_from_capture(capture_records, 4)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["4"]["messages"]
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected):
            assert a['type'] == e['type']
            assert a['content'] == e['content']


# ====== Test 9: Stream 5 - Fragmented TLV boundaries ======

class TestStream5Fragmented:
    def test_fragmented_reassembly(self, streams_data, capture_records):
        """Stream 5 has very small segments that split TLV headers across boundaries."""
        raw = _reassemble_stream_from_capture(capture_records, 5)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["5"]["messages"]
        assert len(actual) == len(expected), \
            f"Stream 5: expected {len(expected)} messages, got {len(actual)}"
        for a, e in zip(actual, expected):
            assert a['type'] == e['type']
            assert a['content'] == e['content']


# ====== Test 10: Stream 6 - Overlapping segments ======

class TestStream6Overlapping:
    def test_overlap_handling(self, streams_data, capture_records):
        """Stream 6 has overlapping segments - first-seen data must be preferred."""
        raw = _reassemble_stream_from_capture(capture_records, 6)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["6"]["messages"]
        assert len(actual) == len(expected), \
            f"Stream 6: expected {len(expected)} messages, got {len(actual)}"
        for a, e in zip(actual, expected):
            assert a['content'] == e['content'], \
                f"Stream 6 content mismatch (likely corrupted by retransmission overlap)"


# ====== Test 11: Stream 7 - RST termination, incomplete message excluded ======

class TestStream7RST:
    def test_only_complete_messages(self, streams_data, capture_records):
        """Stream 7 is RST-terminated. Only complete TLV messages should be in output."""
        raw = _reassemble_stream_from_capture(capture_records, 7)
        expected = _parse_tlv_messages(raw)
        actual = streams_data["7"]["messages"]
        assert len(actual) == len(expected), \
            f"Stream 7: expected {len(expected)} complete messages, got {len(actual)}"
        # All messages should be complete TEXT messages
        for msg in actual:
            assert msg['type'] == 'TEXT'

    def test_incomplete_message_not_included(self, streams_data):
        """The truncated final message should NOT appear in stream 7 output."""
        messages = streams_data["7"]["messages"]
        for msg in messages:
            # The incomplete message would have partial content about truncation
            assert 'truncated by a connection res' not in msg.get('content', ''), \
                "Incomplete/truncated message should not appear in output"


# ====== Test 12: Summary consistency ======

class TestSummaryConsistency:
    def test_summary_matches_streams(self, streams_data, summary_data):
        """Summary message counts should match actual message lists."""
        for sid in ["1", "2", "3", "4", "5", "6", "7"]:
            expected_count = len(streams_data[sid]['messages'])
            actual_count = summary_data['streams'][sid]['message_count']
            assert actual_count == expected_count, \
                f"Stream {sid}: summary says {actual_count} messages, streams.json has {expected_count}"

    def test_summary_termination_matches(self, streams_data, summary_data):
        """Summary termination should match streams termination."""
        for sid in ["1", "2", "3", "4", "5", "6", "7"]:
            assert summary_data['streams'][sid]['termination'] == streams_data[sid]['termination']
