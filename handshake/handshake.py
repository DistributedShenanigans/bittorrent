import struct
import socket

# Protocol constants
BT_PROTOCOL = b"BitTorrent protocol"
BT_PSTRLEN = len(BT_PROTOCOL)  # Always 19 bytes
RESERVED = b"\x00" * 8  # 8-byte reserved field


class Handshake:
    """BitTorrent protocol handshake handler (v1.0)"""

    def __init__(self, info_hash: bytes, peer_id: bytes):
        if len(info_hash) != 20 or len(peer_id) != 20:
            raise ValueError("info_hash and peer_id must each be exactly 20 bytes")
        self.pstr = BT_PROTOCOL
        self.info_hash = info_hash  # 20-byte SHA1 hash
        self.peer_id = peer_id  # 20-byte client ID

    def serialize(self) -> bytes:
        """Pack handshake into 68-byte binary format"""
        # Format: [1B: pstrlen][19B: pstr][8B: reserved][20B: info_hash][20B: peer_id]
        fmt = f">B{BT_PSTRLEN}s8s20s20s"
        return struct.pack(
            fmt,
            BT_PSTRLEN,
            self.pstr,
            RESERVED,
            self.info_hash,
            self.peer_id
        )

    @classmethod
    def read_from(cls, sock: socket.socket, timeout: float = 5.0) -> "Handshake":
        """Read and validate handshake from socket"""
        sock.settimeout(timeout)

        # Read protocol header
        header = sock.recv(1)
        if not header:
            raise ConnectionError("Connection closed before handshake")

        # Parse protocol length
        (pstrlen,) = struct.unpack(">B", header)

        # Read remaining handshake data
        to_read = pstrlen + 8 + 20 + 20  # pstr + reserved + info_hash + peer_id
        data = b""
        while len(data) < to_read:
            chunk = sock.recv(to_read - len(data))
            if not chunk:
                raise ConnectionError("Connection closed during handshake")
            data += chunk

        # Unpack and validate components
        fmt = f">{pstrlen}s8s20s20s"
        pstr, reserved, info_hash, peer_id = struct.unpack(fmt, data)

        if pstr != BT_PROTOCOL:
            raise ValueError(f"Invalid protocol: {pstr!r}")

        return cls(info_hash=info_hash, peer_id=peer_id)