"""Percent-encoding and decoding for mailto: URI components (RFC 3986, RFC 6068)."""

from __future__ import annotations

from urllib.parse import quote, unquote, unquote_to_bytes

from ._address import check_domain, split_address
from ._chars import ADDRESS_SAFE, FIELD_SAFE, HEX
from ._errors import MailtoError
from ._positions import byte_position


def _quote(value: str, safe: str) -> str:
    try:
        return quote(value, safe=safe)
    except UnicodeEncodeError as error:
        code = ord(value[error.start])
        raise MailtoError(f"lone surrogate U+{code:04X} cannot be encoded as UTF-8") from None


def encode_field(value: str) -> str:
    """Percent-encode a header field name or value."""
    return _quote(value, FIELD_SAFE)


def encode_address(address: str) -> str:
    """Percent-encode one validated address; "@" is encoded inside the local part."""
    local, domain = split_address(address)
    check_domain(domain)
    return f"{_quote(local, ADDRESS_SAFE)}@{_quote(domain, ADDRESS_SAFE)}"


def check_escapes(raw: str, offset: int) -> None:
    """Raise MailtoError at the first "%" not followed by two hex digits."""
    index = raw.find("%")
    while index >= 0:
        if raw[index + 1 : index + 2] not in HEX or raw[index + 2 : index + 3] not in HEX:
            raise MailtoError("incomplete percent-encoding", offset + index)
        index = raw.find("%", index + 3)


def decode(raw: str, offset: int, *, strict: bool) -> str:
    """Reverse percent-encoding as UTF-8; strict mode refuses broken escapes and UTF-8."""
    if not strict:
        return unquote(raw)
    check_escapes(raw, offset)
    try:
        return unquote_to_bytes(raw).decode("utf-8")
    except UnicodeDecodeError as error:
        where = byte_position(raw, error.start, offset)
        raise MailtoError("percent-encoded bytes are not UTF-8", where) from error
