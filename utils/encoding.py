import socket
import struct
from typing import List, Set, Tuple


def encode_peers(peers: Set[Tuple[str, int]]) -> bytes:
    """Convert (IP, port) tuples to compact binary format (BEP 7)."""
    return b"".join(
        # IPv4 to 4 bytes + port as 2 big-endian bytes
        socket.inet_aton(ip) + struct.pack(">H", port)
        for ip, port in peers
    )


def decode_peers(blob: bytes) -> List[Tuple[str, int]]:
    """Parse compact peer list (6 bytes per peer) to (IP, port) tuples."""
    peers = []
    # Process 6-byte chunks: 4 bytes IP, 2 bytes port
    for i in range(0, len(blob), 6):
        ip_bytes = blob[i:i + 4]
        port_bytes = blob[i + 4:i + 6]

        # Convert 4-byte network format to IPv4 string
        ip = socket.inet_ntoa(ip_bytes)
        # Unpack port as unsigned short (big-endian)
        port = struct.unpack(">H", port_bytes)[0]

        peers.append((ip, port))
    return peers