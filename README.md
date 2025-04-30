# 💾 Peer-to-Peer File Sharing with BitTorrent

Implement a simplified BitTorrent-style file sharing protocol. Each peer stores and exchanges file chunks.

## Validation Checklist:
- [x] Upload a file and download it completely using chunk exchange
- [x] Log peer join/leave and chunk ownership updates
- [x] Visualize download progress per peer

## BitTorrent Architecture 

![BitTorrent Architecture](/assets/arch.png)

## Running the System

### 1. Start the Tracker

```bash
python3.12 -m tracker.server
```
This starts the tracker on port 8080.

Check it's running with:

```bash
curl http://localhost:8080/health
# → {"status": "ok"}
```

###  2. Start the Seeder(s)

```bash
python3.12 -m seed.seed \
  -t path/to/your-file.torrent \
  -p 6881
```

This will:
- Parse the .torrent
- Announce to the tracker
- Serve pieces to requesting peers

### 3. Run the Client

To download the file using the BitTorrent client:
```bash
python3.12 -m client.main \
  -t path/to/your-file.torrent \
  -o path/to/output-file \
  -p 6889
```

- `-t` – path to the .torrent file
- `-o` – where to save the downloaded file (optional)
- `-p` – port to announce to tracker (should differ from seeder)

## Project Structure

```bash
bittorrent/
├── handshake/
│   └── handshake.py         # Peer-to-peer handshake logic
├── leech/
│   └── leech.py             # Leech (downloading peer) implementation
├── msg/
│   └── message.py           # BitTorrent message definitions and handling
├── p2p/
│   └── p2p.py               # Core integration of P2P logic
├── seed/
│   └── seed.py              # Seeder (uploading peer) implementation
├── torrentfile/
│   └── torrentfile.py       # .torrent parsing and file download helpers
├── tracker/
│   ├── server.py            # FastAPI tracker server (announce endpoint)
│   └── models.py            # Data models for requests and peer info
├── utils/
│   ├── bitfield.py          # Efficient bitfield structure for piece availability
│   └── encoding.py          # Peer host/port serialization (compact format)
└── main.py                  # Project entry point (CLI or orchestrator)
```

## References
- [The BitTorrent Protocol Specification](https://www.bittorrent.org/beps/bep_0003.html)
- [Building a BitTorrent client from the ground up](https://blog.jse.li/posts/torrent/)