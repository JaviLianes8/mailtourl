"""Parse and build mailto: URIs per RFC 6068, safely and with correct percent-encoding.

>>> from mailtourl import build, parse
>>> parse("mailto:jane@example.com?subject=Hi%20there").subject
'Hi there'
>>> build("jane@example.com", body="one\\ntwo")
'mailto:jane@example.com?body=one%0D%0Atwo'
"""

from __future__ import annotations

from ._address import is_address
from ._build import build
from ._errors import MailtoError
from ._model import Mailto
from ._parse import parse

__version__ = "1.0.0"

# The public classes show and pickle as mailtourl.<Name>, so a pickle never depends on the
# private module that defines them.
for _cls in (Mailto, MailtoError):
    _cls.__module__ = __name__
    # Methods follow, so doctest finds their examples here (it takes properties anyway).
    for _member in vars(_cls).values():
        if callable(_member) and str(getattr(_member, "__module__", "")).startswith("mailtourl._"):
            _member.__module__ = __name__
del _cls, _member

__all__ = ["Mailto", "MailtoError", "build", "is_address", "parse"]
