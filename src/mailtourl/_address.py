"""RFC 5322 addr-spec as RFC 6068 section 2 restricts it, with RFC 6532 UTF-8."""

from __future__ import annotations

from ._chars import DTEXT, is_atext, is_qtext, is_vchar
from ._errors import MailtoError


def _quoted_end(text: str) -> int:
    """Index just past the closing quote of the quoted-string that starts ``text``."""
    index = 1
    while index < len(text):
        char = text[index]
        if char == '"':
            return index + 1
        if char == "\\":
            # quoted-pair: VCHAR or WSP; an escaped space is how RFC 6068 6.2 writes one.
            if index + 1 >= len(text) or not (
                is_vchar(text[index + 1]) or text[index + 1] in " \t"
            ):
                raise MailtoError(f"bad quoted-pair in address {text[:60]!r}")
            index += 2
            continue
        if char in " \t":
            raise MailtoError(f"bare whitespace in the quoted local part of {text[:60]!r}")
        if not is_qtext(char):
            raise MailtoError(f"character {char!r} not allowed in the quoted local part")
        index += 1
    raise MailtoError(f"unterminated quoted local part in {text[:60]!r}")


def _check_dot_atom(text: str, what: str) -> None:
    if not text:
        raise MailtoError(f"empty {what}")
    for atom in text.split("."):
        if not atom:
            raise MailtoError(f"empty dot-separated part in {what} {text[:60]!r}")
        for char in atom:
            if not is_atext(char):
                raise MailtoError(f"character {char!r} not allowed in {what} {text[:60]!r}")


def split_address(text: str) -> tuple[str, str]:
    """Split an addr-spec into local part and domain; raise MailtoError if it is not one."""
    if not text:
        raise MailtoError("empty address")
    if text.startswith('"'):
        end = _quoted_end(text)
        local, rest = text[:end], text[end:]
        if not rest.startswith("@"):
            raise MailtoError(f"expected '@' after the quoted local part of {text[:60]!r}")
    else:
        at = text.find("@")
        if at < 0:
            raise MailtoError(f"missing '@' in address {text[:60]!r}")
        local, rest = text[:at], text[at:]
        _check_dot_atom(local, "local part")
    domain = rest[1:]
    if domain.startswith("[") and domain.endswith("]") and len(domain) >= 2:
        for char in domain[1:-1]:
            if char not in DTEXT:
                raise MailtoError(
                    f"character {char!r} not allowed in domain literal {domain[:60]!r}"
                )
    else:
        _check_dot_atom(domain, "domain")
    return local, domain


def is_address(text: str) -> bool:
    """True when ``text`` is an addr-spec that a mailto: URI may carry (RFC 6068 section 2).

    Quoted local parts are allowed, without bare whitespace (use a quoted-pair); comments,
    obsolete forms and display names are not. Non-ASCII text is allowed per RFC 6532.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    try:
        split_address(text)
    except MailtoError:
        return False
    return True
