"""Parse a mailto: URI into a Mailto (RFC 6068, WHATWG URL preprocessing)."""

from __future__ import annotations

import re

from ._chars import FTEXT, PCHAR, QCHAR, plain
from ._codec import decode
from ._errors import MailtoError, quoted
from ._headers import RECIPIENTS
from ._model import Mailto
from ._strict import check_address, check_body, check_name, check_raw, check_text, guard

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
        for part in raw.split(","):
            if self.strict:
                check_raw(part, allowed, offset, f"{key} address")
            address = decode(part, offset, strict=self.strict)
            guard(address, part, f"{key} address", offset)
            if self.strict:
                check_address(address, part, offset)
            else:
                address = address.strip()
            if address:
                self.recipients[key].append(address)
            offset += len(part) + 1

    def field(self, segment: str, offset: int) -> None:
        raw_name, equals, raw_value = segment.partition("=")
        value_at = offset + len(raw_name) + 1
        if self.strict:
            if not equals:
                raise MailtoError("header field without '='", offset + len(segment))
            check_raw(raw_name, QCHAR, offset, "header field name")
        name = decode(raw_name, offset, strict=self.strict)
        guard(name, raw_name, "header field name", offset)
        if self.strict:
            check_name(name, offset)
        else:
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
        if self.strict:
            check_raw(raw_value, QCHAR, value_at, f"{shown} value")
        value = decode(raw_value, value_at, strict=self.strict)
        if key == "body":
            if self.strict:
                check_body(value, raw_value, value_at)
            self.body = value if self.body is None else self.body
            return
        guard(value, raw_value, f"{shown} field", value_at)
        if self.strict:
            check_text(value, raw_value, f"{shown} field", value_at)
        if key == "subject":
            self.subject = value if self.subject is None else self.subject
        else:
            self.headers.append((name, value))

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
    if hash_mark and strict:
        raise MailtoError("a mailto: URI takes no fragment", start + len(hier))
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
    cleaned = _REMOVED.sub("", uri.strip(_C0_OR_SPACE))
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
