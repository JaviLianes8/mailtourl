"""Header field rules from RFC 6068 sections 3 and 4."""

from __future__ import annotations

from ._chars import FTEXT

# Fields with a dedicated slot on Mailto and a dedicated argument on build.
DEDICATED = frozenset({"to", "cc", "bcc", "subject", "body"})
RECIPIENTS = ("to", "cc", "bcc")

# Section 3: originator fields (RFC 5322 3.6.1 and 3.6.2), routing fields, trace fields
# (RFC 5322 3.6.7) and MIME fields MUST be ignored by the client resolving the URI.
_IGNORED = frozenset(
    {"from", "sender", "reply-to", "date", "apparently-to", "received", "return-path"}
)
_IGNORED_PREFIXES = ("resent-", "content-", "mime-")

# Section 4: subject, keywords and body are believed safe in the general case.
DEFAULT_SAFE = ("keywords",)


def is_ignored(name: str) -> bool:
    """True for a field RFC 6068 section 3 says a client MUST ignore."""
    key = name.lower()
    return key in _IGNORED or key.startswith(_IGNORED_PREFIXES)


def name_fault(name: str) -> tuple[str, int] | None:
    """Why ``name`` is not an RFC 5322 field name and the index to blame, or None.

    The message names the character, never the name: a "Name: value" typo would echo
    the value, which may be a secret.
    """
    if not name:
        return "empty header field name", 0
    for index, char in enumerate(name):
        if char not in FTEXT:
            return f"character {char!r} not allowed in a header field name", index
    return None


def read_pair(item: object) -> tuple[object, object]:
    """The two members of a ``(name, value)`` pair, read from what the tuple or list holds.

    A subclass that overrides ``__iter__``, ``__len__`` or ``__getitem__`` cannot make the
    builder and ``Mailto`` read different pairs.
    """
    members: tuple[object, ...]
    if isinstance(item, tuple):
        members = tuple.__getitem__(item, slice(None))
    elif isinstance(item, list):
        members = tuple(list.copy(item))
    else:
        raise TypeError("headers must hold (name, value) pairs")
    if tuple.__len__(members) != 2:
        raise TypeError("headers must hold (name, value) pairs")
    return members[0], members[1]
