"""Percent-encoding and decoding for mailto: URI components (RFC 3986, RFC 6068)."""

from __future__ import annotations

from urllib.parse import quote, unquote, unquote_to_bytes

from ._address import check_domain, split_address
from ._chars import ADDRESS_SAFE, FIELD_SAFE
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


def encode_address(address: str, *, query: bool) -> str:
    """Percent-encode one validated address; "@" is encoded inside the local part.

    In a query field "+" is encoded too, since a form decoder reads it as a space (RFC 6068
    section 5); ``check_domain`` keeps it out of a domain name, which may not be encoded.
    """
    local, domain = split_address(address)
    check_domain(domain)
    safe = ADDRESS_SAFE.replace("+", "") if query else ADDRESS_SAFE
    return f"{_quote(local, safe)}@{_quote(domain, safe)}"


def decode(raw: str) -> str:
    """Reverse percent-encoding as UTF-8, keeping broken escapes and replacing bad bytes."""
    return unquote(raw)


def decode_strict(raw: str, offset: int) -> str:
    """Reverse percent-encoding as UTF-8; raise MailtoError at the first byte that is not.

    A broken escape is kept as written: the raw-character check reports it.
    """
    data = unquote_to_bytes(raw.encode("utf-8", "surrogatepass"))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        where = byte_position(raw, error.start, offset)
        raise MailtoError("percent-encoded bytes are not UTF-8", where) from error
