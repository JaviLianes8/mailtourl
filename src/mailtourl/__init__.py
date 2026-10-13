"""Parse and build mailto: URIs per RFC 6068, safely and with correct percent-encoding."""

from __future__ import annotations

from ._address import is_address
from ._build import build
from ._errors import MailtoError
from ._model import Mailto
from ._parse import parse

__version__ = "0.2.0"

__all__ = ["Mailto", "MailtoError", "build", "is_address", "parse"]
