"""Parse and build mailto: URIs per RFC 6068 with correct percent-encoding."""

from __future__ import annotations

from ._build import build
from ._errors import MailtoError
from ._model import Mailto
from ._parse import parse

__version__ = "0.1.0"

__all__ = ["Mailto", "MailtoError", "build", "parse"]
