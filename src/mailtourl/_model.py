"""The parsed form of a mailto: URI."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ._address import is_address
from ._build import build
from ._headers import DEFAULT_SAFE


def _strings(value: str | Iterable[str], what: str) -> tuple[str, ...]:
    if isinstance(value, (bytes, bytearray)):
        raise TypeError(f"{what} must be str or an iterable of str, got bytes")
    items = (value,) if isinstance(value, str) else tuple(value)
    for item in items:
        if not isinstance(item, str):
            raise TypeError(f"{what} must hold str, got {type(item).__name__}")
    return items


def _pairs(value: Mapping[str, str] | Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    items = tuple(value.items()) if isinstance(value, Mapping) else tuple(value)
    pairs: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise TypeError("headers must hold (name, value) pairs")
        name, text = item
        if not isinstance(name, str) or not isinstance(text, str):
            raise TypeError("headers must hold (str, str) pairs")
        pairs.append((name, text))
    return tuple(pairs)


def _optional(value: str | None, what: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{what} must be str or None, got {type(value).__name__}")
    return value


@dataclass(frozen=True, init=False)
class Mailto:
    """Recipients and header fields of a mailto: URI, decoded.

    Frozen and hashable. ``headers`` holds every other field as ``(name, value)`` pairs in
    URI order, repeats included; ``header`` and ``header_all`` look names up ignoring case.
    """

    to: tuple[str, ...]
    cc: tuple[str, ...]
    bcc: tuple[str, ...]
    subject: str | None
    body: str | None
    headers: tuple[tuple[str, str], ...]

    def __init__(
        self,
        to: str | Iterable[str] = (),
        *,
        cc: str | Iterable[str] = (),
        bcc: str | Iterable[str] = (),
        subject: str | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | Iterable[tuple[str, str]] = (),
    ) -> None:
        object.__setattr__(self, "to", _strings(to, "to"))
        object.__setattr__(self, "cc", _strings(cc, "cc"))
        object.__setattr__(self, "bcc", _strings(bcc, "bcc"))
        object.__setattr__(self, "subject", _optional(subject, "subject"))
        object.__setattr__(self, "body", _optional(body, "body"))
        object.__setattr__(self, "headers", _pairs(headers))

    @property
    def recipients(self) -> tuple[str, ...]:
        """Every address in ``to``, ``cc`` and ``bcc``, in that order."""
        return self.to + self.cc + self.bcc

    def header_all(self, name: str) -> tuple[str, ...]:
        """Values of every other field called ``name``, ignoring case."""
        key = name.lower()
        return tuple(value for field, value in self.headers if field.lower() == key)

    def header(self, name: str) -> str | None:
        """The first value of the other field called ``name``, ignoring case."""
        values = self.header_all(name)
        return values[0] if values else None

    def safe(self, allow: Iterable[str] = DEFAULT_SAFE) -> Mailto:
        """A copy keeping only the headers named in ``allow`` (RFC 6068 section 4).

        Subject and body are kept, and every recipient that is an addr-spec (``is_address``),
        so a lenient reading such as ``a@x,b@y`` held in one entry or a display name is
        dropped. The default keeps ``keywords``, the one other field the RFC calls safe in
        general; widen it for sources you trust.
        """
        keep = {name.lower() for name in _strings(allow, "allow")}
        pairs = tuple(pair for pair in self.headers if pair[0].lower() in keep)
        to, cc, bcc = (tuple(filter(is_address, slot)) for slot in (self.to, self.cc, self.bcc))
        return Mailto(to, cc=cc, bcc=bcc, subject=self.subject, body=self.body, headers=pairs)

    def to_uri(self) -> str:
        """Build the URI with the same rules and checks as ``build``."""
        return build(
            self.to,
            cc=self.cc,
            bcc=self.bcc,
            subject=self.subject,
            body=self.body,
            headers=self.headers,
        )
