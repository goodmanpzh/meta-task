# MiniRPC Binary Protocol Specification v1

## Overview

MiniRPC is a lightweight binary RPC protocol over TCP. It supports request/response,
ping/pong keepalive, and publish/subscribe messaging patterns. All communication
consists of **frames** sent over a persistent TCP connection.

## Frame Format

Every frame has the following structure:

```
+--------+--------+--------+----------+---------+---------+-------+
| Magic  | Version| MsgType| RequestID| PayLen  | Payload | CRC16 |
| 4 bytes| 1 byte | 1 byte | 2 bytes  | 4 bytes | N bytes | 2 bytes|
+--------+--------+--------+----------+---------+---------+-------+
```

### Field Details

| Field     | Size    | Encoding     | Description                                      |
|-----------|---------|--------------|--------------------------------------------------|
| Magic     | 4 bytes | Big-endian   | Always `0xDEADBEEF`                             |
| Version   | 1 byte  | Unsigned     | Protocol version, currently `0x01`               |
| MsgType   | 1 byte  | Unsigned     | Message type code (see below)                    |
| RequestID | 2 bytes | Big-endian   | Caller-assigned request identifier               |
| PayLen    | 4 bytes | Big-endian   | Length of the Payload field in bytes              |
| Payload   | N bytes | Raw bytes    | Message-specific payload (may be 0 bytes)        |
| CRC16     | 2 bytes | Big-endian   | CRC-16/CCITT checksum of all preceding bytes     |

**CRC-16/CCITT**: The checksum is computed over the concatenation of all preceding
fields (Magic + Version + MsgType + RequestID + PayLen + Payload). The polynomial
is `0x1021` with initial value `0xFFFF`. The CRC is appended in big-endian byte order.

### Total frame size

`Header (12 bytes) + Payload (PayLen bytes) + CRC (2 bytes) = 14 + PayLen bytes`

## Message Types

| Code   | Name        | Direction        | Description                          |
|--------|-------------|------------------|--------------------------------------|
| `0x01` | PING        | Client → Server  | Keepalive ping                       |
| `0x02` | PONG        | Server → Client  | Keepalive pong (echoes PING payload) |
| `0x10` | REQUEST     | Client → Server  | RPC method invocation                |
| `0x11` | RESPONSE    | Server → Client  | RPC method result                    |
| `0x20` | ERROR       | Server → Client  | Error response                       |
| `0x30` | SUBSCRIBE   | Client → Server  | Subscribe to a named channel         |
| `0x31` | EVENT       | Server → Client  | Event published on a channel         |
| `0x32` | UNSUBSCRIBE | Client → Server  | Unsubscribe from a named channel     |

## Message Payloads

### PING (0x01)
- Payload: Arbitrary bytes (may be empty).

### PONG (0x02)
- Payload: Must echo the exact payload from the corresponding PING.
- RequestID: Must match the PING's RequestID.

### REQUEST (0x10)
- Payload: UTF-8 encoded JSON object with fields:
  - `"method"` (string): Method name to invoke.
  - `"params"` (object, optional): Method parameters.
- Example: `{"method": "echo", "params": {"message": "hello"}}`

### RESPONSE (0x11)
- Payload: UTF-8 encoded JSON object with fields:
  - `"result"` (any): Method return value.
- RequestID: Must match the REQUEST's RequestID.

### ERROR (0x20)
- Payload: UTF-8 encoded JSON object with fields:
  - `"code"` (integer): Error code.
  - `"message"` (string): Human-readable error description.
- RequestID: Must match the REQUEST's RequestID (or 0x0000 for unsolicited errors).

### SUBSCRIBE (0x30)
- Payload: UTF-8 encoded channel name string (e.g., `"events.temperature"`).
- Server responds with a RESPONSE containing `{"result": "subscribed"}`.

### UNSUBSCRIBE (0x32)
- Payload: UTF-8 encoded channel name string.
- Server responds with a RESPONSE containing `{"result": "unsubscribed"}`.

### EVENT (0x31)
- Payload: UTF-8 encoded JSON object with fields:
  - `"channel"` (string): The channel name.
  - `"data"` (any): The event data.
- RequestID: Always `0x0000` for server-pushed events.

## Built-in RPC Methods

The server must implement these methods:

### `echo`
- Params: `{"message": <string>}`
- Returns: `{"result": {"message": <string>}}` (echoes the message back)

### `add`
- Params: `{"a": <number>, "b": <number>}`
- Returns: `{"result": {"sum": <number>}}`

### `kv.set`
- Params: `{"key": <string>, "value": <any>}`
- Returns: `{"result": {"key": <string>, "stored": true}}`
- Stores the key-value pair in an in-memory store.

### `kv.get`
- Params: `{"key": <string>}`
- Returns: `{"result": {"key": <string>, "value": <any>}}` if key exists.
- Returns ERROR with code `404` and message `"Key not found"` if key doesn't exist.

### `publish`
- Params: `{"channel": <string>, "data": <any>}`
- Delivers an EVENT to all clients subscribed to the given channel.
- Returns: `{"result": {"channel": <string>, "subscribers": <int>}}`

## Error Codes

| Code | Meaning               |
|------|-----------------------|
| 400  | Bad request           |
| 404  | Not found             |
| 405  | Method not allowed    |
| 500  | Internal server error |

## Connection Semantics

- The server listens on a configurable TCP port (default: 9777).
- Multiple clients may connect simultaneously.
- Each client connection is independent.
- The server must handle frames sequentially per connection but serve multiple
  connections concurrently.
- If a frame fails CRC validation, the server must send an ERROR frame with code
  400 and message `"CRC mismatch"`, then close the connection.
- If the magic bytes are wrong, the server must close the connection immediately.
- The server should handle client disconnections gracefully without crashing.
