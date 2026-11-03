"""
MiniRPC Reference Client

A correct implementation of the MiniRPC client protocol for testing purposes.
"""

import asyncio
import json
import struct
from typing import Optional

MAGIC = 0xDEADBEEF
VERSION = 0x01
HEADER_SIZE = 12
CRC_SIZE = 2

MSG_PING        = 0x01
MSG_PONG        = 0x02
MSG_REQUEST     = 0x10
MSG_RESPONSE    = 0x11
MSG_ERROR       = 0x20
MSG_SUBSCRIBE   = 0x30
MSG_EVENT       = 0x31
MSG_UNSUBSCRIBE = 0x32


def crc16_ccitt(data: bytes) -> int:
    """Compute CRC-16/CCITT with polynomial 0x1021 and initial value 0xFFFF."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc


def build_frame(msg_type: int, request_id: int, payload: bytes) -> bytes:
    """Build a correct MiniRPC frame."""
    header = struct.pack("!IBBHI",
                         MAGIC, VERSION, msg_type, request_id, len(payload))
    frame_without_crc = header + payload
    crc = crc16_ccitt(frame_without_crc)
    return frame_without_crc + struct.pack("!H", crc)


def parse_frame(data: bytes):
    """Parse a complete MiniRPC frame. Returns (msg_type, request_id, payload)."""
    if len(data) < HEADER_SIZE + CRC_SIZE:
        raise ValueError("Frame too short")

    magic = struct.unpack("!I", data[0:4])[0]
    if magic != MAGIC:
        raise ValueError(f"Bad magic: 0x{magic:08X}")

    version = data[4]
    msg_type = data[5]
    request_id = struct.unpack("!H", data[6:8])[0]
    payload_length = struct.unpack("!I", data[8:12])[0]

    expected_len = HEADER_SIZE + payload_length + CRC_SIZE
    if len(data) < expected_len:
        raise ValueError(f"Frame incomplete: got {len(data)}, expected {expected_len}")

    payload = data[HEADER_SIZE:HEADER_SIZE + payload_length]
    received_crc = struct.unpack("!H", data[HEADER_SIZE + payload_length:
                                              HEADER_SIZE + payload_length + 2])[0]
    computed_crc = crc16_ccitt(data[:HEADER_SIZE + payload_length])

    if received_crc != computed_crc:
        raise ValueError(
            f"CRC mismatch: got 0x{received_crc:04X}, expected 0x{computed_crc:04X}")

    return msg_type, request_id, payload


class MiniRPCClient:
    """Async MiniRPC client."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9777):
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._req_counter = 0
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._pending: dict[int, asyncio.Future] = {}
        self._recv_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def connect(self):
        """Connect to the server."""
        self._reader, self._writer = await asyncio.open_connection(
            self.host, self.port
        )
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def close(self):
        """Close the connection."""
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        # Cancel any pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()

    async def _read_exact(self, n: int) -> bytes:
        """Read exactly n bytes."""
        data = b""
        while len(data) < n:
            chunk = await self._reader.read(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    async def _read_frame(self):
        """Read a single frame from the connection."""
        header_data = await self._read_exact(HEADER_SIZE)

        magic = struct.unpack("!I", header_data[0:4])[0]
        if magic != MAGIC:
            raise ValueError(f"Bad magic: 0x{magic:08X}")

        msg_type = header_data[5]
        request_id = struct.unpack("!H", header_data[6:8])[0]
        payload_length = struct.unpack("!I", header_data[8:12])[0]

        payload = await self._read_exact(payload_length) if payload_length > 0 else b""
        crc_data = await self._read_exact(CRC_SIZE)

        received_crc = struct.unpack("!H", crc_data)[0]
        computed_crc = crc16_ccitt(header_data + payload)

        if received_crc != computed_crc:
            raise ValueError(
                f"CRC mismatch: got 0x{received_crc:04X}, "
                f"expected 0x{computed_crc:04X}"
            )

        return msg_type, request_id, payload

    async def _recv_loop(self):
        """Background task to receive and dispatch frames."""
        try:
            while True:
                msg_type, request_id, payload = await self._read_frame()

                if msg_type == MSG_EVENT:
                    await self._event_queue.put(
                        json.loads(payload.decode("utf-8")))
                elif msg_type in (MSG_PONG, MSG_RESPONSE, MSG_ERROR):
                    fut = self._pending.get(request_id)
                    if fut and not fut.done():
                        fut.set_result((msg_type, payload))
                else:
                    pass  # Unknown message, ignore
        except (ConnectionError, asyncio.CancelledError):
            pass
        except Exception as e:
            # Set error on all pending futures
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(e)

    def _next_req_id(self) -> int:
        self._req_counter += 1
        if self._req_counter > 0xFFFF:
            self._req_counter = 1
        return self._req_counter

    async def _send_and_wait(self, msg_type: int, request_id: int,
                              payload: bytes, timeout: float = 5.0):
        """Send a frame and wait for the response."""
        fut = asyncio.get_event_loop().create_future()
        self._pending[request_id] = fut

        frame = build_frame(msg_type, request_id, payload)
        self._writer.write(frame)
        await self._writer.drain()

        try:
            result = await asyncio.wait_for(fut, timeout=timeout)
            return result
        finally:
            self._pending.pop(request_id, None)

    async def ping(self, data: bytes = b"", timeout: float = 5.0):
        """Send PING and wait for PONG. Returns the PONG payload."""
        req_id = self._next_req_id()
        msg_type, payload = await self._send_and_wait(
            MSG_PING, req_id, data, timeout=timeout)
        assert msg_type == MSG_PONG, f"Expected PONG, got 0x{msg_type:02X}"
        return payload

    async def request(self, method: str, params: dict = None,
                      timeout: float = 5.0):
        """Send a REQUEST and wait for RESPONSE/ERROR. Returns parsed JSON."""
        req_id = self._next_req_id()
        body = {"method": method}
        if params is not None:
            body["params"] = params
        payload = json.dumps(body).encode("utf-8")

        msg_type, resp_payload = await self._send_and_wait(
            MSG_REQUEST, req_id, payload, timeout=timeout)

        resp = json.loads(resp_payload.decode("utf-8"))
        if msg_type == MSG_ERROR:
            raise RPCError(resp.get("code", 500), resp.get("message", "Unknown"))
        return resp.get("result")

    async def subscribe(self, channel: str, timeout: float = 5.0):
        """Subscribe to a channel."""
        req_id = self._next_req_id()
        payload = channel.encode("utf-8")
        msg_type, resp_payload = await self._send_and_wait(
            MSG_SUBSCRIBE, req_id, payload, timeout=timeout)
        resp = json.loads(resp_payload.decode("utf-8"))
        return resp.get("result")

    async def unsubscribe(self, channel: str, timeout: float = 5.0):
        """Unsubscribe from a channel."""
        req_id = self._next_req_id()
        payload = channel.encode("utf-8")
        msg_type, resp_payload = await self._send_and_wait(
            MSG_UNSUBSCRIBE, req_id, payload, timeout=timeout)
        resp = json.loads(resp_payload.decode("utf-8"))
        return resp.get("result")

    async def wait_event(self, timeout: float = 5.0):
        """Wait for an EVENT from the server."""
        return await asyncio.wait_for(self._event_queue.get(), timeout=timeout)

    async def request_with_id(self, method: str, params: dict,
                               request_id: int, timeout: float = 5.0):
        """Send a REQUEST with a specific request_id. Returns (msg_type, parsed_json)."""
        body = {"method": method, "params": params}
        payload = json.dumps(body).encode("utf-8")

        msg_type, resp_payload = await self._send_and_wait(
            MSG_REQUEST, request_id, payload, timeout=timeout)

        resp = json.loads(resp_payload.decode("utf-8"))
        return msg_type, resp

    async def ping_with_id(self, request_id: int, data: bytes = b"",
                            timeout: float = 5.0):
        """Send PING with a specific request_id."""
        msg_type, payload = await self._send_and_wait(
            MSG_PING, request_id, data, timeout=timeout)
        return msg_type, payload


class RPCError(Exception):
    """Raised when the server returns an ERROR response."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"RPC Error {code}: {message}")
