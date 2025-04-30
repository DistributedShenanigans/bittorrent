from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Tuple
from urllib.parse import unquote_to_bytes


class AnnounceRequest(BaseModel):
    """BitTorrent tracker announce parameters (BEP 3/23)."""
    info_hash: bytes
    peer_id:   bytes
    port:      int
    uploaded:   Optional[int] = 0
    downloaded: Optional[int] = 0
    left:       Optional[int] = 0
    event:     Optional[str] = None


class TrackerResponse(BaseModel):
    """BitTorrent tracker response format (BEP 3)."""
    interval: int = Field(..., description="Seconds to wait between announces")
    peers: bytes = Field(..., description="Compact peer list")