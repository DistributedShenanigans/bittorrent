import uvicorn
import bencodepy  # For Bencoded tracker responses

from fastapi import FastAPI, Request, Response, Query
from typing import Dict, Set, Tuple
from urllib.parse import unquote_to_bytes

from utils.encoding import encode_peers  # Peer list serialization

app = FastAPI()

# In-memory peer storage: {info_hash: {(ip, port)}}
peers_db: Dict[bytes, Set[Tuple[str, int]]] = {}


@app.get("/announce")
def announce(
        request: Request,
        info_hash: str = Query(..., description="Percent-encoded 20-byte torrent ID"),
        peer_id: str = Query(..., description="Client's self-identifier (unused)"),
        port: int = Query(..., description="Peer's listening port"),
        uploaded: int = Query(0, description="Bytes uploaded (stats)"),
        downloaded: int = Query(0, description="Bytes downloaded (stats)"),
        left: int = Query(0, description="Bytes remaining to download"),
        compact: int = Query(1, description="Require compact peer format"),
        event: str | None = Query(None, description="started/stopped/completed"),
):
    """BitTorrent tracker endpoint (BEP 3/23) for peer coordination."""
    # Decode URL-safe parameters to bytes
    ih = unquote_to_bytes(info_hash)

    # Get peer connection details
    peer_ip = request.client.host  # Extract client IP from request
    peer_tuple = (peer_ip, port)

    # Update peer swarm state
    swarm = peers_db.setdefault(ih, set())
    if event == "stopped":
        swarm.discard(peer_tuple)  # Remove departing peer
    else:
        swarm.add(peer_tuple)  # Add/refresh peer presence

    # Prepare peer list excluding self (BEP 7 compact format)
    response_peers = swarm - {peer_tuple}

    # Build Bencoded response with 30min interval
    body = bencodepy.encode({
        b"interval": 1800,  # 30min re-announce interval
        b"peers": encode_peers(response_peers)  # Compact peer list
    })

    return Response(content=body, media_type="application/octet-stream")


@app.get("/health")
def health_check():
    """Liveness probe endpoint for infrastructure monitoring."""
    return {"status": "ok"}


if __name__ == "__main__":
    # Start production-grade ASGI server
    uvicorn.run("tracker.server:app",
                host="0.0.0.0",  # Bind to all interfaces
                port=8080  # Standard alt HTTP port
                )