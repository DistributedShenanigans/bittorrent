import argparse
import os
import requests
import socket
import struct
import threading
import signal

from pathlib import Path
from handshake.handshake import Handshake
from msg.message import Message, MessageID
from torrentfile.torrentfile import parse_torrent, TorrentFile
from utils.bitfield import Bitfield

PEER_ID_SIZE = 20  # Standard BitTorrent peer ID length


class Seed:
    """Server for sharing complete torrent files with peers."""

    def __init__(self, host: str, port: int, peer_id: bytes, tf: TorrentFile, file_path: str):
        self.host = host  # Binding interface (typically 0.0.0.0)
        self.port = port  # Listening port
        self.peer_id = peer_id  # 20-byte unique identifier
        self.tf = tf  # Parsed torrent metadata
        self.file_path = file_path  # Path to shared file
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._stop = threading.Event()  # Graceful shutdown flag

    def start(self):
        """Start seeding server and handle incoming peer connections."""
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"[seeder] listening on {self.host}:{self.port}")

        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        # Main accept loop
        while not self._stop.is_set():
            try:
                conn, addr = self.server.accept()
                threading.Thread(target=self.handle, args=(conn,), daemon=True).start()
            except OSError:
                break  # Socket closed during shutdown

        print("[seeder] shutting down")

    def _shutdown(self, *_):
        """Trigger graceful shutdown of the seeder."""
        print("[seeder] received shutdown, stopping...")
        self._stop.set()
        self.server.close()

    def handle(self, conn: socket.socket):
        """Handle peer connection lifecycle: handshake, seeding, requests."""
        try:
            # Validate peer handshake
            client_hs = Handshake.read_from(conn)
            if client_hs.info_hash != self.tf.info_hash:
                return

            # Complete handshake
            conn.sendall(Handshake(self.tf.info_hash, self.peer_id).serialize())

            # Announce full availability
            bf = Bitfield(len(self.tf.piece_hashes))
            bf.set_all()  # Mark all pieces as available
            conn.sendall(Message(MessageID.BITFIELD, bf.serialize()).serialize())

            # Process peer requests
            while True:
                msg = Message.read_from(conn)
                if not msg:
                    continue  # Ignore keep-alives

                if msg.id == MessageID.REQUEST:
                    # Extract request parameters
                    idx, offset, length = struct.unpack(">III", msg.payload)

                    # Read requested block from file
                    with open(self.file_path, "rb") as f:
                        start_pos = idx * self.tf.piece_length + offset
                        f.seek(start_pos)
                        block_data = f.read(length)

                    # Send PIECE response
                    response = struct.pack(">II", idx, offset) + block_data
                    conn.sendall(Message(MessageID.PIECE, response).serialize())

        except (ConnectionError, EOFError):
            pass  # Peer disconnected normally
        finally:
            conn.close()


def main():
    """Command-line interface for torrent seeder."""
    parser = argparse.ArgumentParser(description="Simple Python BitTorrent Seeder")
    parser.add_argument("-t", "--torrent", help=".torrent file to seed")
    parser.add_argument("-p", "--port", type=int, default=6881, help="TCP port to listen on")
    args = parser.parse_args()

    # Load torrent metadata
    tf_path = Path(args.torrent)
    with tf_path.open("rb") as f:
        tf = parse_torrent(f)

    # Generate random peer ID
    peer_id = os.urandom(PEER_ID_SIZE)
    print(f"[seeder] using peer_id {peer_id.hex()}")

    # Announce to tracker
    tracker_url = tf.build_tracker_url(peer_id, args.port)
    try:
        requests.get(f"{tracker_url}&event=started", timeout=15)
        print("[seeder] announced to tracker, now serving peers")
    except requests.RequestException as e:
        print(f"[seeder] tracker announcement failed: {e}")

    # Start seeding server
    seed = Seed(
        host="0.0.0.0",
        port=args.port,
        peer_id=peer_id,
        tf=tf,
        file_path=tf_path.with_suffix("").name  # Assume torrent name matches file
    )
    seed.start()

    # Final tracker update on shutdown
    try:
        requests.get(f"{tracker_url}&event=stopped", timeout=5)
    except requests.RequestException:
        pass


if __name__ == "__main__":
    main()