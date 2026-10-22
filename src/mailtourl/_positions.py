"""Map a character of a percent-decoded value back to its index in the raw text."""

from __future__ import annotations

from collections.abc import Iterator

from ._chars import HEX


def _escape(raw: str, at: int) -> int | None:
    """The byte a complete "%XX" at ``raw[at]`` stands for, or None."""
    if raw[at] == "%" and raw[at + 1 : at + 2] in HEX and raw[at + 2 : at + 3] in HEX:
        return int(raw[at + 1 : at + 3], 16)
    return None


def _second_byte_range(lead: int) -> tuple[int, int, int] | None:
    """Bytes still to come and the range of the next one (Unicode table 3-7), or None."""
    if 0xC2 <= lead <= 0xDF:
        return 1, 0x80, 0xBF
    if 0xE0 <= lead <= 0xEF:
        return 2, 0xA0 if lead == 0xE0 else 0x80, 0x9F if lead == 0xED else 0xBF
    if 0xF0 <= lead <= 0xF4:
        return 3, 0x90 if lead == 0xF0 else 0x80, 0x8F if lead == 0xF4 else 0xBF
    return None


def _sequence(data: bytearray, at: int) -> int:
    """Length of the character, or of the broken part one U+FFFD replaces, at ``data[at]``.

    The decoder's "replace" handler turns each maximal subpart of a broken sequence into
    one U+FFFD; this finds the same boundaries.
    """
    if data[at] < 0x80:
        return 1
    rule = _second_byte_range(data[at])
    if rule is None or at + 1 >= len(data) or not rule[1] <= data[at + 1] <= rule[2]:
        return 1
    end = at + 2
    while end < at + 1 + rule[0] and end < len(data) and 0x80 <= data[end] <= 0xBF:
        end += 1
    return end - at


def _run_starts(raw: str, begin: int, end: int) -> Iterator[int]:
    """Where each character starts of the ASCII run ``raw[begin:end]`` decoded as UTF-8."""
    data = bytearray()
    where: list[int] = []
    at = begin
    while at < end:
        byte = _escape(raw, at)
        data.append(ord(raw[at]) if byte is None else byte)
        where.append(at)
        at += 1 if byte is None else 3
    index = 0
    while index < len(data):
        yield where[index]
        index += _sequence(data, index)


def char_starts(raw: str) -> Iterator[int]:
    """Index in ``raw`` where each character of ``urllib.parse.unquote(raw)`` starts.

    unquote decodes every run of ASCII text as UTF-8 on its own and copies the rest.
    """
    at = 0
    while at < len(raw):
        if not raw[at].isascii():
            yield at
            at += 1
            continue
        end = at
        while end < len(raw) and raw[end].isascii():
            end += 1
        yield from _run_starts(raw, at, end)
        at = end


def position(raw: str, index: int, offset: int) -> int:
    """Offset in the input of character ``index`` of ``raw`` decoded."""
    if "%" not in raw:
        return offset + index
    for count, start in enumerate(char_starts(raw)):
        if count == index:
            return offset + start
    return offset + len(raw)


def byte_position(raw: str, index: int, offset: int) -> int:
    """Offset in the input of byte ``index`` of ``raw`` percent-decoded to bytes."""
    at = 0
    while at < len(raw):
        step = 1 if _escape(raw, at) is None else 3
        size = 1 if step == 3 else len(raw[at].encode("utf-8", "surrogatepass"))
        if index < size:
            break
        index -= size
        at += step
    return offset + at
