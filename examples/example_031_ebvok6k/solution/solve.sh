#!/bin/bash
set -e

# Step 1: Create the proxy configuration from the template
cp /app/proxy.conf.template /app/proxy.conf

# Step 2: Write the complete, working SOCKS5 server
cat > /app/socks5_server.py << 'PYEOF'
#!/usr/bin/env python3
"""
SOCKS5 Proxy Server - Complete Implementation
Implements RFC 1928 (SOCKS5) and RFC 1929 (Username/Password Auth)
"""

import socket
import struct
import threading
import select
import configparser
import sys
import signal

SOCKS_VERSION = 0x05
AUTH_VERSION = 0x01

# SOCKS5 auth methods
AUTH_NONE = 0x00
AUTH_USERPASS = 0x02
AUTH_NO_ACCEPTABLE = 0xFF

# SOCKS5 commands
CMD_CONNECT = 0x01
CMD_BIND = 0x02
CMD_UDP_ASSOCIATE = 0x03

# SOCKS5 address types
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04

# SOCKS5 reply codes
REP_SUCCESS = 0x00
REP_GENERAL_FAILURE = 0x01
REP_NOT_ALLOWED = 0x02
REP_NETWORK_UNREACHABLE = 0x03
REP_HOST_UNREACHABLE = 0x04
REP_CONNECTION_REFUSED = 0x05
REP_TTL_EXPIRED = 0x06
REP_COMMAND_NOT_SUPPORTED = 0x07
REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08


def recvall(sock, n):
    """Receive exactly n bytes from socket."""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed while reading")
        data += chunk
    return data


def send_reply(client_sock, rep, atyp=ATYP_IPV4, bind_addr='0.0.0.0', bind_port=0):
    """Send a SOCKS5 reply to the client."""
    reply = struct.pack('!BBB', SOCKS_VERSION, rep, 0x00)
    if atyp == ATYP_IPV4:
        reply += struct.pack('!B', ATYP_IPV4)
        reply += socket.inet_aton(bind_addr)
    elif atyp == ATYP_IPV6:
        reply += struct.pack('!B', ATYP_IPV6)
        reply += socket.inet_pton(socket.AF_INET6, bind_addr)
    else:
        # Default to IPv4 0.0.0.0 for error replies
        reply += struct.pack('!B', ATYP_IPV4)
        reply += socket.inet_aton('0.0.0.0')
    reply += struct.pack('!H', bind_port)
    client_sock.sendall(reply)


def relay_data(client_sock, remote_sock):
    """Bidirectional data relay between client and remote."""
    sockets = [client_sock, remote_sock]
    try:
        while True:
            readable, _, exceptional = select.select(sockets, [], sockets, 60)
            if exceptional:
                break
            if not readable:
                # Timeout
                break
            for sock in readable:
                data = sock.recv(8192)
                if not data:
                    return
                if sock is client_sock:
                    remote_sock.sendall(data)
                else:
                    client_sock.sendall(data)
    except (ConnectionError, OSError):
        pass


def handle_client(client_sock, config):
    """Handle a single SOCKS5 client connection."""
    remote_sock = None
    try:
        # === Step 1: Client Greeting ===
        # VER | NMETHODS | METHODS
        header = recvall(client_sock, 2)
        ver = header[0]
        nmethods = header[1]

        if ver != SOCKS_VERSION:
            client_sock.sendall(bytes([SOCKS_VERSION, AUTH_NO_ACCEPTABLE]))
            client_sock.close()
            return

        methods = recvall(client_sock, nmethods)

        # Select authentication method - prefer username/password
        if AUTH_USERPASS in methods:
            client_sock.sendall(bytes([SOCKS_VERSION, AUTH_USERPASS]))
        elif AUTH_NONE in methods:
            client_sock.sendall(bytes([SOCKS_VERSION, AUTH_NONE]))
        else:
            client_sock.sendall(bytes([SOCKS_VERSION, AUTH_NO_ACCEPTABLE]))
            client_sock.close()
            return

        # === Step 2: Authentication ===
        if AUTH_USERPASS in methods:
            # Read auth subnegotiation (RFC 1929)
            # VER(1) | ULEN(1) | UNAME(1-255) | PLEN(1) | PASSWD(1-255)
            auth_header = recvall(client_sock, 2)
            auth_ver = auth_header[0]
            ulen = auth_header[1]

            username = recvall(client_sock, ulen).decode('utf-8')

            plen_data = recvall(client_sock, 1)
            plen = plen_data[0]
            password = recvall(client_sock, plen).decode('utf-8')

            valid_user = config.get('auth', 'username', fallback='admin')
            valid_pass = config.get('auth', 'password', fallback='proxy_pass')

            if username == valid_user and password == valid_pass:
                # Auth success: VER=0x01, STATUS=0x00
                client_sock.sendall(bytes([AUTH_VERSION, 0x00]))
            else:
                # Auth failure: VER=0x01, STATUS=0x01
                client_sock.sendall(bytes([AUTH_VERSION, 0x01]))
                client_sock.close()
                return

        # === Step 3: SOCKS5 Request ===
        # VER | CMD | RSV | ATYP | DST.ADDR | DST.PORT
        req_header = recvall(client_sock, 4)
        req_ver = req_header[0]
        cmd = req_header[1]
        rsv = req_header[2]
        atyp = req_header[3]

        if req_ver != SOCKS_VERSION:
            send_reply(client_sock, REP_GENERAL_FAILURE)
            client_sock.close()
            return

        # Only CONNECT is supported
        if cmd != CMD_CONNECT:
            send_reply(client_sock, REP_COMMAND_NOT_SUPPORTED)
            client_sock.close()
            return

        # Parse destination address
        dst_addr = None
        addr_family = socket.AF_INET

        if atyp == ATYP_IPV4:
            raw_addr = recvall(client_sock, 4)
            dst_addr = socket.inet_ntoa(raw_addr)
        elif atyp == ATYP_DOMAIN:
            domain_len = recvall(client_sock, 1)[0]
            domain = recvall(client_sock, domain_len).decode('utf-8')
            try:
                dst_addr = socket.gethostbyname(domain)
            except socket.gaierror:
                send_reply(client_sock, REP_HOST_UNREACHABLE)
                client_sock.close()
                return
        elif atyp == ATYP_IPV6:
            raw_addr = recvall(client_sock, 16)
            dst_addr = socket.inet_ntop(socket.AF_INET6, raw_addr)
            addr_family = socket.AF_INET6
        else:
            send_reply(client_sock, REP_ADDRESS_TYPE_NOT_SUPPORTED)
            client_sock.close()
            return

        # Read destination port
        raw_port = recvall(client_sock, 2)
        dst_port = struct.unpack('!H', raw_port)[0]

        # === Step 4: Connect to destination ===
        try:
            remote_sock = socket.socket(addr_family, socket.SOCK_STREAM)
            remote_sock.settimeout(10)
            remote_sock.connect((dst_addr, dst_port))
            remote_sock.settimeout(None)

            # Get the bound address
            bind_addr, bind_port = remote_sock.getsockname()[:2]

            # Send success reply
            if addr_family == socket.AF_INET6:
                send_reply(client_sock, REP_SUCCESS, ATYP_IPV6, bind_addr, bind_port)
            else:
                send_reply(client_sock, REP_SUCCESS, ATYP_IPV4, bind_addr, bind_port)

        except ConnectionRefusedError:
            send_reply(client_sock, REP_CONNECTION_REFUSED)
            client_sock.close()
            return
        except socket.timeout:
            send_reply(client_sock, REP_HOST_UNREACHABLE)
            client_sock.close()
            return
        except OSError as e:
            if e.errno == 101:  # Network unreachable
                send_reply(client_sock, REP_NETWORK_UNREACHABLE)
            elif e.errno == 113:  # No route to host
                send_reply(client_sock, REP_HOST_UNREACHABLE)
            else:
                send_reply(client_sock, REP_GENERAL_FAILURE)
            client_sock.close()
            return

        # === Step 5: Data relay ===
        relay_data(client_sock, remote_sock)

    except Exception as e:
        print(f"Error handling client: {e}", file=sys.stderr)
    finally:
        try:
            client_sock.close()
        except:
            pass
        if remote_sock:
            try:
                remote_sock.close()
            except:
                pass


def main():
    config = configparser.ConfigParser()
    config.read('/app/proxy.conf')

    port = config.getint('server', 'port', fallback=1080)
    bind_addr = config.get('server', 'bind', fallback='0.0.0.0')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((bind_addr, port))
    server.listen(128)
    print(f"SOCKS5 proxy listening on {bind_addr}:{port}", flush=True)

    def shutdown_handler(signum, frame):
        print("Shutting down...", flush=True)
        server.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    while True:
        try:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client, config))
            t.daemon = True
            t.start()
        except OSError:
            break


if __name__ == '__main__':
    main()
PYEOF

chmod +x /app/socks5_server.py

# Step 3: Start the SOCKS5 proxy in the background
# Kill any existing instance first
for pid in $(pgrep -f "python3 /app/socks5_server.py" 2>/dev/null || true); do
    kill "$pid" 2>/dev/null || true
done
sleep 1

nohup python3 /app/socks5_server.py > /var/log/socks5_proxy.log 2>&1 &
echo "SOCKS5 proxy PID: $!"

# Wait for server to start
sleep 2

# Verify the server is running
if python3 -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',1080)); s.close(); print('OK')" 2>/dev/null; then
    echo "SOCKS5 proxy server is running on port 1080"
else
    echo "ERROR: SOCKS5 proxy server failed to start"
    cat /var/log/socks5_proxy.log
    exit 1
fi
