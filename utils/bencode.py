import typing


def encode(obj: typing.Any) -> bytes:
    """
    Bencode-encode a Python object: int, bytes/str, list, dict.
    """
    if isinstance(obj, int):
        return b'i' + str(obj).encode() + b'e'
    elif isinstance(obj, (bytes, bytearray)):
        data = bytes(obj)
        return str(len(data)).encode() + b':' + data
    elif isinstance(obj, str):
        data = obj.encode()
        return str(len(data)).encode() + b':' + data
    elif isinstance(obj, list):
        return b'l' + b''.join(encode(item) for item in obj) + b'e'
    elif isinstance(obj, dict):
        # Keys must be sorted strings or bytes
        items = []
        for key in sorted(obj):
            key_b = key if isinstance(key, (bytes, bytearray)) else str(key).encode()
            items.append(str(len(key_b)).encode() + b':' + key_b)
            items.append(encode(obj[key]))
        return b'd' + b''.join(items) + b'e'
    else:
        raise TypeError(f"Type {type(obj)} not supported for bencoding")


def decode(data: bytes) -> typing.Any:
    """
    Decode Bencoded bytes into Python objects.
    """
    def _decode(index: int) -> typing.Tuple[typing.Any, int]:
        byte = data[index]
        if byte == ord('i'):
            # integer: i<digits>e
            end = data.index(b'e', index)
            number = int(data[index + 1 : end])
            return number, end + 1
        elif byte in b'0123456789':
            # byte string: <len>:<data>
            colon = data.index(b':', index)
            length = int(data[index:colon])
            start = colon + 1
            end = start + length
            return data[start:end], end
        elif byte == ord('l'):
            # list: l<items>e
            lst = []
            idx = index + 1
            while data[idx] != ord('e'):
                item, idx = _decode(idx)
                lst.append(item)
            return lst, idx + 1
        elif byte == ord('d'):
            # dict: d<pairs>e
            dct = {}
            idx = index + 1
            while data[idx] != ord('e'):
                key, idx = _decode(idx)
                val, idx = _decode(idx)
                # decode key to str if bytes
                if isinstance(key, bytes):
                    key = key.decode()
                dct[key] = val
            return dct, idx + 1
        else:
            raise ValueError(f"Invalid bencode data at position {index}")

    result, final_idx = _decode(0)
    if final_idx != len(data):
        raise ValueError("Extra data after valid bencode decoding")
    return result
