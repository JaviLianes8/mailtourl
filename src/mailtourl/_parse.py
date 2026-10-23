"""Parse a mailto: URI into a Mailto (RFC 6068, WHATWG URL preprocessing)."""

from __future__ import annotations

import re
from functools import partial

from ._chars import FTEXT, PCHAR, QCHAR, plain
from ._codec import decode
from ._errors import MailtoError, quoted
from ._headers import RECIPIENTS
from ._model import Mailto
from ._strict import (
    Check,
    check_address,
    check_body,
    check_name,
    check_text,
    guard,
    read_part,
)

_SCHEME = "mailto:"
_C0_OR_SPACE = "".join(chr(code) for code in range(0x21))
# The URL Standard removes every tab and newline from a link before it parses it.
_REMOVED = re.compile("[\t\n\r]")


class _Reader:
    def __init__(self, strict: bool) -> None:
        self.strict = strict
        self.recipients: dict[str, list[str]] = {key: [] for key in RECIPIENTS}
        self.subject: str | None = None
        self.body: str | None = None
        self.headers: list[tuple[str, str]] = []
        self.seen: set[str] = set()

    def addresses(self, key: str, raw: str, offset: int, allowed: frozenset[str]) -> None:
        if not raw:
            return
        what = f"{key} address"
        for part in raw.split(","):
            if self.strict:
                checks = (partial(guard, what=what), check_address)
                address = read_part(part, offset, allowed, what, checks)
            else:
                address = decode(part)
                guard(address, part, offset, what)
                address = address.strip()
            if address:
                self.recipients[key].append(address)
            offset += len(part) + 1

    def field(self, segment: str, offset: int) -> None:
        raw_name, equals, raw_value = segment.partition("=")
        value_at = offset + len(raw_name) + 1
        what = "header field name"
        if self.strict:
            end = offset + len(segment)
            missing = None if equals else MailtoError("header field without '='", end)
            checks = (partial(guard, what=what), check_name)
            name = read_part(raw_name, offset, QCHAR, what, checks, missing)
        else:
            name = decode(raw_name)
            guard(name, raw_name, offset, what)
            # Trimmed before it is classified, so " bcc" cannot hide a recipient, and a
            # name that is still not a field name ("Bcc:x", controls) is dropped.
            name = name.strip()
            if not name or any(char not in FTEXT for char in name):
                return
        key = name.lower()
        if self.strict:
            if key in self.seen:
                raise MailtoError(f"header field {quoted(name)} repeated", offset)
            self.seen.add(key)
        shown = name if len(name) <= 60 else f"{name[:60]}..."
        if key in RECIPIENTS:
            self.addresses(key, raw_value, value_at, QCHAR)
            return
        if key == "body":
            value = self.value(raw_value, value_at, shown, body=True)
            self.body = value if self.body is None else self.body
            return
        value = self.value(raw_value, value_at, shown, body=False)
        if key == "subject":
            self.subject = value if self.subject is None else self.subject
        else:
            self.headers.append((name, value))

    def value(self, raw: str, offset: int, shown: str, *, body: bool) -> str:
        """Decode a field value; outside the body, a line break is header injection."""
        field = f"{shown} field"
        if self.strict:
            checks: tuple[Check, ...] = (
                (check_body,)
                if body
                else (partial(guard, what=field), partial(check_text, what=field))
            )
            return read_part(raw, offset, QCHAR, f"{shown} value", checks)
        value = decode(raw)
        if not body:
            guard(value, raw, offset, field)
        return value

    def result(self) -> Mailto:
        return Mailto(
            self.recipients["to"],
            cc=self.recipients["cc"],
            bcc=self.recipients["bcc"],
            subject=self.subject,
            body=self.body,
            headers=self.headers,
        )


def _read(text: str, strict: bool) -> Mailto:
    if text[: len(_SCHEME)].lower() != _SCHEME:
        raise MailtoError("not a mailto: URI", 0)
    start = len(_SCHEME)
    hier, hash_mark, _ = text[start:].partition("#")
    path, question, query = hier.partition("?")
    reader = _Reader(strict)
    reader.addresses("to", path, start, PCHAR)
    if question:
        offset = start + len(path) + 1
        for segment in query.split("&"):
            if segment:
                reader.field(segment, offset)
            elif strict:
                raise MailtoError("empty header field", offset)
            offset += len(segment) + 1
    # Checked last: whatever the part before it breaks comes first in the text.
    if hash_mark and strict:
        raise MailtoError("a mailto: URI takes no fragment", start + len(hier))
    return reader.result()


def parse(uri: str, *, strict: bool = False) -> Mailto:
    """Parse a mailto: URI into a Mailto.

    The default mode first cleans the text as a browser does before it parses a link:
    leading and trailing C0 controls and spaces are stripped, tabs and newlines removed,
    the fragment ignored. ``strict=True`` checks the text against the RFC 6068 grammar
    instead. In both modes a decoded NUL or line break outside the body raises
    MailtoError: it would inject a header. A ``uri`` that is not a ``str`` raises
    TypeError.

    >>> from mailtourl import parse
    >>> mail = parse("mailto:a@example.com,b@example.com?cc=c@example.com&subject=Hi%20there")
    >>> mail.to, mail.cc, mail.subject
    (('a@example.com', 'b@example.com'), ('c@example.com',), 'Hi there')
    >>> parse(" mailto:a@example.com?body=1+1%3D2#ignored ").body
    '1+1=2'
    >>> parse("mailto:a@example.com?subject=a b", strict=True)
    Traceback (most recent call last):
    mailtourl.MailtoError: ' ' must be percent-encoded in the subject value at offset 30
    """
    if not isinstance(uri, str):
        raise TypeError(f"expected str, got {type(uri).__name__}")
    uri = plain(uri)
    if strict:
        return _read(uri, strict=True)
    begin = len(uri) - len(uri.lstrip(_C0_OR_SPACE))
    # str.replace needs no list of pieces as a regex substitution does: a copy at most.
    cleaned = uri.strip(_C0_OR_SPACE).replace("\t", "").replace("\n", "").replace("\r", "")
    try:
        return _read(cleaned, strict=False)
    except MailtoError as error:
        if error.offset is None:
            raise
        offset = _original(uri, begin, error.offset) if cleaned else 0
        raise MailtoError(error.reason, offset) from None


def _original(uri: str, begin: int, index: int) -> int:
    """Index in ``uri`` of character ``index`` of its cleaned text, which starts at ``begin``."""
    at = begin + index
    for removed in _REMOVED.finditer(uri, begin):
        if removed.start() > at:
            break
        at += 1
    return at
