"""Error raised for malformed or unsafe mailto: URIs and builder input."""

from __future__ import annotations

_SHOWN = 60


def quoted(text: str) -> str:
    """``repr`` of ``text`` cut to a few dozen characters, so a message never echoes huge input."""
    shown = repr(text[:_SHOWN])
    return shown if len(text) <= _SHOWN and len(shown) <= _SHOWN + 2 else shown[:_SHOWN] + "..."


class MailtoError(ValueError):
    r"""Raised when a string cannot be read as a mailto: URI or a field cannot be written.

    A ``ValueError``. ``reason`` is the message without the position; ``offset`` is the
    index in the parsed string where the problem starts, or None when there is none (the
    builder's errors).

    >>> from mailtourl import MailtoError, parse
    >>> try:
    ...     parse("mailto:a@example.com?subject=%0D%0ABcc:%20spy@evil.example")
    ... except MailtoError as error:
    ...     print(error.reason, error.offset, isinstance(error, ValueError))
    '\r' in the subject field: header injection 29 True
    """

    def __init__(self, reason: str, offset: int | None = None) -> None:
        super().__init__(reason if offset is None else f"{reason} at offset {offset}")
        self.reason = reason
        self.offset = offset

    def __reduce__(self) -> tuple[type[MailtoError], tuple[str, int | None]]:
        return (type(self), (self.reason, self.offset))
