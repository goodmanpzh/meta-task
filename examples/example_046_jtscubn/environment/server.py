#!/usr/bin/env python3
"""
MiniRPC Protocol Server Implementation

A binary RPC server implementing the MiniRPC protocol (see protocol.md).
Supports: PING/PONG, REQUEST/RESPONSE, SUBSCRIBE/UNSUBSCRIBE/EVENT.

Usage:
    python server.py [--port PORT]
"""

import asyncio
import argparse
import json
import struct
import logging
import signal
import sys
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("minirpc")

# Protocol constants
MAGIC = 0xDEADBEEF
VERSION = 0x01
HEADER_SIZE = 12  # magic(4) + version(1) + msgtype(1) + reqid(2) + paylen(4)
CRC_SIZE = 2

# Message types
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
    """Construct a complete MiniRPC frame with header, payload, and CRC."""
    header = struct.pack("!IBBHI",
                         MAGIC, VERSION, msg_type, request_id, len(payload))
    frame_without_crc = header + payload
    crc = crc16_ccitt(header)
    return frame_without_crc + struct.pack("!H", crc)


class MiniRPCServer:
    """Async MiniRPC protocol server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9777):
        self.host = host
        self.port = port
        self._kv_store: dict = {}
        self._subscriptions: dict[str, set] = defaultdict(set)
        self._client_writers: dict[int, asyncio.StreamWriter] = {}
        self._client_counter = 0
        self._lock = asyncio.Lock()
        self._server = None

    async def start(self):
        """Start the server."""
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        addrs = [sock.getsockname() for sock in self._server.sockets]
        logger.info(f"MiniRPC server listening on {addrs}")
        async with self._server:
            await self._server.serve_forever()

    async def _read_exact(self, reader: asyncio.StreamReader, n: int) -> bytes:
        """Read exactly n bytes from the stream."""
        data = b""
        while len(data) < n:
            chunk = await asyncio.wait_for(reader.read(n - len(data)), timeout=30.0)
            if not chunk:
                raise ConnectionError("Connection closed while reading")
            data += chunk
        return data

    async def _read_frame(self, reader: asyncio.StreamReader):
        """Read and parse a single MiniRPC frame from the stream.

        Returns (msg_type, request_id, payload) or raises on error.
        """
        # Read header
        header_data = await self._read_exact(reader, HEADER_SIZE)

        magic = struct.unpack("!I", header_data[0:4])[0]
        if magic != MAGIC:
            raise ValueError(f"Invalid magic: 0x{magic:08X}")

        version = header_data[4]
        if version != VERSION:
            raise ValueError(f"Unsupported version: {version}")

        msg_type = header_data[5]
        request_id = struct.unpack("<H", header_data[6:8])[0]
        payload_length = struct.unpack("<I", header_data[8:12])[0]

        # Read payload
        if payload_length > 0:
            payload = await self._read_exact(reader, payload_length - 1)
        else:
            payload = b""

        # Read CRC
        crc_data = await self._read_exact(reader, CRC_SIZE)
        received_crc = struct.unpack("!H", crc_data)[0]

        # Verify CRC
        frame_data = header_data + payload
        computed_crc = crc16_ccitt(frame_data)
        if received_crc != computed_crc:
            raise ValueError(
                f"CRC mismatch: received=0x{received_crc:04X}, "
                f"computed=0x{computed_crc:04X}"
            )

        return msg_type, request_id, payload

    async def _send_frame(self, writer: asyncio.StreamWriter,
                          msg_type: int, request_id: int, payload: bytes):
        """Send a MiniRPC frame."""
        frame = build_frame(msg_type, request_id, payload)
        writer.write(frame)
        await writer.drain()

    async def _send_error(self, writer: asyncio.StreamWriter,
                          request_id: int, code: int, message: str):
        """Send an error response."""
        payload = json.dumps({"code": code, "message": message}).encode("utf-8")
        await self._send_frame(writer, MSG_RESPONSE, request_id, payload)

    async def _send_response(self, writer: asyncio.StreamWriter,
                             request_id: int, result):
        """Send a success response."""
        payload = json.dumps({"result": result}).encode("utf-8")
        await self._send_frame(writer, MSG_RESPONSE, request_id, payload)

    async def _handle_ping(self, writer: asyncio.StreamWriter,
                           request_id: int, payload: bytes):
        """Handle PING: respond with PONG."""
        await self._send_frame(writer, MSG_PONG, request_id, b"")

    async def _handle_request(self, writer: asyncio.StreamWriter,
                              request_id: int, payload: bytes):
        """Handle REQUEST: dispatch to the appropriate RPC method."""
        try:
            body = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            await self._send_error(writer, request_id, 400, f"Invalid JSON: {e}")
            return

        method = body.get("method")
        params = body.get("params", {})

        if method == "echo":
            msg = params.get("message", "")
            await self._send_response(writer, request_id, {"message": msg})

        elif method == "add":
            a = params.get("a", 0)
            b = params.get("b", 0)
            await self._send_response(writer, request_id, {"sum": a + b})

        elif method == "kv.set":
            key = params.get("key")
            value = params.get("value")
            if key is None:
                await self._send_error(writer, request_id, 400, "Missing 'key'")
                return
            self._kv_store[key] = value
            await self._send_response(writer, request_id,
                                       {"key": key, "stored": True})

        elif method == "kv.get":
            key = params.get("key")
            if key is None:
                await self._send_error(writer, request_id, 400, "Missing 'key'")
                return
            if key not in self._kv_store:
                await self._send_error(writer, request_id, 404, "Key not found")
                return
            await self._send_response(writer, request_id,
                                       {"key": key,
                                        "value": self._kv_store[key]})

        elif method == "publish":
            channel = params.get("channel")
            data = params.get("data")
            if channel is None:
                await self._send_error(writer, request_id, 400,
                                        "Missing 'channel'")
                return
            subscribers = await self._publish(channel, data)
            await self._send_response(writer, request_id,
                                       {"channel": channel,
                                        "subscribers": subscribers})
        else:
            await self._send_error(writer, request_id, 405,
                                    f"Unknown method: {method}")

    async def _handle_subscribe(self, writer: asyncio.StreamWriter,
                                client_id: int, request_id: int,
                                payload: bytes):
        """Handle SUBSCRIBE: add client to channel subscription list."""
        channel = payload.decode("utf-8")
        async with self._lock:
            self._subscriptions[channel].add(client_id)
        await self._send_response(writer, request_id, "subscribed")

    async def _handle_unsubscribe(self, writer: asyncio.StreamWriter,
                                  client_id: int, request_id: int,
                                  payload: bytes):
        """Handle UNSUBSCRIBE: remove client from channel subscription list."""
        channel = payload.decode("utf-8")
        async with self._lock:
            self._subscriptions[channel].discard(client_id)
        await self._send_response(writer, request_id, "unsubscribed")

    async def _publish(self, channel: str, data) -> int:
        """Publish an event to all subscribers of a channel."""
        event_payload = json.dumps({
            "channel": channel,
            "data": data
        }).encode("utf-8")

        count = 0
        async with self._lock:
            for ch, subscriber_ids in self._subscriptions.items():
                for client_id in subscriber_ids:
                    writer = self._client_writers.get(client_id)
                    if writer and not writer.is_closing():
                        try:
                            await self._send_frame(
                                writer, MSG_EVENT, 0x0000, event_payload
                            )
                            count += 1
                        except Exception:
                            pass

        return count

    async def _remove_client(self, client_id: int):
        """Clean up a disconnected client."""
        # Remove from subscriptions
        for channel in list(self._subscriptions.keys()):
            self._subscriptions[channel].discard(client_id)
            if not self._subscriptions[channel]:
                del self._subscriptions[channel]

        # Remove writer reference
        writer = self._client_writers.pop(client_id, None)
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_client(self, reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter):
        """Handle a single client connection."""
        self._client_counter += 1
        client_id = self._client_counter
        addr = writer.get_extra_info("peername")
        logger.info(f"Client {client_id} connected from {addr}")

        async with self._lock:
            self._client_writers[client_id] = writer

        try:
            while True:
                msg_type, request_id, payload = await self._read_frame(reader)

                if msg_type == MSG_PING:
                    await self._handle_ping(writer, request_id, payload)

                elif msg_type == MSG_REQUEST:
                    await self._handle_request(writer, request_id, payload)

                elif msg_type == MSG_SUBSCRIBE:
                    await self._handle_subscribe(
                        writer, client_id, request_id, payload
                    )

                elif msg_type == MSG_UNSUBSCRIBE:
                    await self._handle_unsubscribe(
                        writer, client_id, request_id, payload
                    )

                else:
                    await self._send_error(
                        writer, request_id, 400,
                        f"Unsupported message type: 0x{msg_type:02X}"
                    )

        except ConnectionError:
            logger.info(f"Client {client_id} disconnected")
        except asyncio.TimeoutError:
            logger.warning(f"Client {client_id} timed out")
        except ValueError as e:
            logger.warning(f"Client {client_id} protocol error: {e}")
            try:
                await self._send_error(writer, 0x0000, 400, str(e))
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Client {client_id} unexpected error: {e}")
        finally:
            await self._remove_client(client_id)
            logger.info(f"Client {client_id} cleaned up")


def main():
    parser = argparse.ArgumentParser(description="MiniRPC Server")
    parser.add_argument("--port", type=int, default=9777,
                        help="Port to listen on (default: 9777)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    server = MiniRPCServer(host=args.host, port=args.port)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        loop.call_soon_threadsafe(loop.stop)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        loop.run_until_complete(server.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
