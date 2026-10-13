"""Error raised for malformed or unsafe mailto: URIs and builder input."""

from __future__ import annotations


class MailtoError(ValueError):
    """Raised when a string cannot be read as a mailto: URI or a field cannot be written.

    ``offset`` is the index in the input where the problem starts, when there is one.
    """

    def __init__(self, message: str, offset: int | None = None) -> None:
        super().__init__(message if offset is None else f"{message} at offset {offset}")
        self.reason = message
        self.offset = offset

    def __reduce__(self) -> tuple[type[MailtoError], tuple[str, int | None]]:
        return (type(self), (self.reason, self.offset))
