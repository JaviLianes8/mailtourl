"""Character classes from RFC 3986, RFC 5322, RFC 6068 and RFC 6532."""

from __future__ import annotations

import string
import unicodedata

_ALNUM = string.ascii_letters + string.digits
HEX = frozenset(string.hexdigits)

# RFC 3986 section 2.3 and 2.2.
UNRESERVED = frozenset(_ALNUM + "-._~")
SUB_DELIMS = frozenset("!$&'()*+,;=")
# RFC 3986 pchar: what may stay raw in the address part (RFC 6068 erratum 7919).
PCHAR = UNRESERVED | SUB_DELIMS | frozenset(":@")
# RFC 6068 qchar without pct-encoded: what may stay raw in a field name or value.
SOME_DELIMS = frozenset("!$'()*+,;:@")
QCHAR = UNRESERVED | SOME_DELIMS

# What the builder leaves raw. "+" is encoded in fields because HTML form decoders read it
# as a space (RFC 6068 section 5); "," is encoded inside addresses because it separates
# them; "&", ";" and "=" are encoded in addresses too, as the RFC text before erratum 7919
# required, so the output is valid under either reading.
ADDRESS_SAFE = "!$'()*+:"
FIELD_SAFE = "!$'()*,;:@"

# RFC 5322 atext, extended to UTF-8 by RFC 6532 section 3.2.
_ATEXT = frozenset(_ALNUM + "!#$%&'*+-/=?^_`{|}~")
# RFC 5322 qtext: printable ASCII except "\" and the double quote, plus RFC 6532 UTF-8.
_QTEXT = frozenset(chr(c) for c in range(33, 127)) - frozenset('\\"')
# RFC 6068 dtext-no-obs: printable ASCII except "[", "]" and "\"; no UTF-8 here.
DTEXT = frozenset(chr(c) for c in range(33, 127)) - frozenset("[]\\")
# RFC 5322 ftext: printable ASCII except ":"; RFC 6532 keeps field names ASCII.
FTEXT = frozenset(chr(c) for c in range(33, 127)) - frozenset(":")


# Every character str.splitlines breaks on, plus NUL: in a header each one can end the
# line (or truncate it in C-based clients), so all are refused outside the body.
LINE_BREAKS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029\x00")
# Unicode categories that are whitespace, controls or invisible formatting: RFC 6068
# section 2 forbids whitespace in an address, and these would hide what a reader sees.
_HIDDEN = frozenset({"Cc", "Cf", "Cs", "Zs", "Zl", "Zp"})
# The joiners are formatting characters that IDNA allows in context.
_JOINERS = frozenset("\u200c\u200d")


def is_utf8_text(char: str) -> bool:
    """A visible non-ASCII code point (RFC 6532 UTF8-non-ascii, less hidden characters)."""
    code = ord(char)
    if code < 0x80 or 0xFDD0 <= code <= 0xFDEF or code & 0xFFFE == 0xFFFE:
        return False
    return char in _JOINERS or unicodedata.category(char) not in _HIDDEN


def is_atext(char: str) -> bool:
    return char in _ATEXT or is_utf8_text(char)


def is_qtext(char: str) -> bool:
    return char in _QTEXT or is_utf8_text(char)


def is_vchar(char: str) -> bool:
    """RFC 5234 VCHAR, extended to UTF-8 by RFC 6532."""
    return 33 <= ord(char) <= 126 or is_utf8_text(char)


def is_control(char: str) -> bool:
    """A C0 control, DEL, a C1 control or a line or paragraph separator."""
    code = ord(char)
    return code < 0x20 or 0x7F <= code <= 0x9F or char in LINE_BREAKS
