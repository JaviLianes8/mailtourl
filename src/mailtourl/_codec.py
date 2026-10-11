"""Percent-encoding helpers for mailto: URI components (RFC 6068)."""

from __future__ import annotations

from urllib.parse import quote, unquote

# some-delims from RFC 6068 that may stay literal in a field value. The comma is
# the recipient separator, so it is kept out of the address set and encoded
# inside each address, which lets a round trip survive an address that holds one.
_HEADER_SAFE = "!$'()*+,;:@"
_ADDRESS_SAFE = "!$'()*+;:@"


def encode_header(value: str) -> str:
    """Percent-encode a header name or value."""
    return quote(value, safe=_HEADER_SAFE)


def encode_address(value: str) -> str:
    """Percent-encode a single recipient address."""
    return quote(value, safe=_ADDRESS_SAFE)


def decode(value: str) -> str:
    """Reverse percent-encoding, decoding the bytes as UTF-8."""
    return unquote(value)
