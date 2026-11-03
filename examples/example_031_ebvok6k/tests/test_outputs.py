"""
Tests for the SOCKS5 proxy server task.
Verifies protocol compliance, authentication, CONNECT command,
concurrent connections, and error handling.
"""

import socket
import struct
import threading
import time
import os
import configparser
from pathlib import Path


# --- Helpers ---

SOCKS_VERSION = 0x05
AUTH_USERPASS = 0x02
AUTH_VERSION = 0x01

ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04

CMD_CONNECT = 0x01
CMD_BIND = 0x02


def get_proxy_port():
    """Read the proxy port from the config file."""
    config = configparser.ConfigParser()
    config.read('/app/proxy.conf')
    return config.getint('server', 'port', fallback=1080)


def get_auth_credentials():
    """Read auth credentials from the config file."""
    config = configparser.ConfigParser()
    config.read('/app/proxy.conf')
    username = config.get('auth', 'username', fallback='admin')
    password = config.get('auth', 'password', fallback='proxy_pass')
    return username, password


def recvall(sock, n, timeout=5):
    """Receive exactly n bytes."""
    sock.settimeout(timeout)
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError(f"Connection closed, got {len(data)}/{n} bytes")
        data += chunk
    return data


def socks5_handshake(sock, username, password):
    """Perform full SOCKS5 handshake with username/password auth."""
    # Send greeting: VER=5, NMETHODS=1, METHODS=[0x02]
    sock.sendall(bytes([SOCKS_VERSION, 0x01, AUTH_USERPASS]))

    # Receive method selection
    resp = recvall(sock, 2)
    assert resp[0] == SOCKS_VERSION, f"Expected SOCKS5 version (0x05), got 0x{resp[0]:02x}"
    assert resp[1] == AUTH_USERPASS, f"Expected auth method 0x02, got 0x{resp[1]:02x}"

    # Send username/password auth (RFC 1929)
    auth = bytes([AUTH_VERSION, len(username)]) + username.encode() + \
           bytes([len(password)]) + password.encode()
    sock.sendall(auth)

    # Receive auth response
    auth_resp = recvall(sock, 2)
    assert auth_resp[0] == AUTH_VERSION, f"Expected auth version 0x01, got 0x{auth_resp[0]:02x}"
    assert auth_resp[1] == 0x00, f"Auth failed with status 0x{auth_resp[1]:02x}"


def socks5_connect_ipv4(sock, addr, port):
    """Send SOCKS5 CONNECT request for IPv4 address."""
    req = struct.pack('!BBBB', SOCKS_VERSION, CMD_CONNECT, 0x00, ATYP_IPV4)
    req += socket.inet_aton(addr)
    req += struct.pack('!H', port)
    sock.sendall(req)

    # Read reply header: VER(1) + REP(1) + RSV(1) + ATYP(1)
    reply_header = recvall(sock, 4)
    rep = reply_header[1]
    atyp = reply_header[3]

    # Read bound address based on ATYP
    if atyp == ATYP_IPV4:
        recvall(sock, 4)  # BND.ADDR
    elif atyp == ATYP_IPV6:
        recvall(sock, 16)
    elif atyp == ATYP_DOMAIN:
        dlen = recvall(sock, 1)[0]
        recvall(sock, dlen)

    recvall(sock, 2)  # BND.PORT

    return rep


def socks5_connect_domain(sock, domain, port):
    """Send SOCKS5 CONNECT request for domain name."""
    req = struct.pack('!BBBB', SOCKS_VERSION, CMD_CONNECT, 0x00, ATYP_DOMAIN)
    domain_bytes = domain.encode('utf-8')
    req += bytes([len(domain_bytes)]) + domain_bytes
    req += struct.pack('!H', port)
    sock.sendall(req)

    # Read reply header
    reply_header = recvall(sock, 4)
    rep = reply_header[1]
    atyp = reply_header[3]

    if atyp == ATYP_IPV4:
        recvall(sock, 4)
    elif atyp == ATYP_IPV6:
        recvall(sock, 16)
    elif atyp == ATYP_DOMAIN:
        dlen = recvall(sock, 1)[0]
        recvall(sock, dlen)

    recvall(sock, 2)  # BND.PORT

    return rep


def start_echo_server(port, ready_event=None):
    """Start a simple echo server for testing CONNECT relay."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.settimeout(15)
    server.bind(('127.0.0.1', port))
    server.listen(5)
    if ready_event:
        ready_event.set()

    def handle(conn):
        try:
            conn.settimeout(5)
            data = conn.recv(4096)
            if data:
                conn.sendall(data)
        except:
            pass
        finally:
            conn.close()

    try:
        while True:
            try:
                conn, _ = server.accept()
                t = threading.Thread(target=handle, args=(conn,))
                t.daemon = True
                t.start()
            except socket.timeout:
                break
    finally:
        server.close()


# --- Tests ---


def test_config_file_exists():
    """Test that /app/proxy.conf exists and has required sections."""
    conf_path = Path('/app/proxy.conf')
    assert conf_path.exists(), "/app/proxy.conf does not exist"

    config = configparser.ConfigParser()
    config.read(str(conf_path))

    assert config.has_section('server'), "proxy.conf missing [server] section"
    assert config.has_option('server', 'port'), "proxy.conf missing 'port' in [server]"
    assert config.has_section('auth'), "proxy.conf missing [auth] section"
    assert config.has_option('auth', 'username'), "proxy.conf missing 'username' in [auth]"
    assert config.has_option('auth', 'password'), "proxy.conf missing 'password' in [auth]"


def test_server_file_exists():
    """Test that /app/socks5_server.py exists and is valid Python."""
    server_path = Path('/app/socks5_server.py')
    assert server_path.exists(), "/app/socks5_server.py does not exist"

    code = server_path.read_text()
    # Verify it compiles without syntax errors
    compile(code, str(server_path), 'exec')


def test_server_listening():
    """Test that the SOCKS5 server is running and accepting connections."""
    port = get_proxy_port()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        assert result == 0, f"SOCKS5 server not listening on port {port}"
    finally:
        sock.close()


def test_socks5_handshake_and_auth():
    """Test SOCKS5 greeting and username/password authentication."""
    port = get_proxy_port()
    username, password = get_auth_credentials()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('127.0.0.1', port))

    try:
        socks5_handshake(sock, username, password)
    finally:
        sock.close()


def test_auth_failure_rejected():
    """Test that wrong credentials are rejected."""
    port = get_proxy_port()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('127.0.0.1', port))

    try:
        # Send greeting
        sock.sendall(bytes([SOCKS_VERSION, 0x01, AUTH_USERPASS]))
        resp = recvall(sock, 2)
        assert resp[0] == SOCKS_VERSION
        assert resp[1] == AUTH_USERPASS

        # Send wrong credentials
        wrong_user = b'wronguser'
        wrong_pass = b'wrongpass'
        auth = bytes([AUTH_VERSION, len(wrong_user)]) + wrong_user + \
               bytes([len(wrong_pass)]) + wrong_pass
        sock.sendall(auth)

        # Expect auth failure
        auth_resp = recvall(sock, 2)
        assert auth_resp[0] == AUTH_VERSION, f"Expected auth version 0x01, got 0x{auth_resp[0]:02x}"
        assert auth_resp[1] != 0x00, "Server accepted wrong credentials"
    finally:
        sock.close()


def test_connect_ipv4():
    """Test CONNECT command with IPv4 address type."""
    port = get_proxy_port()
    username, password = get_auth_credentials()
    echo_port = 19876

    # Start echo server
    ready = threading.Event()
    echo_thread = threading.Thread(target=start_echo_server, args=(echo_port, ready))
    echo_thread.daemon = True
    echo_thread.start()
    ready.wait(timeout=5)
    time.sleep(0.5)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect(('127.0.0.1', port))

    try:
        socks5_handshake(sock, username, password)
        rep = socks5_connect_ipv4(sock, '127.0.0.1', echo_port)
        assert rep == 0x00, f"CONNECT failed with reply code 0x{rep:02x}"

        # Test data relay
        test_data = b'Hello through SOCKS5 proxy!'
        sock.sendall(test_data)
        echoed = recvall(sock, len(test_data))
        assert echoed == test_data, f"Data relay failed: got {echoed!r}, expected {test_data!r}"
    finally:
        sock.close()


def test_connect_domain():
    """Test CONNECT command with domain name address type."""
    port = get_proxy_port()
    username, password = get_auth_credentials()
    echo_port = 19877

    # Start echo server
    ready = threading.Event()
    echo_thread = threading.Thread(target=start_echo_server, args=(echo_port, ready))
    echo_thread.daemon = True
    echo_thread.start()
    ready.wait(timeout=5)
    time.sleep(0.5)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect(('127.0.0.1', port))

    try:
        socks5_handshake(sock, username, password)
        rep = socks5_connect_domain(sock, 'localhost', echo_port)
        assert rep == 0x00, f"CONNECT to domain failed with reply code 0x{rep:02x}"

        # Test data relay
        test_data = b'Domain name CONNECT test data!'
        sock.sendall(test_data)
        echoed = recvall(sock, len(test_data))
        assert echoed == test_data, f"Data relay failed: got {echoed!r}"
    finally:
        sock.close()


def test_unsupported_command_reply():
    """Test that unsupported commands get proper error reply."""
    port = get_proxy_port()
    username, password = get_auth_credentials()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('127.0.0.1', port))

    try:
        socks5_handshake(sock, username, password)

        # Send BIND command (0x02) which should not be supported
        req = struct.pack('!BBBB', SOCKS_VERSION, CMD_BIND, 0x00, ATYP_IPV4)
        req += socket.inet_aton('127.0.0.1')
        req += struct.pack('!H', 80)
        sock.sendall(req)

        # Read reply - expect command not supported (0x07)
        reply_header = recvall(sock, 4)
        assert reply_header[0] == SOCKS_VERSION, \
            f"Expected SOCKS5 version in reply, got 0x{reply_header[0]:02x}"
        rep = reply_header[1]
        assert rep == 0x07, \
            f"Expected 'command not supported' (0x07), got 0x{rep:02x}"
    finally:
        sock.close()


def test_concurrent_connections():
    """Test that the server handles multiple simultaneous connections."""
    port = get_proxy_port()
    username, password = get_auth_credentials()
    base_echo_port = 19880
    num_connections = 5

    results = [None] * num_connections
    errors = [None] * num_connections

    # Start echo servers
    for i in range(num_connections):
        eport = base_echo_port + i
        ready = threading.Event()
        t = threading.Thread(target=start_echo_server, args=(eport, ready))
        t.daemon = True
        t.start()
        ready.wait(timeout=5)

    time.sleep(0.5)

    def connect_and_relay(idx):
        eport = base_echo_port + idx
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect(('127.0.0.1', port))
            socks5_handshake(sock, username, password)
            rep = socks5_connect_ipv4(sock, '127.0.0.1', eport)
            if rep != 0x00:
                errors[idx] = f"CONNECT failed: 0x{rep:02x}"
                sock.close()
                return

            test_data = f'concurrent-test-{idx}'.encode()
            sock.sendall(test_data)
            echoed = recvall(sock, len(test_data))
            if echoed == test_data:
                results[idx] = True
            else:
                errors[idx] = f"Echo mismatch: {echoed!r} != {test_data!r}"
            sock.close()
        except Exception as e:
            errors[idx] = str(e)

    threads = []
    for i in range(num_connections):
        t = threading.Thread(target=connect_and_relay, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=15)

    for i in range(num_connections):
        assert results[i] is True, \
            f"Connection {i} failed: {errors[i]}"


def test_connect_ipv6():
    """Test CONNECT command with IPv6 address type (::1 loopback)."""
    port = get_proxy_port()
    username, password = get_auth_credentials()
    echo_port = 19878

    # Check if IPv6 is available on this system
    try:
        test_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        test_sock.bind(('::1', 0))
        test_sock.close()
    except OSError:
        import pytest
        pytest.skip("IPv6 not available on this system")

    # Start IPv6 echo server
    def start_ipv6_echo_server(eport, ready_event):
        srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.settimeout(15)
        srv.bind(('::1', eport))
        srv.listen(5)
        ready_event.set()
        try:
            conn, _ = srv.accept()
            conn.settimeout(5)
            data = conn.recv(4096)
            if data:
                conn.sendall(data)
            conn.close()
        except:
            pass
        finally:
            srv.close()

    ready = threading.Event()
    echo_thread = threading.Thread(target=start_ipv6_echo_server, args=(echo_port, ready))
    echo_thread.daemon = True
    echo_thread.start()
    ready.wait(timeout=5)
    time.sleep(0.5)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect(('127.0.0.1', port))

    try:
        socks5_handshake(sock, username, password)

        # Send CONNECT with ATYP=0x04 (IPv6), address=::1
        req = struct.pack('!BBBB', SOCKS_VERSION, CMD_CONNECT, 0x00, ATYP_IPV6)
        req += socket.inet_pton(socket.AF_INET6, '::1')
        req += struct.pack('!H', echo_port)
        sock.sendall(req)

        # Read reply
        reply_header = recvall(sock, 4)
        rep = reply_header[1]
        atyp = reply_header[3]

        if atyp == ATYP_IPV4:
            recvall(sock, 4)
        elif atyp == ATYP_IPV6:
            recvall(sock, 16)
        recvall(sock, 2)  # BND.PORT

        assert rep == 0x00, f"CONNECT to IPv6 ::1 failed with reply code 0x{rep:02x}"

        # Test data relay
        test_data = b'IPv6 SOCKS5 tunnel test!'
        sock.sendall(test_data)
        echoed = recvall(sock, len(test_data))
        assert echoed == test_data, f"IPv6 data relay failed: got {echoed!r}"
    finally:
        sock.close()


def test_connect_refused_reply():
    """Test that connecting to a refused port returns proper SOCKS5 error."""
    port = get_proxy_port()
    username, password = get_auth_credentials()

    # Use a port that's definitely not listening
    dead_port = 19999

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect(('127.0.0.1', port))

    try:
        socks5_handshake(sock, username, password)
        rep = socks5_connect_ipv4(sock, '127.0.0.1', dead_port)
        # Should get connection refused (0x05) or general failure (0x01)
        assert rep in (0x01, 0x04, 0x05), \
            f"Expected error reply for refused connection, got 0x{rep:02x}"
    finally:
        sock.close()


def test_multiple_auth_methods_offered():
    """Test that server correctly selects auth method when client offers multiple."""
    port = get_proxy_port()
    username, password = get_auth_credentials()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('127.0.0.1', port))

    try:
        # Offer both NO_AUTH (0x00) and USERNAME/PASSWORD (0x02)
        sock.sendall(bytes([SOCKS_VERSION, 0x02, 0x00, AUTH_USERPASS]))

        resp = recvall(sock, 2)
        assert resp[0] == SOCKS_VERSION, f"Expected SOCKS5 version, got 0x{resp[0]:02x}"
        # Server should select username/password (0x02) since that's what we require
        assert resp[1] == AUTH_USERPASS, \
            f"Server should select username/password auth (0x02), got 0x{resp[1]:02x}"
    finally:
        sock.close()
