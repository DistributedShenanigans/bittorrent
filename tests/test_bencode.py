import pytest
from utils.bencode import encode, decode

@pytest.mark.parametrize("value,expected", [
    (0, b"i0e"),
    (42, b"i42e"),
    (b"spam", b"4:spam"),
    ("spam", b"4:spam"),
    ([1, b"ab"], b"li1e2:abe"),
    ({"a": 1, "b": b"xy"}, b"d1:ai1e1:b2:xye")  # словари сортируются по ключам
])
def test_encode_literals(value, expected):
    assert encode(value) == expected

@pytest.mark.parametrize("bencoded,obj", [
    (b"i-5e", -5),
    (b"0:", b""),
    (b"l4:spam4:eggse", [b"spam", b"eggs"]),
    (b"d3:key5:valuee", {"key": b"value"}),
])
def test_decode_literals(bencoded, obj):
    assert decode(bencoded) == obj

def test_roundtrip_complex():
    original = {
        "num": 123,
        "data": [b"a", b"b", {"x": 1}],
    }
    encoded = encode(original)
    decoded = decode(encoded)
    # при декодировании байты-ключи превращаются в строки
    assert decoded["num"] == 123
    assert decoded["data"][0] == b"a"

def test_decode_error():
    with pytest.raises(ValueError):
        decode(b"i123")  # нет завершающего 'e'
