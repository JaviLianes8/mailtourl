"""Checks shared by both parsing modes and the ones only strict mode applies."""

from __future__ import annotations

from collections.abc import Callable, Collection, Sequence

from ._address import split_address
from ._chars import HEX, LINE_BREAKS, is_control
from ._codec import decode_strict
from ._errors import MailtoError
from ._headers import name_fault
from ._positions import position

# A check of a decoded value: (value, raw text, offset of the raw text in the input).
Check = Callable[[str, str, int], None]


def guard(value: str, raw: str, offset: int, what: str) -> None:
    """Refuse the characters that let a field smuggle in another header line."""
    for index, char in enumerate(value):
        if char in LINE_BREAKS:
            where = position(raw, index, offset)
            raise MailtoError(f"{char!r} in the {what}: header injection", where)


def check_raw(raw: str, allowed: Collection[str], offset: int, what: str) -> None:
    """Every raw character is allowed by the grammar or starts a complete escape."""
    for index, char in enumerate(raw):
        if char == "%":
            if raw[index + 1 : index + 2] not in HEX or raw[index + 2 : index + 3] not in HEX:
                raise MailtoError("incomplete percent-encoding", offset + index)
        elif char not in allowed:
            raise MailtoError(f"{char!r} must be percent-encoded in the {what}", offset + index)


def read_part(
    raw: str,
    offset: int,
    allowed: Collection[str],
    what: str,
    checks: Sequence[Check],
    also: MailtoError | None = None,
) -> str:
    """Decode one part of the URI in strict mode and apply ``checks`` to the value.

    Every rule is checked and the error found first in the text is raised (on a tie, the
    first rule listed: raw characters, UTF-8, then ``checks``, then ``also``), so the
    offset is always that of the first offending character.
    """
    errors: list[MailtoError] = []
    try:
        check_raw(raw, allowed, offset, what)
    except MailtoError as error:
        errors.append(error)
    value = ""
    try:
        value = decode_strict(raw, offset)
    except MailtoError as error:
        errors.append(error)
    else:
        for check in checks:
            try:
                check(value, raw, offset)
            except MailtoError as error:
                errors.append(error)
    if also is not None:
        errors.append(also)
    if errors:
        raise min(errors, key=lambda error: error.offset or 0)
    return value


def check_name(name: str, raw: str, offset: int) -> None:
    fault = name_fault(name)
    if fault is not None:
        raise MailtoError(fault[0], position(raw, fault[1], offset))


def check_text(value: str, raw: str, offset: int, what: str) -> None:
    """No control characters but HTAB in a header value."""
    for index, char in enumerate(value):
        if is_control(char) and char != "\t":
            where = position(raw, index, offset)
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
            where = position(raw, index, offset)
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


def _separator(address: str) -> int:
    """Index of the "@" right after the local part, which may hold others in quotes, or -1."""
    if not address.startswith('"'):
        return address.find("@")
    index = 1
    while index < len(address):
        if address[index] == "\\":
            index += 2
        elif address[index] == '"':
            return index + 1 if address[index + 1 : index + 2] == "@" else -1
        else:
            index += 1
    return -1


def check_address(address: str, raw: str, offset: int) -> None:
    """An addr-spec per RFC 6068 section 2, percent-encoding in a domain only for UTF-8."""
    errors: list[MailtoError] = []
    try:
        split_address(address)
    except MailtoError as error:
        errors.append(MailtoError(error.reason, position(raw, error.offset or 0, offset)))
    separator = _separator(address)
    if separator >= 0:
        at = position(raw, separator, 0)
        if raw[at : at + 1] != "@":
            reason = "the '@' before the domain must not be percent-encoded"
            errors.append(MailtoError(reason, offset + at))
        elif not address[separator + 1 :].startswith("["):
            escape = _ascii_escape(raw[at + 1 :])
            if escape >= 0:
                where = offset + at + 1 + escape
                errors.append(MailtoError("percent-encoding of ASCII in a domain name", where))
    if errors:
        raise min(errors, key=lambda error: error.offset or 0)
