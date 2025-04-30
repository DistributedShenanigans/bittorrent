import threading
import queue
import hashlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor  # Added import
from msg.message import MessageID, Message
from leech.leech import Leech

MAX_BLOCK_SIZE = 16384  # 16KB block size
MAX_BACKLOG = 5  # Max pipelined requests


class PieceWork:
    """Metadata for a piece download job"""

    def __init__(self, index: int, expected_hash: bytes, length: int):
        self.index = index  # Piece index
        self.hash = expected_hash  # SHA1 hash
        self.length = length  # Piece length in bytes


class PieceResult:
    """Container for downloaded piece data"""

    def __init__(self, index: int, buf: bytes):
        self.index = index  # Piece index
        self.buf = buf  # Raw binary data


class Torrent:
    """Main torrent download controller"""

    def __init__(self, peers: list, peer_id: bytes, info_hash: bytes,
                 piece_hashes: list, piece_length: int,
                 total_length: int, name: str):
        # Torrent metadata
        self.peers = peers
        self.peer_id = peer_id
        self.info_hash = info_hash
        self.piece_hashes = piece_hashes
        self.piece_length = piece_length
        self.total_length = total_length
        self.name = name

        # Download state
        self.connected_peers = set()  # Currently connected peers
        self.announced_peers = set()  # Peers that have been UI-announced
        self.done_pieces = 0  # Completed piece count
        self.downloaded_bytes = 0  # Total bytes downloaded
        self.download_start_time = time.time()
        self.peers_lock = threading.Lock()  # Shared state lock

    # Piece Calculations
    def calculate_bounds_for_piece(self, index: int) -> tuple:
        """Get byte range for piece index"""
        begin = index * self.piece_length
        end = min(begin + self.piece_length, self.total_length)
        return begin, end

    def calculate_piece_size(self, index: int) -> int:
        """Calculate actual piece size (last piece may be smaller)"""
        begin, end = self.calculate_bounds_for_piece(index)
        return end - begin

    # Core Download Logic
    def check_integrity(self, pw: PieceWork, buf: bytes):
        """Validate piece against its SHA1 hash"""
        digest = hashlib.sha1(buf).digest()
        if digest != pw.hash:
            raise ValueError(f"Piece {pw.index} failed integrity check")

    def attempt_download_piece(self, client: Leech, pw: PieceWork) -> bytes:
        """Download and validate a single piece"""
        buf = bytearray(pw.length)
        downloaded = requested = backlog = 0

        client.sock.settimeout(30)
        try:
            while downloaded < pw.length:
                # Pipeline requests when unchoked
                if not client.choked:
                    while backlog < MAX_BACKLOG and requested < pw.length:
                        block = min(MAX_BLOCK_SIZE, pw.length - requested)
                        client.send_request(pw.index, requested, block)
                        backlog += 1
                        requested += block

                # Process incoming messages
                msg: Message = client.read()
                if not msg: continue

                # Update client state
                if msg.id == MessageID.UNCHOKE:
                    client.choked = False
                elif msg.id == MessageID.CHOKE:
                    client.choked = True
                elif msg.id == MessageID.HAVE:
                    client.bitfield.set_piece(msg.parse_have())
                elif msg.id == MessageID.PIECE:
                    n = msg.parse_piece(pw.index, buf)
                    downloaded += n
                    backlog -= 1
                    with self.peers_lock:
                        self.downloaded_bytes += n

            return bytes(buf)
        finally:
            client.sock.settimeout(None)

    # Worker Management
    def start_download_worker(self, peer, work_queue: queue.Queue, results: queue.Queue):
        """Thread worker for peer communication"""
        try:
            ip, port = peer
            client = Leech(ip, port, self.info_hash, self.peer_id)

            try:
                client.connect()
                with self.peers_lock:
                    self.connected_peers.add((ip, port))
            except:
                return

            # Begin piece requests
            client.send_unchoke()
            client.send_interested()

            while True:
                try:
                    pw = work_queue.get(block=False)

                    if not client.bitfield.has_piece(pw.index):
                        work_queue.put(pw)  # Requeue if peer doesn't have piece
                        continue

                    data = self.attempt_download_piece(client, pw)
                    self.check_integrity(pw, data)
                    results.put(PieceResult(pw.index, data))

                except Exception as e:
                    work_queue.put(pw)
                    return

        except queue.Empty:
            return
        finally:
            with self.peers_lock:
                self.connected_peers.discard(peer)
            client.close()

    # Main Download Flow
    def download(self) -> bytes:
        """Orchestrate full download process"""
        print(f"Starting download: {self.name}")
        work_queue = queue.Queue()
        results = queue.Queue()

        # Initialize work queue with all pieces
        for idx, h in enumerate(self.piece_hashes):
            size = self.calculate_piece_size(idx)
            work_queue.put(PieceWork(idx, h, size))

        # Start peer worker threads using ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=len(self.peers))  # Create executor
        futures = []
        for peer in self.peers:
            future = executor.submit(
                self.start_download_worker,
                peer,
                work_queue,
                results
            )
            futures.append(future)

        # Start UI updater
        stop_event = threading.Event()
        ui_thread = threading.Thread(
            target=self._update_ui,
            args=(stop_event, len(self.piece_hashes))
        )
        ui_thread.daemon = True
        ui_thread.start()

        # Assemble final file
        buffer = bytearray(self.total_length)
        while self.done_pieces < len(self.piece_hashes):
            res = results.get()
            begin, end = self.calculate_bounds_for_piece(res.index)
            buffer[begin:end] = res.buf
            self.done_pieces += 1

        stop_event.set()
        ui_thread.join()
        executor.shutdown(wait=True)
        print("\nDownload complete!")
        return bytes(buffer)

    # UI Rendering
    def _update_ui(self, stop_event, total_pieces):
        """Terminal UI updater (runs in separate thread)"""
        while not stop_event.is_set():
            with self.peers_lock:
                current_peers = set(self.connected_peers)
                new_peers = current_peers - self.announced_peers
                active_peers = self.announced_peers.copy()
                self.announced_peers.update(new_peers)

            # Calculate metrics
            progress = self.done_pieces / total_pieces
            elapsed = time.time() - self.download_start_time
            speed = self.downloaded_bytes / (elapsed + 1e-6) / 1024  # KB/s

            # Build display components
            output = [
                f"Downloading: {self.name}",
                self._render_progress_bar(progress),
                f"Progress: {progress * 100:.2f}% ({self.done_pieces}/{total_pieces})",
                f"Speed: {speed:.2f} KB/s  Elapsed: {elapsed:.1f}s"
            ]

            if new_peers:
                output.append("\n🌐 New peers:")
                output.extend(f"   🟢 {ip}:{port}" for ip, port in sorted(new_peers))

            output.append(f"\n🔗 Active peers ({len(active_peers)}):")
            output.extend(f"   ● {ip}:{port}" for ip, port in sorted(active_peers)) \
                if active_peers else output.append("   (None)")

            # Terminal update
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write("\n".join(output))
            sys.stdout.flush()
            time.sleep(3)

    def _render_progress_bar(self, pct: float, width: int = 40) -> str:
        """Visual progress bar with emoji blocks"""
        filled = int(pct * width)
        return f"|{'🟩' * filled}{'🟦' * (width - filled)}| {pct * 100:.2f}%"