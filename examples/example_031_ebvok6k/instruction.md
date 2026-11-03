Your colleague Priya was building a SOCKS5 proxy server for the team's internal development environment. The proxy is needed so developers can tunnel their test traffic through a controlled gateway that enforces authentication. Priya had to leave suddenly for a family emergency halfway through the implementation, and the project deadline is tomorrow morning.

She left behind a partially-written Python server at `/app/socks5_server.py`, a protocol reference document at `/app/docs/socks5_notes.md`, and a packet capture at `/app/captures/working_session.pcap` from an earlier prototype that was working correctly. She also left a configuration file template at `/app/proxy.conf.template`.

You've tried running her code, but it's broken in several ways. The handshake negotiation doesn't work correctly — clients can't even get past the initial greeting. From what you can tell, there are bugs in how she handles the authentication method selection, and the CONNECT command handler is incomplete. She started writing support for domain-name resolution in CONNECT requests but never finished it. The IPv6 address handling is also missing entirely.

Here's what the proxy needs to do:

The server must implement the SOCKS5 protocol as defined in RFC 1928, with username/password authentication per RFC 1929. It needs to listen on the port specified in `/app/proxy.conf` (which you'll need to create from the template). The server must handle multiple simultaneous client connections using either threading or async I/O.

Specifically, the server must support:
- The SOCKS5 initial handshake where the client proposes authentication methods and the server selects one
- Username/password authentication (method `0x02`) — the valid credentials should be read from `/app/proxy.conf`
- The CONNECT command (`0x01`) for all three address types: IPv4 (`0x01`), domain name (`0x03`), and IPv6 (`0x04`)
- Proper error replies with correct SOCKS5 reply codes when things go wrong (connection refused, host unreachable, command not supported, etc.)
- Bidirectional data relay after a successful CONNECT

You can use Priya's packet capture to understand the exact byte-level protocol flow if her notes are incomplete. The capture shows a full working session including handshake, authentication, a CONNECT request to a domain name, and data transfer.

When you're done, the working server should be at `/app/socks5_server.py`, the configuration at `/app/proxy.conf`, and the server must be running in the background on the port specified in the config. Make sure the server stays running after your script exits.

Tools available in the environment: Python 3.11, tcpdump, tshark, netcat, curl. The `scapy` and `dpkt` Python libraries are installed for PCAP analysis.
