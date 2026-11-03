#!/bin/bash
set -e

# Kill any existing server
pkill -f "python.*server.py" 2>/dev/null || true
sleep 0.5

cd /app

# Apply all fixes using a single Python patching script
python3 << 'PATCHSCRIPT'
with open('server.py', 'r') as f:
    content = f.read()

# Fix 1: build_frame CRC computed over header only -> should be header+payload
content = content.replace(
    'crc = crc16_ccitt(header)\n    return frame_without_crc',
    'crc = crc16_ccitt(frame_without_crc)\n    return frame_without_crc'
)

# Fix 2: request_id parsed as little-endian -> should be big-endian
content = content.replace(
    'request_id = struct.unpack("<H", header_data[6:8])[0]',
    'request_id = struct.unpack("!H", header_data[6:8])[0]'
)

# Fix 3: payload_length parsed as little-endian -> should be big-endian
content = content.replace(
    'payload_length = struct.unpack("<I", header_data[8:12])[0]',
    'payload_length = struct.unpack("!I", header_data[8:12])[0]'
)

# Fix 4: Off-by-one in payload read
content = content.replace(
    'payload = await self._read_exact(reader, payload_length - 1)',
    'payload = await self._read_exact(reader, payload_length)'
)

# Fix 5: _send_error uses MSG_RESPONSE instead of MSG_ERROR
# Must be careful to only change the one in _send_error, not _send_response
content = content.replace(
    '    async def _send_error(self, writer: asyncio.StreamWriter,\n'
    '                          request_id: int, code: int, message: str):\n'
    '        """Send an error response."""\n'
    '        payload = json.dumps({"code": code, "message": message}).encode("utf-8")\n'
    '        await self._send_frame(writer, MSG_RESPONSE, request_id, payload)',
    '    async def _send_error(self, writer: asyncio.StreamWriter,\n'
    '                          request_id: int, code: int, message: str):\n'
    '        """Send an error response."""\n'
    '        payload = json.dumps({"code": code, "message": message}).encode("utf-8")\n'
    '        await self._send_frame(writer, MSG_ERROR, request_id, payload)'
)

# Fix 6: _handle_ping sends empty payload instead of echoing
content = content.replace(
    '        await self._send_frame(writer, MSG_PONG, request_id, b"")',
    '        await self._send_frame(writer, MSG_PONG, request_id, payload)'
)

# Fix 7: _publish iterates all channels instead of just the target channel
content = content.replace(
    '            for ch, subscriber_ids in self._subscriptions.items():\n'
    '                for client_id in subscriber_ids:',
    '            subscriber_ids = self._subscriptions.get(channel, set())\n'
    '            if True:\n'
    '                for client_id in subscriber_ids:'
)

# Fix 8: _remove_client lacks lock protection
content = content.replace(
    '    async def _remove_client(self, client_id: int):\n'
    '        """Clean up a disconnected client."""\n'
    '        # Remove from subscriptions\n'
    '        for channel in list(self._subscriptions.keys()):',
    '    async def _remove_client(self, client_id: int):\n'
    '        """Clean up a disconnected client."""\n'
    '        async with self._lock:\n'
    '          # Remove from subscriptions\n'
    '          for channel in list(self._subscriptions.keys()):'
)
content = content.replace(
    '            self._subscriptions[channel].discard(client_id)\n'
    '            if not self._subscriptions[channel]:\n'
    '                del self._subscriptions[channel]\n'
    '\n'
    '        # Remove writer reference\n'
    '        writer = self._client_writers.pop(client_id, None)',
    '              self._subscriptions[channel].discard(client_id)\n'
    '              if not self._subscriptions[channel]:\n'
    '                  del self._subscriptions[channel]\n'
    '\n'
    '          # Remove writer reference\n'
    '          writer = self._client_writers.pop(client_id, None)'
)

with open('server.py', 'w') as f:
    f.write(content)

print("All patches applied successfully")
PATCHSCRIPT

# Start the fixed server in background
python server.py --port 9777 &
SERVER_PID=$!

# Wait for server to be ready
for i in $(seq 1 20); do
    if python3 -c "import socket; s=socket.create_connection(('127.0.0.1', 9777), timeout=1); s.close()" 2>/dev/null; then
        echo "Server is ready (PID: $SERVER_PID)"
        exit 0
    fi
    sleep 0.5
done

echo "ERROR: Server failed to start"
exit 1
