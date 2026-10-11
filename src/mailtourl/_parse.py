"""Parse a mailto: URI into a Mailto (RFC 6068)."""

from __future__ import annotations

from ._codec import decode
from ._errors import MailtoError
from ._model import Mailto

_SCHEME = "mailto:"
_RECIPIENT_FIELDS = ("to", "cc", "bcc")


def _split_addresses(raw: str) -> list[str]:
    """Split a raw comma list into decoded, non-empty addresses."""
    parts = (decode(part).strip() for part in raw.split(","))
    return [part for part in parts if part]


def parse(uri: str) -> Mailto:
    """Parse a mailto: URI; raise MailtoError when the scheme is missing."""
    if uri[: len(_SCHEME)].lower() != _SCHEME:
        raise MailtoError(f"not a mailto: URI: {uri!r}")
    path, _, query = uri[len(_SCHEME) :].partition("?")

    to = _split_addresses(path)
    recipients: dict[str, list[str]] = {"to": to, "cc": [], "bcc": []}
    subject: str | None = None
    body: str | None = None
    headers: dict[str, str] = {}

    for segment in query.split("&"):
        if not segment:
            continue
        name, _, value = segment.partition("=")
        key = decode(name).lower()
        if key in _RECIPIENT_FIELDS:
            recipients[key].extend(_split_addresses(value))
        elif key == "subject":
            subject = decode(value)
        elif key == "body":
            body = decode(value)
        else:
            headers[decode(name)] = decode(value)

    return Mailto(
        to=to,
        cc=recipients["cc"],
        bcc=recipients["bcc"],
        subject=subject,
        body=body,
        headers=headers,
    )
