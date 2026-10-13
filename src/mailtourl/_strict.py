"""Checks shared by both parsing modes and the ones only strict mode applies."""

from __future__ import annotations

from collections.abc import Collection

from ._address import split_address
from ._chars import FTEXT, HEX, is_control
from ._errors import MailtoError

# A decoded CR or LF outside the body ends a header line in the composed message, and a
# NUL truncates it in C-based clients: refused in every mode.
_INJECTION = "\r\n\x00"


def guard(value: str, what: str, offset: int) -> None:
    """Refuse the characters that let a field smuggle in another header line."""
    for char in value:
        if char in _INJECTION:
            raise MailtoError(f"{char!r} in the {what}: header injection", offset)


def check_raw(raw: str, allowed: Collection[str], offset: int, what: str) -> None:
    """Every raw character is allowed by the grammar or starts a percent-encoding."""
    for index, char in enumerate(raw):
        if char not in allowed and char != "%":
            raise MailtoError(f"{char!r} must be percent-encoded in the {what}", offset + index)


def check_name(name: str, offset: int) -> None:
    if not name or any(char not in FTEXT for char in name):
        raise MailtoError(f"{name!r} is not an RFC 5322 header field name", offset)


def check_text(value: str, what: str, offset: int) -> None:
    """No control characters but HTAB in a header value."""
    for char in value:
        if is_control(char) and char != "\t":
            raise MailtoError(f"control character {char!r} in the {what}", offset)


def check_body(value: str, offset: int) -> None:
    """Line breaks only as CRLF (RFC 6068 section 5), no other control but HTAB."""
    for index, char in enumerate(value):
        if char == "\r" and value[index + 1 : index + 2] == "\n":
            continue
        if char == "\n" and value[index - 1 : index] == "\r":
            continue
        if char in "\r\n":
            raise MailtoError("body line break not written as %0D%0A", offset)
        if is_control(char) and char != "\t":
            raise MailtoError(f"control character {char!r} in the body", offset)


def _ascii_escape(raw: str) -> bool:
    """True when ``raw`` percent-encodes an ASCII character."""
    index = raw.find("%")
    while index >= 0:
        if raw[index + 1 : index + 2] in HEX and raw[index + 1] in "01234567":
            return True
        index = raw.find("%", index + 1)
    return False


def check_address(address: str, raw: str, offset: int) -> None:
    """An addr-spec per RFC 6068 section 2, percent-encoding in a domain only for UTF-8."""
    try:
        _, domain = split_address(address)
    except MailtoError as error:
        raise MailtoError(error.reason, offset) from None
    if "@" in raw and not domain.startswith("["):
        at = raw.rindex("@")
        if _ascii_escape(raw[at + 1 :]):
            raise MailtoError("percent-encoding of ASCII in a domain name", offset + at + 1)
