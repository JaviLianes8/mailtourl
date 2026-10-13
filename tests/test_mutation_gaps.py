"""Cases a mutation run showed were missing: each one fails if its guard is removed."""

from __future__ import annotations

import io

import pytest

from mailtourl import MailtoError, build, is_address, parse
from mailtourl._cli import main


def test_is_address_refuses_any_non_string() -> None:
    with pytest.raises(TypeError, match="expected str"):
        is_address(5)  # type: ignore[arg-type]


def test_the_unit_separator_is_a_control_character() -> None:
    with pytest.raises(MailtoError, match="control character"):
        build(subject="a\x1fb")
    with pytest.raises(MailtoError, match="control character"):
        parse("mailto:?subject=a%1Fb", strict=True)


@pytest.mark.parametrize(
    ("uri", "offset"),
    [("mailto:?subject=%0G", 16), ("mailto:?subject=%41%G1", 19), ("mailto:?subject=%41%4", 19)],
)
def test_every_escape_needs_two_hex_digits(uri: str, offset: int) -> None:
    with pytest.raises(MailtoError, match="incomplete") as caught:
        parse(uri, strict=True)
    assert caught.value.offset == offset


def test_an_escaped_tilde_in_a_domain_is_an_ascii_escape() -> None:
    with pytest.raises(MailtoError, match="domain name"):
        parse("mailto:a@x%7Ey.example", strict=True)


def test_a_raw_at_sign_inside_quotes_does_not_hide_the_domain() -> None:
    assert parse("mailto:%22a@%41%22@x.example", strict=True).to == ('"a@A"@x.example',)


def test_ignored_fields_are_refused_in_any_case() -> None:
    with pytest.raises(MailtoError, match="MUST ignore"):
        build(headers={"FROM": "x@y.example"})


@pytest.mark.parametrize(
    "call",
    [
        lambda: build(subject=1),  # type: ignore[arg-type]
        lambda: build(body=1),  # type: ignore[arg-type]
    ],
)
def test_build_names_the_wrong_type(call: object) -> None:
    with pytest.raises(TypeError, match="must be str, got int"):
        call()  # type: ignore[operator]


def test_strict_parse_on_the_command_line_strips_the_input_line() -> None:
    out = io.StringIO()
    status = main(["parse", "--strict"], stdin=io.StringIO("mailto:a@x.example\n"), stdout=out)
    assert status == 0
