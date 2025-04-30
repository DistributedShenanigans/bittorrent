import struct
import socket


class MessageID:
    """BitTorrent protocol message type identifiers."""
    (CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED,
     HAVE, BITFIELD, REQUEST, PIECE, CANCEL) = range(9)


class Message:
    """BitTorrent protocol message serialization/deserialization."""

    def __init__(self, msg_id: int, payload: bytes = b""):
        self.id = msg_id  # Message type from MessageID
        self.payload = payload  # Message-specific data

    def serialize(self) -> bytes:
        """Convert message to wire format: [4-byte length][id][payload]."""
        length = len(self.payload) + 1  # +1 for message ID byte
        return struct.pack(">I B", length, self.id) + self.payload

    @classmethod
    def read_from(cls, sock: socket.socket) -> "Message":
        """Read message from socket stream."""
        # Read length prefix (4 bytes big-endian)
        header = sock.recv(4)
        if len(header) < 4:
            raise ConnectionError("Failed to read length prefix")
        (length,) = struct.unpack(">I", header)

        if length == 0:
            return None  # Keep-alive message

        # Read message body
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                raise ConnectionError("Stream ended prematurely")
            data += chunk

        return cls(data[0], data[1:])  # First byte is message ID

    # Message Factories
    @classmethod
    def format_request(cls, index: int, begin: int, length: int) -> "Message":
        """Create REQUEST message for block (index, begin offset, length)."""
        payload = struct.pack(">III", index, begin, length)
        return cls(MessageID.REQUEST, payload)

    @classmethod
    def format_have(cls, index: int) -> "Message":
        """Create HAVE message to announce piece availability."""
        payload = struct.pack(">I", index)
        return cls(MessageID.HAVE, payload)

    # Message Parsers
    def parse_piece(self, expected_index: int, buf: bytearray) -> int:
        """Extract PIECE data into buffer. Returns bytes written."""
        if self.id != MessageID.PIECE:
            raise ValueError(f"Expected PIECE (id={MessageID.PIECE}), got {self.id}")
        if len(self.payload) < 8:
            raise ValueError("PIECE payload too short")

        # Unpack piece index and block offset
        idx, begin = struct.unpack(">II", self.payload[:8])
        if idx != expected_index:
            raise ValueError(f"PIECE index mismatch: expected {expected_index}, got {idx}")

        # Write data to buffer
        block = self.payload[8:]
        end = begin + len(block)
        if end > len(buf):
            raise ValueError("PIECE block overruns buffer")
        buf[begin:end] = block
        return len(block)

    def parse_have(self) -> int:
        """Extract piece index from HAVE message."""
        if self.id != MessageID.HAVE:
            raise ValueError(f"Expected HAVE (id={MessageID.HAVE}), got {self.id}")
        if len(self.payload) != 4:
            raise ValueError("HAVE payload length != 4")
        return struct.unpack(">I", self.payload)[0]

    # Debug Utilities
    def name(self) -> str:
        """Get human-readable message name."""
        names = {
            MessageID.CHOKE: "Choke",
            MessageID.UNCHOKE: "Unchoke",
            MessageID.INTERESTED: "Interested",
            MessageID.NOT_INTERESTED: "NotInterested",
            MessageID.HAVE: "Have",
            MessageID.BITFIELD: "Bitfield",
            MessageID.REQUEST: "Request",
            MessageID.PIECE: "Piece",
            MessageID.CANCEL: "Cancel",
        }
        return names.get(self.id, f"Unknown#{self.id}")

    def __str__(self) -> str:
        """Human-readable message representation."""
        if self is None:
            return "KeepAlive"
        return f"{self.name()} [{len(self.payload)} bytes]"