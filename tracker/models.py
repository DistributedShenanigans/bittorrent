from pydantic import BaseModel, Field
from typing import List, Literal


class AnnounceRequest(BaseModel):
    info_hash: bytes = Field(..., min_length=20, max_length=20, description="20-byte SHA1 info hash")
    peer_id: str = Field(..., min_length=20, max_length=20, description="Peer identifier")
    port: int = Field(..., ge=1, le=65535)
    uploaded: int = Field(..., ge=0)
    downloaded: int = Field(..., ge=0)
    left: int = Field(..., ge=0)
    event: Literal["started", "stopped", "completed"] = "started"


class PeerInfo(BaseModel):
    ip: str
    port: int


class TrackerResponse(BaseModel):
    interval: int = Field(..., description="Reconnect interval in seconds")
    peers: List[PeerInfo]

