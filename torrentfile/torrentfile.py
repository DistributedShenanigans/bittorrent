import os
import hashlib
import requests
import bencodepy

from urllib.parse import urlparse, urlunparse, quote_from_bytes

from utils.encoding import decode_peers
from p2p.p2p import Torrent  # Core P2P download implementation

def parse_torrent(f):
    """Parse .torrent file into structured TorrentFile object."""
    data = f.read()
    decoded = bencodepy.decode(data)  # Decode Bencode format

    # Validate required fields
    if b'announce' not in decoded or b'info' not in decoded:
        raise ValueError("Missing required 'announce' or 'info' in torrent")

    announce = decoded[b'announce'].decode('utf-8')
    info = decoded[b'info']

    # Verify torrent info structure
    required_info = (b'pieces', b'piece length', b'length', b'name')
    for field in required_info:
        if field not in info:
            raise ValueError(f"Missing '{field.decode()}' in torrent info")

    # Extract core torrent metadata
    pieces = info[b'pieces']  # Concatenated SHA-1 hashes
    piece_length = info[b'piece length']
    length = info[b'length']
    name = info[b'name'].decode('utf-8')

    # Calculate torrent identifier (SHA-1 of bencoded info dict)
    info_bencoded = bencodepy.encode(info)
    info_hash = hashlib.sha1(info_bencoded).digest()

    # Split pieces into individual 20-byte hashes
    piece_hashes = [pieces[i:i+20] for i in range(0, len(pieces), 20)]

    return TorrentFile(
        announce=announce,
        info_hash=info_hash,
        piece_hashes=piece_hashes,
        piece_length=piece_length,
        total_length=length,
        name=name
    )

class TorrentFile:
    """Represents torrent metadata and handles tracker communication."""
    def __init__(self, announce: str, info_hash: bytes,
                 piece_hashes: list, piece_length: int,
                 total_length: int, name: str):
        self.announce = announce      # Tracker URL
        self.info_hash = info_hash    # Torrent identifier (20-byte SHA1)
        self.piece_hashes = piece_hashes  # List of piece hashes
        self.piece_length = piece_length  # Bytes per piece (except last)
        self.total_length = total_length  # Total file size in bytes
        self.name = name              # Recommended filename

    def build_tracker_url(self, peer_id: bytes, port: int) -> str:
        """Build tracker announce URL with proper URL encoding."""
        parsed = urlparse(self.announce)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid announce URL: {self.announce}")

        # Percent-encode binary parameters without double-escaping
        params = {
            "info_hash": quote_from_bytes(self.info_hash),
            "peer_id": quote_from_bytes(peer_id),
            "port": str(port),
            "uploaded": "0",
            "downloaded": "0",
            "compact": "1",  # Prefer compact peer list
            "left": str(self.total_length),
        }

        # Construct query string manually to preserve encoding
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return urlunparse(parsed._replace(query=query))

    def request_peers(self, peer_id: bytes, port: int, timeout: int = 15):
        """Fetch peer list from tracker using announce URL."""
        url = self.build_tracker_url(peer_id, port)
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()

        # Decode tracker's Bencoded response
        data = bencodepy.decode(resp.content)
        if b"peers" not in data:
            raise ValueError("Tracker response missing 'peers' field")

        return decode_peers(data[b"peers"])  # Parse compact/binary peer list

    def download_to_file(self, path: str, port: int = 6881):
        """Orchestrate full download process from peers to file."""
        # Generate random 20-byte peer ID
        peer_id = os.urandom(20)

        # Get initial peer list from tracker
        peers = self.request_peers(peer_id, port)

        # Initialize P2P download manager
        torrent = Torrent(
            peers=peers,
            peer_id=peer_id,
            info_hash=self.info_hash,
            piece_hashes=self.piece_hashes,
            piece_length=self.piece_length,
            total_length=self.total_length,
            name=self.name,
        )

        # Execute download and save results
        data = torrent.download()
        with open(path, "wb") as out:
            out.write(data)