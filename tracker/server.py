from fastapi import FastAPI, Request
from .models import AnnounceRequest, TrackerResponse, PeerInfo
from typing import Dict, Set, Tuple

app = FastAPI()
# In-memory store: info_hash -> set of (ip, port)
peers_db: Dict[bytes, Set[Tuple[str, int]]] = {}


@app.post("/announce", response_model=TrackerResponse)
def announce(request: Request, req: AnnounceRequest):
    """
    Handle announce requests from peers: add/remove peer to the swarm, return list.
    """
    info_hash = req.info_hash
    peer_ip = request.client.host
    peer_tuple = (peer_ip, req.port)

    swarm = peers_db.setdefault(info_hash, set())
    if req.event in ("started", "completed"):
        swarm.add(peer_tuple)
    elif req.event == "stopped":
        swarm.discard(peer_tuple)

    peers_list = [PeerInfo(ip=ip, port=port) for ip, port in list(swarm)[:50]]
    return TrackerResponse(interval=1800, peers=peers_list)


@app.get("/health")
def health_check():
    return {"status": "ok"}
