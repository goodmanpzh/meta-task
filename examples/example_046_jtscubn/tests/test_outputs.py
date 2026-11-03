"""
MiniRPC Server Test Suite

Tests the server implementation against the protocol specification.
The server must be running on localhost:9777 before tests execute.
"""

import asyncio
import json
import os
import socket
import struct
import subprocess
import sys
import time

import pytest
import pytest_asyncio

# Add tests directory to path so we can import the reference client
sys.path.insert(0, os.path.dirname(__file__))
from reference_client import (
    MiniRPCClient, RPCError,
    build_frame, parse_frame, crc16_ccitt,
    MAGIC, VERSION, HEADER_SIZE, CRC_SIZE,
    MSG_PING, MSG_PONG, MSG_REQUEST, MSG_RESPONSE, MSG_ERROR,
    MSG_SUBSCRIBE, MSG_EVENT, MSG_UNSUBSCRIBE,
)

# Configure pytest-asyncio to auto mode
pytestmark = pytest.mark.asyncio

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9777


def wait_for_server(host=SERVER_HOST, port=SERVER_PORT, timeout=10):
    """Wait for the server to be accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.2)
    return False


@pytest.fixture(scope="session", autouse=True)
def ensure_server_running():
    """Ensure the MiniRPC server is running before tests."""
    if not wait_for_server():
        pytest.skip("MiniRPC server not running on port 9777")


@pytest_asyncio.fixture
async def client():
    """Create and connect a MiniRPC client."""
    c = MiniRPCClient(SERVER_HOST, SERVER_PORT)
    await c.connect()
    yield c
    await c.close()


@pytest_asyncio.fixture
async def client_pair():
    """Create two connected clients for pub/sub testing."""
    c1 = MiniRPCClient(SERVER_HOST, SERVER_PORT)
    c2 = MiniRPCClient(SERVER_HOST, SERVER_PORT)
    await c1.connect()
    await c2.connect()
    yield c1, c2
    await c1.close()
    await c2.close()


# ============================================================
# Category 1: Basic PING/PONG
# ============================================================

class TestPingPong:
    @pytest.mark.asyncio
    async def test_basic_ping(self, client):
        """Server responds to PING with PONG."""
        result = await client.ping(b"hello")
        assert result == b"hello", "PONG must echo the PING payload"

    @pytest.mark.asyncio
    async def test_empty_ping(self, client):
        """Server handles PING with empty payload."""
        result = await client.ping(b"")
        assert result == b"", "Empty PING should get empty PONG"

    @pytest.mark.asyncio
    async def test_large_ping(self, client):
        """Server handles PING with a large payload."""
        data = b"X" * 4096
        result = await client.ping(data)
        assert result == data, "Large PING payload must be echoed exactly"


# ============================================================
# Category 2: CRC Verification
# ============================================================

class TestCRC:
    @pytest.mark.asyncio
    async def test_server_sends_valid_crc(self, client):
        """Verify the server's outgoing frames have correct CRC."""
        # The reference client already validates CRC on receive;
        # if this test passes, the server CRC is correct.
        result = await client.ping(b"crc-check")
        assert result == b"crc-check"

    @pytest.mark.asyncio
    async def test_crc_with_varying_payloads(self, client):
        """Verify CRC integrity across different payload contents."""
        r1 = await client.ping(b"AAAA")
        r2 = await client.ping(b"BBBB")
        assert r1 == b"AAAA"
        assert r2 == b"BBBB"


# ============================================================
# Category 3: Request ID handling
# ============================================================

class TestRequestID:
    @pytest.mark.asyncio
    async def test_request_id_preserved(self, client):
        """Response must carry the same request_id as the request."""
        req_id = 0x0102
        msg_type, resp = await client.request_with_id(
            "echo", {"message": "id-test"}, request_id=req_id
        )
        assert msg_type == MSG_RESPONSE
        assert resp.get("result", {}).get("message") == "id-test"

    @pytest.mark.asyncio
    async def test_request_id_high_value(self, client):
        """Test request ID near the maximum value."""
        req_id = 0xFFFE
        msg_type, resp = await client.request_with_id(
            "echo", {"message": "high-id"}, request_id=req_id
        )
        assert msg_type == MSG_RESPONSE
        assert resp.get("result", {}).get("message") == "high-id"


# ============================================================
# Category 4: RPC Methods
# ============================================================

class TestRPCMethods:
    @pytest.mark.asyncio
    async def test_echo(self, client):
        """Test the echo RPC method."""
        result = await client.request("echo", {"message": "hello world"})
        assert result == {"message": "hello world"}

    @pytest.mark.asyncio
    async def test_add(self, client):
        """Test the add RPC method."""
        result = await client.request("add", {"a": 17, "b": 25})
        assert result == {"sum": 42}

    @pytest.mark.asyncio
    async def test_kv_set_and_get(self, client):
        """Test kv.set and kv.get methods."""
        set_result = await client.request("kv.set",
                                           {"key": "test_key", "value": 12345})
        assert set_result["stored"] is True

        get_result = await client.request("kv.get", {"key": "test_key"})
        assert get_result["value"] == 12345

    @pytest.mark.asyncio
    async def test_kv_get_missing(self, client):
        """Test kv.get for a non-existent key returns an error."""
        with pytest.raises(RPCError) as exc_info:
            await client.request("kv.get", {"key": "nonexistent_key_xyz"})
        assert exc_info.value.code == 404
        assert "not found" in exc_info.value.message.lower()


# ============================================================
# Category 5: Error Handling
# ============================================================

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_unknown_method_error(self, client):
        """Server returns error for unknown RPC methods."""
        with pytest.raises(RPCError) as exc_info:
            await client.request("nonexistent.method", {})
        assert exc_info.value.code == 405

    @pytest.mark.asyncio
    async def test_error_message_type(self, client):
        """Error responses must use the correct message type code."""
        req_id = 0x0055
        msg_type, resp = await client.request_with_id(
            "nonexistent.method", {}, request_id=req_id
        )
        assert msg_type == MSG_ERROR, (
            f"Error responses must use message type 0x{MSG_ERROR:02X} (ERROR), "
            f"but got 0x{msg_type:02X}"
        )

    @pytest.mark.asyncio
    async def test_invalid_json_error(self, client):
        """Server handles invalid JSON payload gracefully."""
        # Send a raw REQUEST with invalid JSON
        req_id = client._next_req_id()
        fut = asyncio.get_event_loop().create_future()
        client._pending[req_id] = fut

        bad_payload = b"not valid json {"
        frame = build_frame(MSG_REQUEST, req_id, bad_payload)
        client._writer.write(frame)
        await client._writer.drain()

        msg_type, resp_payload = await asyncio.wait_for(fut, timeout=5.0)
        client._pending.pop(req_id, None)

        assert msg_type == MSG_ERROR
        resp = json.loads(resp_payload.decode("utf-8"))
        assert resp["code"] == 400


# ============================================================
# Category 6: Pub/Sub
# ============================================================

class TestPubSub:
    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self, client_pair):
        """Subscriber receives events published to their channel."""
        subscriber, publisher = client_pair

        await subscriber.subscribe("test.channel")
        await asyncio.sleep(0.1)

        result = await publisher.request("publish", {
            "channel": "test.channel",
            "data": {"value": 42}
        })
        assert result["subscribers"] >= 1

        event = await subscriber.wait_event(timeout=5.0)
        assert event["channel"] == "test.channel"
        assert event["data"]["value"] == 42

    @pytest.mark.asyncio
    async def test_unsubscribe(self, client_pair):
        """Client stops receiving events after unsubscribing."""
        subscriber, publisher = client_pair

        await subscriber.subscribe("unsub.channel")
        await asyncio.sleep(0.1)
        await subscriber.unsubscribe("unsub.channel")
        await asyncio.sleep(0.1)

        await publisher.request("publish", {
            "channel": "unsub.channel",
            "data": "should-not-arrive"
        })

        with pytest.raises(asyncio.TimeoutError):
            await subscriber.wait_event(timeout=1.0)

    @pytest.mark.asyncio
    async def test_channel_isolation(self, client_pair):
        """Events on one channel should not leak to another channel's subscribers."""
        subscriber, publisher = client_pair

        await subscriber.subscribe("channel.A")
        await asyncio.sleep(0.1)

        await publisher.request("publish", {
            "channel": "channel.B",
            "data": "wrong-channel"
        })

        # The subscriber should NOT receive this event
        with pytest.raises(asyncio.TimeoutError):
            await subscriber.wait_event(timeout=1.5)

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, client_pair):
        """Multiple clients on the same channel each receive events."""
        c1, c2 = client_pair

        await c1.subscribe("multi.ch")
        await c2.subscribe("multi.ch")
        await asyncio.sleep(0.1)

        # Use a third client to publish
        pub = MiniRPCClient(SERVER_HOST, SERVER_PORT)
        await pub.connect()

        try:
            result = await pub.request("publish", {
                "channel": "multi.ch",
                "data": "broadcast"
            })
            assert result["subscribers"] >= 2

            e1 = await c1.wait_event(timeout=5.0)
            e2 = await c2.wait_event(timeout=5.0)
            assert e1["data"] == "broadcast"
            assert e2["data"] == "broadcast"
        finally:
            await pub.close()


# ============================================================
# Category 7: Concurrent Connections
# ============================================================

class TestConcurrency:
    @pytest.mark.asyncio
    async def test_multiple_clients(self):
        """Server handles multiple concurrent client connections."""
        clients = []
        try:
            for _ in range(5):
                c = MiniRPCClient(SERVER_HOST, SERVER_PORT)
                await c.connect()
                clients.append(c)

            # Each client does an independent operation
            tasks = []
            for i, c in enumerate(clients):
                tasks.append(c.request("echo", {"message": f"client-{i}"}))

            results = await asyncio.gather(*tasks)

            for i, result in enumerate(results):
                assert result == {"message": f"client-{i}"}
        finally:
            for c in clients:
                await c.close()

    @pytest.mark.asyncio
    async def test_sequential_requests(self, client):
        """Server handles many sequential requests on one connection."""
        for i in range(20):
            result = await client.request("add", {"a": i, "b": i * 2})
            assert result == {"sum": i * 3}


# ============================================================
# Category 8: Connection Cleanup
# ============================================================

class TestConnectionCleanup:
    @pytest.mark.asyncio
    async def test_client_disconnect_no_crash(self):
        """Server survives abrupt client disconnection."""
        c = MiniRPCClient(SERVER_HOST, SERVER_PORT)
        await c.connect()

        # Do some work
        await c.request("echo", {"message": "before-disconnect"})
        await c.subscribe("cleanup.channel")

        # Abruptly close
        c._writer.close()
        try:
            await c._writer.wait_closed()
        except Exception:
            pass
        if c._recv_task:
            c._recv_task.cancel()
            try:
                await c._recv_task
            except (asyncio.CancelledError, Exception):
                pass

        await asyncio.sleep(0.5)

        # Server should still work for new clients
        c2 = MiniRPCClient(SERVER_HOST, SERVER_PORT)
        await c2.connect()
        try:
            result = await c2.request("echo", {"message": "after-disconnect"})
            assert result == {"message": "after-disconnect"}
        finally:
            await c2.close()


# ============================================================
# Category 9: Payload Edge Cases
# ============================================================

class TestPayloadEdgeCases:
    @pytest.mark.asyncio
    async def test_zero_length_payload_request(self, client):
        """Server handles zero-length payload gracefully (as invalid JSON)."""
        req_id = client._next_req_id()
        fut = asyncio.get_event_loop().create_future()
        client._pending[req_id] = fut

        frame = build_frame(MSG_REQUEST, req_id, b"")
        client._writer.write(frame)
        await client._writer.drain()

        msg_type, resp_payload = await asyncio.wait_for(fut, timeout=5.0)
        client._pending.pop(req_id, None)
        assert msg_type == MSG_ERROR

    @pytest.mark.asyncio
    async def test_unicode_payload(self, client):
        """Server handles UTF-8 encoded payloads with non-ASCII characters."""
        result = await client.request("echo",
                                       {"message": "こんにちは世界 🌍"})
        assert result == {"message": "こんにちは世界 🌍"}


# ============================================================
# Category 10: Protocol Compliance
# ============================================================

class TestProtocolCompliance:
    @pytest.mark.asyncio
    async def test_server_frame_structure(self):
        """Verify server frames have correct magic, version, and structure."""
        # Send a raw PING and read the raw response to verify structure
        reader, writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)
        try:
            ping_payload = b"struct-test"
            frame = build_frame(MSG_PING, 0x0001, ping_payload)
            writer.write(frame)
            await writer.drain()

            # Read header
            header = b""
            while len(header) < HEADER_SIZE:
                chunk = await asyncio.wait_for(
                    reader.read(HEADER_SIZE - len(header)), timeout=5.0)
                if not chunk:
                    raise ConnectionError("Closed")
                header += chunk

            magic = struct.unpack("!I", header[0:4])[0]
            assert magic == MAGIC, f"Wrong magic: 0x{magic:08X}"

            version = header[4]
            assert version == VERSION, f"Wrong version: {version}"

            msg_type = header[5]
            assert msg_type == MSG_PONG, f"Expected PONG, got 0x{msg_type:02X}"

            req_id = struct.unpack("!H", header[6:8])[0]
            assert req_id == 0x0001, f"Wrong request ID: 0x{req_id:04X}"

            payload_length = struct.unpack("!I", header[8:12])[0]
            assert payload_length == len(ping_payload), \
                f"Wrong payload length: {payload_length}"

            # Read payload
            payload = b""
            while len(payload) < payload_length:
                chunk = await asyncio.wait_for(
                    reader.read(payload_length - len(payload)), timeout=5.0)
                if not chunk:
                    raise ConnectionError("Closed")
                payload += chunk

            assert payload == ping_payload, \
                f"Wrong payload: {payload!r} != {ping_payload!r}"

            # Read and verify CRC
            crc_bytes = b""
            while len(crc_bytes) < CRC_SIZE:
                chunk = await asyncio.wait_for(
                    reader.read(CRC_SIZE - len(crc_bytes)), timeout=5.0)
                if not chunk:
                    raise ConnectionError("Closed")
                crc_bytes += chunk

            received_crc = struct.unpack("!H", crc_bytes)[0]
            expected_crc = crc16_ccitt(header + payload)
            assert received_crc == expected_crc, \
                f"CRC mismatch: 0x{received_crc:04X} != 0x{expected_crc:04X}"
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
