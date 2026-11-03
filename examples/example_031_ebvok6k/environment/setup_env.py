#!/usr/bin/env python3
"""
Generate the environment files for the SOCKS5 proxy task:
- Buggy starter code at /app/socks5_server.py
- Protocol notes at /app/docs/socks5_notes.md
- PCAP capture at /app/captures/working_session.pcap
- Config template at /app/proxy.conf.template
"""
import os
import struct
import socket

def create_directories():
    os.makedirs("/app/docs", exist_ok=True)
    os.makedirs("/app/captures", exist_ok=True)

def create_buggy_server():
    """Create a partially-written SOCKS5 server with several bugs."""
    code = r'''#!/usr/bin/env python3
"""
SOCKS5 Proxy Server - Work in Progress
Author: Priya Sharma
Status: INCOMPLETE - handshake is buggy, CONNECT partially done
"""

import socket
import struct
import threading
import select
import configparser
import sys

def load_config(path="/app/proxy.conf"):
    config = configparser.ConfigParser()
    config.read(path)
    return config

def handle_client(client_sock, config):
    """Handle a single SOCKS5 client connection."""
    try:
        # Step 1: Read client greeting
        # Client sends: VER | NMETHODS | METHODS
        greeting = client_sock.recv(256)
        if len(greeting) < 3:
            client_sock.close()
            return

        ver = greeting[0]
        nmethods = greeting[1]
        methods = greeting[2:2+nmethods]

        # BUG: Priya checks for SOCKS4 version instead of SOCKS5
        if ver != 0x04:
            # Send failure and close
            client_sock.sendall(b'\x05\xFF')
            client_sock.close()
            return

        # Select authentication method
        # BUG: Logic is inverted - she checks if method is NOT in the list
        if 0x02 not in methods:
            # Choose username/password auth
            client_sock.sendall(b'\x05\x02')
        else:
            # No acceptable methods
            client_sock.sendall(b'\x05\xFF')
            client_sock.close()
            return

        # Step 2: Username/Password authentication (RFC 1929)
        auth_data = client_sock.recv(256)
        if len(auth_data) < 3:
            client_sock.close()
            return

        # BUG: Priya reads the version byte but uses wrong offset for username
        auth_ver = auth_data[0]
        ulen = auth_data[1]
        username = auth_data[2:2+ulen].decode('utf-8')
        # BUG: Password offset calculation is wrong - off by one
        plen = auth_data[2+ulen+1]
        password = auth_data[3+ulen+1:3+ulen+1+plen].decode('utf-8')

        valid_user = config.get('auth', 'username', fallback='admin')
        valid_pass = config.get('auth', 'password', fallback='proxy_pass')

        if username == valid_user and password == valid_pass:
            # Auth success
            # BUG: Should send version 0x01 for auth subnegotiation, not 0x05
            client_sock.sendall(b'\x05\x00')
        else:
            # Auth failure
            client_sock.sendall(b'\x01\x01')
            client_sock.close()
            return

        # Step 3: Read CONNECT request
        # Client sends: VER | CMD | RSV | ATYP | DST.ADDR | DST.PORT
        request = client_sock.recv(256)
        if len(request) < 4:
            client_sock.close()
            return

        req_ver = request[0]
        cmd = request[1]
        rsv = request[2]
        atyp = request[3]

        if cmd != 0x01:
            # Only CONNECT is supported
            # TODO: Send proper error reply
            client_sock.close()
            return

        # Parse destination address based on address type
        if atyp == 0x01:
            # IPv4
            if len(request) < 10:
                client_sock.close()
                return
            dst_addr = socket.inet_ntoa(request[4:8])
            dst_port = struct.unpack('!H', request[8:10])[0]
        elif atyp == 0x03:
            # Domain name
            # TODO: Priya started this but didn't finish
            # BUG: She reads domain length but uses wrong slice
            domain_len = request[4]
            domain = request[5:5+domain_len+1].decode('utf-8')  # off-by-one: includes extra byte
            # TODO: resolve domain and connect
            # dst_port = ???
            client_sock.close()
            return
        elif atyp == 0x04:
            # IPv6
            # TODO: Not implemented yet
            client_sock.close()
            return
        else:
            client_sock.close()
            return

        # TODO: Connect to destination and relay data
        # Priya's notes say she was going to use select() for the relay
        # but never got to it

        client_sock.close()

    except Exception as e:
        print(f"Error handling client: {e}", file=sys.stderr)
        try:
            client_sock.close()
        except:
            pass

def main():
    config = load_config()
    port = config.getint('server', 'port', fallback=1080)
    bind_addr = config.get('server', 'bind', fallback='0.0.0.0')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((bind_addr, port))
    server.listen(5)
    print(f"SOCKS5 proxy listening on {bind_addr}:{port}")

    while True:
        client, addr = server.accept()
        print(f"Connection from {addr}")
        t = threading.Thread(target=handle_client, args=(client, config))
        t.daemon = True
        t.start()

if __name__ == '__main__':
    main()
'''
    with open("/app/socks5_server.py", "w") as f:
        f.write(code)

def create_protocol_notes():
    """Create partial SOCKS5 protocol notes (intentionally incomplete)."""
    notes = """# SOCKS5 Protocol Notes
## Priya's Reference Notes - DRAFT

### Overview
SOCKS5 is defined in RFC 1928. It provides a framework for client-server
applications to conveniently and securely use the services of a network firewall.

### Connection Flow
1. Client connects to SOCKS server
2. Client sends greeting with supported auth methods
3. Server selects an auth method
4. Authentication subnegotiation (if required)
5. Client sends request (CONNECT, BIND, or UDP ASSOCIATE)
6. Server connects to target and replies
7. Bidirectional data relay begins

### Greeting (Client -> Server)

```
+----+----------+----------+
|VER | NMETHODS | METHODS  |
+----+----------+----------+
| 1  |    1     | 1 to 255 |
+----+----------+----------+
```

- VER: Protocol version (0x05 for SOCKS5)
- NMETHODS: Number of method identifiers
- METHODS: List of supported methods
  - 0x00: No authentication
  - 0x02: Username/Password

### Server Method Selection (Server -> Client)

```
+----+--------+
|VER | METHOD |
+----+--------+
| 1  |   1    |
+----+--------+
```

- VER: 0x05
- METHOD: Selected method, or 0xFF if none acceptable

### Username/Password Auth (RFC 1929)

Client sends:
```
+----+------+----------+------+----------+
|VER | ULEN |  UNAME   | PLEN |  PASSWD  |
+----+------+----------+------+----------+
| 1  |  1   | 1 to 255 |  1   | 1 to 255 |
+----+------+----------+------+----------+
```

Note: The VER field in auth subnegotiation is 0x01 (not 0x05!)

Server replies:
```
+----+--------+
|VER | STATUS |
+----+--------+
| 1  |   1    |
+----+--------+
```
- VER: 0x01
- STATUS: 0x00 for success, non-zero for failure

### CONNECT Request

```
+----+-----+-------+------+----------+----------+
|VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
+----+-----+-------+------+----------+----------+
| 1  |  1  | X'00' |  1   | Variable |    2     |
+----+-----+-------+------+----------+----------+
```

- CMD: 0x01 = CONNECT, 0x02 = BIND, 0x03 = UDP ASSOCIATE
- ATYP: Address type
  - 0x01: IPv4 (4 bytes)
  - 0x03: Domain name (first byte is length, followed by domain string — NO null terminator)
  - 0x04: IPv6 (16 bytes)

### CONNECT Reply

[Priya's note: I need to look up the exact reply format. I think it mirrors
the request format but I'm not 100% sure about all the reply codes.]

The reply format is:
```
+----+-----+-------+------+----------+----------+
|VER | REP |  RSV  | ATYP | BND.ADDR | BND.PORT |
+----+-----+-------+------+----------+----------+
| 1  |  1  | X'00' |  1   | Variable |    2     |
+----+-----+-------+------+----------+----------+
```

Reply codes (REP field):
- 0x00: succeeded
- 0x01: general SOCKS server failure
- 0x02: connection not allowed by ruleset
- 0x03: Network unreachable
- 0x04: Host unreachable
- 0x05: Connection refused
- 0x07: Command not supported

### Data Relay
After successful CONNECT, all data sent by the client is forwarded to the
destination, and all data from the destination is forwarded to the client.
The SOCKS server acts as a transparent relay at this point.

### TODO
- Need to handle connection timeouts
- Need to handle concurrent connections properly
- IPv6 support needed for ATYP 0x04
"""
    with open("/app/docs/socks5_notes.md", "w") as f:
        f.write(notes)

def create_pcap():
    """Create a synthetic PCAP showing a working SOCKS5 session.
    Uses raw PCAP file format (no scapy dependency needed for generation).
    """

    def make_pcap_header():
        """PCAP global header."""
        return struct.pack('<IHHiIII',
            0xa1b2c3d4,  # magic number
            2, 4,         # version
            0,            # thiszone
            0,            # sigfigs
            65535,        # snaplen
            1             # network (LINKTYPE_ETHERNET)
        )

    def make_ethernet_header(src_mac, dst_mac, ethertype=0x0800):
        return dst_mac + src_mac + struct.pack('!H', ethertype)

    def make_ip_header(src_ip, dst_ip, total_length, protocol=6):
        """Minimal IPv4 header (no options)."""
        version_ihl = 0x45
        tos = 0
        identification = 0x1234
        flags_fragment = 0x4000  # Don't fragment
        ttl = 64
        # Checksum = 0 (not validated in our use case)
        header = struct.pack('!BBHHHBBH4s4s',
            version_ihl, tos, total_length,
            identification, flags_fragment,
            ttl, protocol, 0,
            socket.inet_aton(src_ip),
            socket.inet_aton(dst_ip)
        )
        return header

    def make_tcp_header(src_port, dst_port, seq, ack, flags, payload=b''):
        """Minimal TCP header (no options)."""
        data_offset = 5 << 4
        window = 65535
        checksum = 0
        urgent = 0
        header = struct.pack('!HHIIBBHHH',
            src_port, dst_port,
            seq, ack,
            data_offset, flags,
            window, checksum, urgent
        )
        return header

    def make_packet(ts_sec, ts_usec, src_mac, dst_mac, src_ip, dst_ip,
                    src_port, dst_port, seq, ack, tcp_flags, payload=b''):
        """Create a complete PCAP packet record."""
        tcp = make_tcp_header(src_port, dst_port, seq, ack, tcp_flags, payload)
        ip_total = 20 + len(tcp) + len(payload)
        ip = make_ip_header(src_ip, dst_ip, ip_total)
        eth = make_ethernet_header(src_mac, dst_mac)
        frame = eth + ip + tcp + payload
        # PCAP packet header
        pkt_header = struct.pack('<IIII', ts_sec, ts_usec, len(frame), len(frame))
        return pkt_header + frame

    client_mac = b'\x00\x11\x22\x33\x44\x55'
    server_mac = b'\x00\xaa\xbb\xcc\xdd\xee'
    client_ip = '192.168.1.100'
    server_ip = '192.168.1.1'
    client_port = 49152
    server_port = 1080

    packets = []
    ts = 1000000

    # Packet 1: Client greeting - propose methods 0x00 and 0x02
    # VER=0x05, NMETHODS=2, METHODS=[0x00, 0x02]
    greeting = bytes([0x05, 0x02, 0x00, 0x02])
    packets.append(make_packet(ts, 0, client_mac, server_mac,
        client_ip, server_ip, client_port, server_port,
        1000, 0, 0x18, greeting))

    # Packet 2: Server selects username/password (0x02)
    # VER=0x05, METHOD=0x02
    ts += 1
    method_sel = bytes([0x05, 0x02])
    packets.append(make_packet(ts, 0, server_mac, client_mac,
        server_ip, client_ip, server_port, client_port,
        2000, 1004, 0x18, method_sel))

    # Packet 3: Client sends username/password auth
    # VER=0x01, ULEN=5, UNAME=admin, PLEN=10, PASSWD=proxy_pass
    ts += 1
    username = b'admin'
    password = b'proxy_pass'
    auth_req = bytes([0x01, len(username)]) + username + bytes([len(password)]) + password
    packets.append(make_packet(ts, 0, client_mac, server_mac,
        client_ip, server_ip, client_port, server_port,
        1004, 2002, 0x18, auth_req))

    # Packet 4: Server auth success
    # VER=0x01, STATUS=0x00
    ts += 1
    auth_resp = bytes([0x01, 0x00])
    packets.append(make_packet(ts, 0, server_mac, client_mac,
        server_ip, client_ip, server_port, client_port,
        2002, 1004 + len(auth_req), 0x18, auth_resp))

    # Packet 5: Client CONNECT to domain example.com:80
    # VER=0x05, CMD=0x01, RSV=0x00, ATYP=0x03, domain
    ts += 1
    domain = b'example.com'
    connect_req = bytes([0x05, 0x01, 0x00, 0x03, len(domain)]) + domain + struct.pack('!H', 80)
    packets.append(make_packet(ts, 0, client_mac, server_mac,
        client_ip, server_ip, client_port, server_port,
        1004 + len(auth_req), 2004, 0x18, connect_req))

    # Packet 6: Server CONNECT reply - success with bound address
    # VER=0x05, REP=0x00, RSV=0x00, ATYP=0x01, BND.ADDR=0.0.0.0, BND.PORT=0
    ts += 1
    connect_resp = bytes([0x05, 0x00, 0x00, 0x01]) + socket.inet_aton('0.0.0.0') + struct.pack('!H', 0)
    packets.append(make_packet(ts, 0, server_mac, client_mac,
        server_ip, client_ip, server_port, client_port,
        2004, 1004 + len(auth_req) + len(connect_req), 0x18, connect_resp))

    # Packet 7: Client sends HTTP request through tunnel
    ts += 1
    http_req = b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n'
    packets.append(make_packet(ts, 0, client_mac, server_mac,
        client_ip, server_ip, client_port, server_port,
        1004 + len(auth_req) + len(connect_req), 2004 + len(connect_resp),
        0x18, http_req))

    # Write PCAP file
    pcap_data = make_pcap_header()
    for pkt in packets:
        pcap_data += pkt

    with open("/app/captures/working_session.pcap", "wb") as f:
        f.write(pcap_data)

def create_config_template():
    """Create the config file template."""
    template = """[server]
# Port for the SOCKS5 proxy to listen on
port = 1080
# Bind address
bind = 0.0.0.0

[auth]
# Username and password for SOCKS5 authentication
username = admin
password = proxy_pass

[logging]
# Log level: DEBUG, INFO, WARNING, ERROR
level = INFO
"""
    with open("/app/proxy.conf.template", "w") as f:
        f.write(template)

if __name__ == "__main__":
    create_directories()
    create_buggy_server()
    create_protocol_notes()
    create_pcap()
    create_config_template()
    print("Environment setup complete.")
