def bencode(value):
    if isinstance(value, int):
        return f"i{value}e".encode()
    elif isinstance(value, bytes):
        return f"{len(value)}:".encode() + value
    elif isinstance(value, str):
        value_bytes = value.encode()
        return f"{len(value_bytes)}:".encode() + value_bytes
    elif isinstance(value, list):
        return b'l' + b''.join(bencode(item) for item in value) + b'e'
    elif isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            key_bytes = key.encode() if isinstance(key, str) else key
            items.append(bencode(key_bytes))
            items.append(bencode(value[key]))
        return b'd' + b''.join(items) + b'e'
    else:
        raise TypeError(f"Type {type(value)} not supported for bencoding.")

def bdecode(data):
    def decode_next(index):
        if data[index:index+1] == b'i':
            end = data.index(b'e', index)
            number = int(data[index+1:end])
            return number, end + 1
        elif data[index:index+1] == b'l':
            lst, index = [], index + 1
            while data[index:index+1] != b'e':
                item, index = decode_next(index)
                lst.append(item)
            return lst, index + 1
        elif data[index:index+1] == b'd':
            dct, index = {}, index + 1
            while data[index:index+1] != b'e':
                key, index = decode_next(index)
                val, index = decode_next(index)
                dct[key] = val
            return dct, index + 1
        elif data[index:index+1].isdigit():
            colon = data.index(b':', index)
            length = int(data[index:colon])
            start = colon + 1
            end = start + length
            return data[start:end], end
        else:
            raise ValueError(f"Invalid bencode at position {index}")

    decoded_value, final_index = decode_next(0)
    if final_index != len(data):
        raise ValueError("Extra data after parsing.")
    return decoded_value
