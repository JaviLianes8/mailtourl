"""Offsets point at the first character that breaks a rule, in the order of the text."""

from __future__ import annotations

import pytest

from mailtourl import MailtoError, parse

STRICT = [
    # An address or field name that breaks the grammar: the character, not where it starts.
    ("mailto:j%20d@x.example", 8),
    ("mailto:ab%20@x.example", 9),
    ("mailto:a..b@x.example", 9),
    ("mailto:.a@x.example", 7),
    ("mailto:a.@x.example", 9),
    ("mailto:a@x%5Cy.example", 10),
    ("mailto:%22a%22b@x.example", 14),
    ("mailto:%22a%20b%22@x.example", 11),
    ("mailto:%22ab@x.example", 22),
    ("mailto:?cc=ok@x.example,c..d@x.example", 26),
    ("mailto:a@x.example?cc=b@x..example", 26),
    ("mailto:a@", 9),
    ("mailto:abc", 10),
    ("mailto:a%20b", 8),
    ("mailto:a@%5B1.2%5Cx%5D", 15),
    ("mailto:?cc=a@%5B192.0.2.1", 25),
    ("mailto:a@%5B192.0.2.1%5Dx", 24),
    ("mailto:a@%5B1.2.3.4%5D%5D", 22),
    ("mailto:a@%5B", 12),
    ("mailto:a@%5B1.2%20", 15),
    ("mailto:a@%5B1.2%09", 15),
    ("mailto:ab%3C", 9),
    ("mailto:ab%20", 9),
    ("mailto:a.b%3C", 10),
    ("mailto:?Xyz%20Y=1", 11),
    ("mailto:a@x.example?a%20b=x", 20),
    ("mailto:a@x.example?Fr%3Aom=x", 21),
    ("mailto:?%41%3A=1", 11),
    ("mailto:?%41b%20=1", 12),
    ("mailto:a@x.example?X-%41%3A=1", 24),
    ("mailto:?=x", 8),
    # A part that breaks several rules: the first one in the text.
    ("mailto:a@x.example?subject=%ZZ<", 27),
    ("mailto:a@x.example?subject=%FF<", 27),
    ("mailto:a@x.example?subject=%C3<", 27),
    ("mailto:a@x.example?sub<ject", 22),
    ("mailto:a<b@x.example#f", 8),
    ("mailto:a@x.example?subject=%0A#f", 27),
    ("mailto:a@x.example?subject=%01%0A", 27),
    ("mailto:a@x%2E%2Eexample", 10),
    ("mailto:a@x.example?body=%01<", 24),
    ("mailto:a%0A<@x.example", 8),
    # Bytes that are not UTF-8 do not hide an earlier problem in the same part.
    ("mailto:a@%5B1%5Dx%FF", 16),
    ("mailto:a@%5B%5Dz%FF", 15),
    ("mailto:a@%5B1%20%FF%5D", 13),
    ("mailto:a@%5B%E2%80%8B%FF%5D", 12),
    ("mailto:a%20b@x%FF", 8),
    ("mailto:?subject=a%01%FF", 17),
    ("mailto:?subject=%0A%FF", 16),
    ("mailto:?body=%0A%FF", 13),
    ("mailto:?X%20Y%FF=1", 9),
    ("mailto:a@%5B1%FF", 13),
    # Strict body offsets skip the escapes before the problem.
    ("mailto:?body=%41%00", 16),
    ("mailto:?body=caf%C3%A9%0A", 22),
]


@pytest.mark.parametrize(("uri", "offset"), STRICT)
def test_strict_points_at_the_first_offending_character(uri: str, offset: int) -> None:
    with pytest.raises(MailtoError) as caught:
        parse(uri, strict=True)
    assert caught.value.offset == offset, caught.value.reason


UTF8_HIDES = [
    ("mailto:a@%5B1%5Dx%FF", "text after the domain literal"),
    ("mailto:a@%5B1%20%FF%5D", "character ' ' not allowed in domain literal"),
    ("mailto:a@%5B%E2%80%8B%FF%5D", "not allowed in domain literal"),
    ("mailto:a%20b@x%FF", "character ' ' not allowed in local part"),
    ("mailto:?subject=a%01%FF", "control character"),
    ("mailto:?subject=%0A%FF", "header injection"),
    ("mailto:?body=%0A%FF", "body line break"),
    ("mailto:?X%20Y%FF=1", "header field name"),
]


@pytest.mark.parametrize(("uri", "reason"), UTF8_HIDES)
def test_bytes_that_are_not_utf8_do_not_hide_an_earlier_problem(uri: str, reason: str) -> None:
    with pytest.raises(MailtoError, match=reason):
        parse(uri, strict=True)


@pytest.mark.parametrize(
    "uri", ["mailto:a@%5B1%FF", "mailto:abc%FF", "mailto:a.%FF@x", "mailto:?X%FF=1", "mailto:%FF"]
)
def test_bytes_that_are_not_utf8_win_a_tie_with_what_they_cut_short(uri: str) -> None:
    with pytest.raises(MailtoError, match="not UTF-8") as caught:
        parse(uri, strict=True)
    assert caught.value.offset == uri.index("%FF")


def test_the_raw_character_rule_wins_a_tie() -> None:
    with pytest.raises(MailtoError, match="'<' must be percent-encoded") as caught:
        parse("mailto:a<b@x.example", strict=True)
    assert caught.value.offset == 8


def test_a_malformed_field_name_names_the_character_not_the_name() -> None:
    with pytest.raises(MailtoError) as caught:
        parse("mailto:?Authorization:%20Bearer%20abc=1", strict=True)
    assert caught.value.reason == "character ':' not allowed in a header field name"
    assert caught.value.offset == len("mailto:?Authorization")
    assert "Bearer" not in str(caught.value)


LENIENT = [
    # Overlong leads C0 and C1 and the leads F5 to F7 are one replacement character each.
    ("mailto:?subject=%C0%80%0A", 22),
    ("mailto:?subject=%C1%BF%0A", 22),
    ("mailto:?subject=%F5%80%80%80%0A", 28),
    ("mailto:?subject=%F7%BF%BF%BF%0A", 28),
    # A removed tab or newline right before the problem is counted.
    ("mailto:?subject=\t%0A", 17),
    ("mailto:?subject=ab\n%0D", 19),
]


@pytest.mark.parametrize(("uri", "offset"), LENIENT)
def test_lenient_offsets_count_what_was_decoded_or_removed(uri: str, offset: int) -> None:
    with pytest.raises(MailtoError) as caught:
        parse(uri)
    assert caught.value.offset == offset
