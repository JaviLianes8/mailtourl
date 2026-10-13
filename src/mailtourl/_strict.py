"""Checks shared by both parsing modes and the ones only strict mode applies."""

from __future__ import annotations

from collections.abc import Collection

from ._address import split_address
from ._chars import FTEXT, HEX, LINE_BREAKS, is_control
from ._errors import MailtoError


def position(raw: str, value: str, index: int, offset: int) -> int:
    """Offset in the input of ``value[index]``, where ``value`` is ``raw`` decoded."""
    target = len(value[:index].encode("utf-8", "surrogatepass"))
    consumed = 0
    at = 0
    while at < len(raw) and consumed < target:
        if raw[at] == "%" and raw[at + 1 : at + 2] in HEX and raw[at + 2 : at + 3] in HEX:
            consumed, at = consumed + 1, at + 3
        else:
            consumed, at = consumed + len(raw[at].encode("utf-8", "surrogatepass")), at + 1
    return offset + at


def guard(value: str, raw: str, what: str, offset: int) -> None:
    """Refuse the characters that let a field smuggle in another header line."""
    for index, char in enumerate(value):
        if char in LINE_BREAKS:
            where = position(raw, value, index, offset)
            raise MailtoError(f"{char!r} in the {what}: header injection", where)


def check_raw(raw: str, allowed: Collection[str], offset: int, what: str) -> None:
    """Every raw character is allowed by the grammar or starts a percent-encoding."""
    for index, char in enumerate(raw):
        if char not in allowed and char != "%":
            raise MailtoError(f"{char!r} must be percent-encoded in the {what}", offset + index)


def check_name(name: str, offset: int) -> None:
    if not name or any(char not in FTEXT for char in name):
        raise MailtoError(f"{name[:60]!r} is not an RFC 5322 header field name", offset)


def check_text(value: str, raw: str, what: str, offset: int) -> None:
    """No control characters but HTAB in a header value."""
    for index, char in enumerate(value):
        if is_control(char) and char != "\t":
            where = position(raw, value, index, offset)
            raise MailtoError(f"control character {char!r} in the {what}", where)


def check_body(value: str, raw: str, offset: int) -> None:
    """Line breaks only as CRLF (RFC 6068 section 5), no other C0 or C1 control but HTAB."""
    for index, char in enumerate(value):
        if char == "\r" and value[index + 1 : index + 2] == "\n":
            continue
        if char == "\n" and value[index - 1 : index] == "\r":
            continue
        code = ord(char)
        if char in "\r\n" or ((code < 0x20 or 0x7F <= code <= 0x9F) and char != "\t"):
            where = position(raw, value, index, offset)
            if char in "\r\n":
                raise MailtoError("body line break not written as %0D%0A", where)
            raise MailtoError(f"control character {char!r} in the body", where)


def _ascii_escape(raw: str) -> int:
    """Index of the first escape of an ASCII character in ``raw``, or -1."""
    index = raw.find("%")
    while index >= 0:
        if raw[index + 1 : index + 2] in HEX and raw[index + 1] in "01234567":
            return index
        index = raw.find("%", index + 1)
    return -1


def check_address(address: str, raw: str, offset: int) -> None:
    """An addr-spec per RFC 6068 section 2, percent-encoding in a domain only for UTF-8."""
    try:
        _, domain = split_address(address)
    except MailtoError as error:
        raise MailtoError(error.reason, offset) from None
    if "@" not in raw:
        raise MailtoError("the '@' before the domain must not be percent-encoded", offset)
    if not domain.startswith("["):
        at = raw.rindex("@")
        escape = _ascii_escape(raw[at + 1 :])
        if escape >= 0:
            where = offset + at + 1 + escape
            raise MailtoError("percent-encoding of ASCII in a domain name", where)
