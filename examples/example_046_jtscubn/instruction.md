**Problem:** MiniRPC binary protocol server fails all client tests — no responses received

**Context:**
`/app/server.py` implements a custom binary RPC-over-TCP server following the MiniRPC protocol specification in `/app/protocol.md`. The server should handle PING/PONG keepalive, JSON-RPC-style method calls, and pub/sub messaging — all using a binary framing format with CRC-16 integrity checks.

The protocol spec is the source of truth. The server is supposed to conform to it, but something is broken.

**Reproduction:**
```
$ cd /app
$ pip install pytest pytest-asyncio
$ python server.py &
$ python -m pytest /tests/test_outputs.py -v --timeout=30
```

All 25 tests time out or fail. No successful request-response cycle completes.

**Expected:** All tests pass. The server correctly implements the MiniRPC protocol:
- PING/PONG with payload echo
- RPC methods: `echo`, `add`, `kv.set`, `kv.get`, `publish`
- SUBSCRIBE/UNSUBSCRIBE with channel-scoped event delivery
- Proper error responses with correct message type codes
- Correct binary framing: big-endian fields, CRC-16/CCITT over header+payload
- Concurrent client support via asyncio

**Actual:** Every test times out. The client sends well-formed frames per the spec but never receives a valid response.

| Aspect | Expected | Actual |
|--------|----------|--------|
| PING/PONG | PONG echoes PING payload | No valid response received |
| CRC-16 | Computed over header + payload | Unknown — responses don't parse |
| Error responses | Use message type 0x20 | Unknown |
| Pub/Sub | Events scoped to subscribed channel | Unknown |

**Files:**
- `/app/server.py` — The server implementation (this is what needs fixing)
- `/app/protocol.md` — The protocol specification (do NOT modify)

**Constraints:**
- Only modify `/app/server.py`
- Do not modify `/app/protocol.md` or any test files
- The server must listen on port `9777`
- The server must be running in the background when tests execute
