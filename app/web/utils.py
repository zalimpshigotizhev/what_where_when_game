import base64

from aiohttp.web import json_response as aiohttp_json_response
from aiohttp.web_response import Response


def json_response(data: dict | None = None, status: str = "ok") -> Response:
    return aiohttp_json_response(
        data={
            "status": status,
            "data": data or {},
        }
    )


def error_json_response(
    http_status: int,
    status: str = "error",
    message: str | None = None,
    data: dict | None = None,
):
    return aiohttp_json_response(
        status=http_status,
        data={
            "status": status,
            "message": str(message),
            "data": data or {},
        },
    )


def encode_data(data: str, key: str) -> str:
    """Кодирует данные с помощью текстового ключа."""
    encoded = []
    key_len = len(key)
    for i, char in enumerate(data):
        key_char = key[i % key_len]
        encoded_char = chr(ord(char) ^ ord(key_char))
        encoded.append(encoded_char)
    encoded_str = "".join(encoded)
    return base64.b64encode(encoded_str.encode("utf-8")).decode("utf-8")


def decode_data(encoded_data: str, key: str) -> str:
    """Декодирует данные с помощью текстового ключа."""
    decoded = []
    encoded_str = base64.b64decode(encoded_data).decode("utf-8")
    key_len = len(key)
    for i, char in enumerate(encoded_str):
        key_char = key[i % key_len]
        decoded_char = chr(ord(char) ^ ord(key_char))
        decoded.append(decoded_char)
    return "".join(decoded)
