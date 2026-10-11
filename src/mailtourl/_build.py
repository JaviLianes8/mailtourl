"""Build a mailto: URI from recipients and header fields (RFC 6068)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ._codec import encode_address, encode_header

_SCHEME = "mailto:"


def _as_list(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _join_addresses(value: str | Iterable[str] | None) -> str:
    return ",".join(encode_address(address) for address in _as_list(value))


def build(
    to: str | Iterable[str] | None = None,
    *,
    cc: str | Iterable[str] | None = None,
    bcc: str | Iterable[str] | None = None,
    subject: str | None = None,
    body: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    """Build a mailto: URI, percent-encoding every field per RFC 6068."""
    fields: list[tuple[str, str]] = []
    for name, addresses in (("cc", cc), ("bcc", bcc)):
        joined = _join_addresses(addresses)
        if joined:
            fields.append((name, joined))
    if subject is not None:
        fields.append(("subject", encode_header(subject)))
    if body is not None:
        fields.append(("body", encode_header(body)))
    if headers:
        for name, value in headers.items():
            fields.append((encode_header(name), encode_header(value)))

    path = _join_addresses(to)
    query = "&".join(f"{name}={value}" for name, value in fields)
    return f"{_SCHEME}{path}?{query}" if query else f"{_SCHEME}{path}"
