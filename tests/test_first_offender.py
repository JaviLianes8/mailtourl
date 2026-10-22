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
    ("mailto:?Xyz%20Y=1", 11),
    ("mailto:a@x.example?a%20b=x", 20),
    ("mailto:a@x.example?Fr%3Aom=x", 21),
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
    # Strict body offsets skip the escapes before the problem.
    ("mailto:?body=%41%00", 16),
    ("mailto:?body=caf%C3%A9%0A", 22),
]


@pytest.mark.parametrize(("uri", "offset"), STRICT)
def test_strict_points_at_the_first_offending_character(uri: str, offset: int) -> None:
    with pytest.raises(MailtoError) as caught:
        parse(uri, strict=True)
    assert caught.value.offset == offset, caught.value.reason


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
