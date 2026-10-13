"""Header field rules from RFC 6068 sections 3 and 4."""

from __future__ import annotations

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
