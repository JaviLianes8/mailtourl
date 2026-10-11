"""The parsed form of a mailto: URI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Mailto:
    """Recipients and header fields decoded from a mailto: URI."""

    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    subject: str | None = None
    body: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
