class Bitfield:
    """BitTorrent bitfield implementation for tracking available pieces."""
    def __init__(self, num_pieces: int):
        """Initialize empty bitfield for given number of pieces."""
        # Each byte tracks 8 pieces, round up to nearest byte
        self.field = bytearray((num_pieces + 7) // 8)

    def has_piece(self, index: int) -> bool:
        """Check if piece at index is available (bit=1)."""
        byte_index = index // 8  # Which byte contains the bit
        offset = index % 8       # Bit position within byte (0=leftmost)
        # Shift mask to check correct bit (big-endian bit ordering)
        return (self.field[byte_index] >> (7 - offset)) & 1 == 1

    def set_piece(self, index: int):
        """Mark piece at index as available (set bit=1)."""
        byte_index = index // 8
        offset = index % 8
        # Set bit using OR mask (1 << (7 - offset))
        self.field[byte_index] |= 1 << (7 - offset)

    def serialize(self) -> bytes:
        """Convert to bytes for network transmission."""
        return bytes(self.field)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Bitfield':
        """Construct from received bitfield bytes."""
        # Create bitfield assuming 8 pieces per byte
        bf = cls(len(data) * 8)
        bf.field = bytearray(data)
        return bf