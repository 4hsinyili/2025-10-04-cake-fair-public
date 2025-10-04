import base64

from pydantic import TypeAdapter


def to_dict(instance, exclude_none: bool = True, *args, **kwargs) -> dict:
    """將 Pydantic 或 dataclass 實例轉換為字典"""
    return TypeAdapter(instance.__class__).dump_python(
        instance, exclude_none=exclude_none, *args, **kwargs
    )


def to_json(instance, exclude_none: bool = True, *args, **kwargs) -> str:
    """將 Pydantic 或 dataclass 實例轉換為 JSON 字串"""
    return TypeAdapter(instance.__class__).dump_json(
        instance, exclude_none=exclude_none, *args, **kwargs
    )


def bytes_to_base64(value: bytes | str | None):
    if value is None or isinstance(value, str):
        return value
    return base64.b64encode(value).decode("utf-8")


def base64_to_bytes(value: bytes | str | None):
    if value is None or isinstance(value, bytes):
        return value
    try:
        return base64.b64decode(value)
    except Exception:
        return value.encode("utf-8")
