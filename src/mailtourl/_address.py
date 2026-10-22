"""RFC 5322 addr-spec as RFC 6068 section 2 restricts it, with RFC 6532 UTF-8."""

from __future__ import annotations

from ._chars import ADDRESS_SAFE, DTEXT, UNRESERVED, is_atext, is_qtext, is_vchar, plain
from ._errors import MailtoError, quoted


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
                raise MailtoError(f"bad quoted-pair in address {quoted(text)}", index)
            index += 2
            continue
        if char in " \t":
            raise MailtoError(f"bare whitespace in the quoted local part of {quoted(text)}", index)
        if not is_qtext(char):
            raise MailtoError(f"character {char!r} not allowed in the quoted local part", index)
        index += 1
    raise MailtoError(f"unterminated quoted local part in {quoted(text)}", len(text))


def _check_dot_atom(text: str, what: str, start: int) -> None:
    """Raise at the index (counted from ``start``) of the first thing that breaks the rule."""
    if not text:
        raise MailtoError(f"empty {what}", start)
    for index, char in enumerate(text):
        if char == "." and (index == 0 or text[index - 1] == "."):
            raise MailtoError(f"empty dot-separated part in {what} {quoted(text)}", start + index)
        if char != "." and not is_atext(char):
            reason = f"character {char!r} not allowed in {what} {quoted(text)}"
            raise MailtoError(reason, start + index)
    if text.endswith("."):
        raise MailtoError(f"empty dot-separated part in {what} {quoted(text)}", start + len(text))


def split_address(text: str) -> tuple[str, str]:
    """Split an addr-spec into local part and domain; raise MailtoError if it is not one.

    The error's offset is the index in ``text`` of the first thing that breaks the rule.
    """
    if not text:
        raise MailtoError("empty address", 0)
    if text.startswith('"'):
        local = text[: _quoted_end(text)]
        if not text[len(local) :].startswith("@"):
            raise MailtoError(
                f"expected '@' after the quoted local part of {quoted(text)}", len(local)
            )
    else:
        at = text.find("@")
        local = text if at < 0 else text[:at]
        _check_dot_atom(local, "local part", 0)
        if at < 0:
            raise MailtoError(f"missing '@' in address {quoted(text)}", len(text))
    start = len(local) + 1
    domain = text[start:]
    if domain.startswith("[") and domain.endswith("]") and len(domain) >= 2:
        for index, char in enumerate(domain[1:-1], start + 1):
            if char not in DTEXT:
                raise MailtoError(
                    f"character {char!r} not allowed in domain literal {quoted(domain)}", index
                )
    else:
        _check_dot_atom(domain, "domain", start)
    return local, domain


def check_domain(domain: str) -> None:
    """Refuse an ASCII character that a domain name could hold only percent-encoded.

    RFC 6068 section 2 allows percent-encoding in a domain name only for UTF-8, so such a
    character ("&" and "=" too, which a field value must encode) fits no field of a URI.
    Nor does "+": a form decoder reads it as a space in cc or bcc (RFC 6068 section 5).
    """
    if not domain.startswith("["):
        for char in domain:
            writable = char in UNRESERVED or (char in ADDRESS_SAFE and char != "+")
            if char.isascii() and not writable:
                raise MailtoError(f"{char!r} cannot be written in a domain name")


def is_address(text: str) -> bool:
    r"""True when ``text`` is an addr-spec that ``build`` can write into a mailto: URI.

    That is an RFC 5322 addr-spec in the form RFC 6068 section 2 allows: a dot-atom or
    quoted local part (no bare whitespace: use a quoted-pair), "@", then a dot-atom domain
    or a domain literal; no comments, obsolete forms or display names. A domain name may
    not hold any of ``# % & + / = ? ^ ` { | }``, since RFC 6068 allows percent-encoding
    there only for UTF-8 and a form decoder reads a raw ``+`` as a space. Non-ASCII is
    allowed (RFC 6532) except whitespace, controls, invisible formatting characters and
    noncharacters (the guide lists them). A ``text`` that is not a ``str`` raises
    TypeError.

    >>> from mailtourl import is_address
    >>> is_address("jane@example.com"), is_address('"j\\ doe"@[192.0.2.1]')
    (True, True)
    >>> is_address("Jane <jane@example.com>"), is_address("jane@example.com ")
    (False, False)
    >>> is_address("a@x/y.example"), is_address("a/b@x.example")
    (False, True)
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    try:
        check_domain(split_address(plain(text))[1])
    except MailtoError:
        return False
    return True
