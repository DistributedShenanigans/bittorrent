import hashlib

def sha1(data: bytes) -> bytes:
    return hashlib.sha1(data).digest()

def sha1_hex(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()