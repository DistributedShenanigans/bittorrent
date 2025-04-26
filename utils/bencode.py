import bencodepy

class BencodeError(ValueError):
    """Custom exception for Bencode encoding/decoding errors."""
    pass


def encode(obj):
    """
    Bencode-encode a Python object using bencodepy.
    Accepts int, bytes/bytearray, list, dict; for str, encodes to UTF-8 bytes.
    Raises BencodeError on failure.
    """
    try:
        if isinstance(obj, str):
            obj = obj.encode()
        return bencodepy.encode(obj)
    except Exception as e:
        raise BencodeError(f"Failed to bencode object {obj!r}: {e}")


def _convert(obj):
    """Recursively convert OrderedDict to dict and decode bytes keys to str."""
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            # Convert key to str if bytes
            if isinstance(k, bytes):
                try:
                    k2 = k.decode()
                except Exception:
                    k2 = k
            else:
                k2 = k
            new[k2] = _convert(v)
        return new
    elif isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    else:
        return obj


def decode(data: bytes):
    """
    Decode Bencoded bytes into Python objects using bencodepy.
    Raises BencodeError on failure.
    """
    try:
        res = bencodepy.decode(data)
    except Exception as e:
        raise BencodeError(f"Failed to decode bencoded data: {e}")

    # Unwrap single-element tuple
    if isinstance(res, tuple) and len(res) == 1:
        res = res[0]

    # Convert OrderedDicts and bytes keys
    return _convert(res)
