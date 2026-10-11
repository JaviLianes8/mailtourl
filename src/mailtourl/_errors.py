"""Error raised for malformed mailto: URIs."""

from __future__ import annotations


class MailtoError(ValueError):
    """Raised when a string cannot be read as a mailto: URI."""
