"""Build a mailto: URI from recipients and header fields (RFC 6068)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import TypeAlias

from ._chars import FTEXT, is_control
from ._codec import encode_address, encode_field
from ._errors import MailtoError, quoted
from ._headers import DEDICATED, is_ignored

_SCHEME = "mailto:"
_LINE_BREAK = re.compile(r"\r\n|\r|\n")

Addresses: TypeAlias = str | Iterable[str] | None
Headers: TypeAlias = Mapping[str, str] | Iterable[tuple[str, str]] | None


def _as_list(value: Addresses, what: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (bytes, bytearray)) or not isinstance(value, Iterable):
        raise TypeError(f"{what} must be str or an iterable of str, got {type(value).__name__}")
    items = list(value)
    for item in items:
        if not isinstance(item, str):
            raise TypeError(f"{what} must hold str, got {type(item).__name__}")
    return items


def _join(value: Addresses, what: str) -> str:
    encoded: list[str] = []
    for address in _as_list(value, what):
        try:
            encoded.append(encode_address(address))
        except MailtoError as error:
            raise MailtoError(f"{what}: {error.reason}") from None
    return ",".join(encoded)


def _check_text(value: object, what: str, *, body: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{what} must be str, got {type(value).__name__}")
    for char in value:
        # A body line may hold the Unicode separators; a header may not (str.splitlines).
        hidden = 0x7F <= ord(char) <= 0x9F or ord(char) < 0x20 if body else is_control(char)
        if hidden and char != "\t":
            # Line breaks outside the body are how header injection works.
            raise MailtoError(f"control character {char!r} in {what}")
    return value


def _encode_body(body: object) -> str:
    if not isinstance(body, str):
        raise TypeError(f"body must be str, got {type(body).__name__}")
    # RFC 6068 section 5: line breaks in the body MUST be encoded as %0D%0A.
    lines = _LINE_BREAK.split(body)
    for line in lines:
        _check_text(line, "body", body=True)
    return encode_field("\r\n".join(lines))


def _header_pairs(headers: Headers) -> list[tuple[str, str]]:
    if headers is None:
        return []
    if isinstance(headers, (str, bytes, bytearray)) or not isinstance(headers, Iterable):
        raise TypeError(f"headers must be a mapping or pairs, got {type(headers).__name__}")
    items = list(headers.items()) if isinstance(headers, Mapping) else list(headers)
    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise TypeError("headers must hold (name, value) pairs")
        name, value = item
        _check_text(name, "header name")
        if not name or any(char not in FTEXT for char in name):
            raise MailtoError(f"{quoted(name)} is not an RFC 5322 header field name")
        key = name.lower()
        if key in DEDICATED:
            raise MailtoError(f"pass {key!r} through its own argument, not headers")
        if is_ignored(name):
            raise MailtoError(f"RFC 6068 section 3 says clients MUST ignore {quoted(name)}")
        if key in seen:
            raise MailtoError(f"header {quoted(name)} given twice")
        seen.add(key)
        pairs.append((name, _check_text(value, f"header {quoted(name)}")))
    return pairs


def build(
    to: Addresses = None,
    *,
    cc: Addresses = None,
    bcc: Addresses = None,
    subject: str | None = None,
    body: str | None = None,
    headers: Headers = None,
) -> str:
    r"""Build a mailto: URI, percent-encoding every field per RFC 6068.

    Raises MailtoError for an address that is not an addr-spec, a control character
    outside the body, a header name that is not a field name, given twice, owned by a
    dedicated argument or one RFC 6068 says clients must ignore, and TypeError for
    arguments of the wrong type. Body line breaks are written as CRLF.

    >>> build(["a@example.com", "b@example.com"], subject="Re: 1+1", body="hi\nthere")
    'mailto:a@example.com,b@example.com?subject=Re:%201%2B1&body=hi%0D%0Athere'
    >>> build(cc="c@example.com", headers={"Keywords": "a&b"})
    'mailto:?cc=c@example.com&Keywords=a%26b'
    >>> build("a@example.com", subject="Hi\r\nBcc: spy@evil.example")
    Traceback (most recent call last):
    mailtourl.MailtoError: control character '\r' in subject
    """
    fields: list[tuple[str, str]] = []
    for name, addresses in (("cc", cc), ("bcc", bcc)):
        joined = _join(addresses, name)
        if joined:
            fields.append((name, joined))
    if subject is not None:
        fields.append(("subject", encode_field(_check_text(subject, "subject"))))
    if body is not None:
        fields.append(("body", _encode_body(body)))
    for name, value in _header_pairs(headers):
        fields.append((encode_field(name), encode_field(value)))

    path = _join(to, "to")
    query = "&".join(f"{name}={value}" for name, value in fields)
    return f"{_SCHEME}{path}?{query}" if query else f"{_SCHEME}{path}"
