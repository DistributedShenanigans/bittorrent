import socket
import struct

from handshake.handshake import Handshake
from msg.message import Message, MessageID
from utils.bitfield import Bitfield


class Leech:
    def __init__(self, peer_ip, peer_port, info_hash, peer_id, timeout=10):
        """Initialize a peer connection for downloading torrent data."""
        self.peer = (peer_ip, peer_port)  # Peer's IP address and port
        self.info_hash = info_hash  # 20-byte torrent identifier
        self.peer_id = peer_id  # 20-byte client identifier
        self.timeout = timeout  # Connection timeout in seconds
        self.sock: socket.socket = None  # TCP connection socket
        self.choked = True  # Choke state (peer-controlled)
        self.bitfield = None  # Peer's available pieces

    def connect(self):
        """Establish connection and complete BitTorrent handshake protocol."""
        # TCP connection setup and handshake exchange
        self.sock = socket.create_connection(self.peer, timeout=self.timeout)
        req = Handshake(self.info_hash, self.peer_id)
        self.sock.sendall(req.serialize())

        # Verify handshake response
        try:
            resp = Handshake.read_from(self.sock, timeout=self.timeout)
        except:
            return

        if resp.info_hash != self.info_hash:
            self.sock.close()
            raise ValueError("InfoHash mismatch")

        # Process initial bitfield message
        raw = self._recv_raw_message()
        if raw is None or raw.id != MessageID.BITFIELD:
            raise ValueError("Expected initial BITFIELD")
        self.bitfield = Bitfield.from_bytes(raw.payload)

        # Remove timeout after successful handshake
        self.sock.settimeout(None)

    def _recv_raw_message(self):
        """Read raw message structure from socket (4-byte length prefix)."""
        header = self._recvall(4)  # Read message length
        length = struct.unpack(">I", header)[0]

        if length == 0:
            return None  # Keep-alive message

        data = self._recvall(length)  # Read message body
        msg_id = data[0]  # First byte is message type
        payload = data[1:]  # Remaining bytes are message content
        return Message(msg_id, payload)

    def _recvall(self, n):
        """Read exactly n bytes from socket."""
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise EOFError("Socket closed")
            buf += chunk
        return buf

    def read(self) -> Message:
        """Read and process incoming peer messages."""
        msg = self._recv_raw_message()
        if msg and msg.id == MessageID.HAVE:
            # Update bitfield when peer announces new piece
            idx = msg.parse_have()
            self.bitfield.set_piece(idx)
        return msg

    # Peer message command interface
    def send_choke(self):
        """Inform peer we're choking them (stop upload)."""
        self._send_message(MessageID.CHOKE)

    def send_unchoke(self):
        """Inform peer we're unchoking them (allow upload)."""
        self._send_message(MessageID.UNCHOKE)

    def send_interested(self):
        """Signal interest in receiving data from peer."""
        self._send_message(MessageID.INTERESTED)

    def send_not_interested(self):
        """Signal lack of interest in peer's data."""
        self._send_message(MessageID.NOT_INTERESTED)

    def send_have(self, index: int):
        """Announce possession of a new piece to peer."""
        msg = Message.format_have(index)
        self.sock.sendall(msg.serialize())

    def send_request(self, index: int, begin: int, length: int):
        """Request block of data from peer (piece index, offset, length)."""
        msg = Message.format_request(index, begin, length)
        self.sock.sendall(msg.serialize())

    def _send_message(self, msg_id: int, payload: bytes = b""):
        """Low-level message sending with protocol framing."""
        length = 1 + len(payload)  # ID byte + payload length
        header = struct.pack(">I", length) + bytes([msg_id])
        try:
            self.sock.sendall(header + payload)
        except BrokenPipeError:
            return  # Silently handle closed connections

    def close(self):
        """Cleanly shutdown connection to peer."""
        if self.sock:
            self.sock.close()
            self.sock = None