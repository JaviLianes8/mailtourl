"""Regression tests for the findings of the independent review."""

from __future__ import annotations

import pytest

from mailtourl import Mailto, MailtoError, build, is_address, parse

LS = chr(0x2028)
# Whitespace, controls, invisible formatting and noncharacters, as code points.
HIDDEN = (0x3000, 0x2028, 0x85, 0x200B, 0xA0, 0xFDD0, 0xFFFF, 0x2003)
# Every character str.splitlines breaks on, plus NUL, percent-encoded.
BREAKS = ["%0A", "%0D", "%0B", "%0C", "%1C", "%1D", "%1E", "%C2%85", "%E2%80%A8", "%E2%80%A9"]


@pytest.mark.parametrize("brk", [*BREAKS, "%00"])
@pytest.mark.parametrize("strict", [False, True])
def test_every_line_break_in_a_header_is_injection(brk: str, strict: bool) -> None:
    for uri in (
        f"mailto:a@x.example?subject=Hi{brk}Bcc:%20s@e.example",
        f"mailto:a@x.example?K{brk}x=v",
        f"mailto:a{brk}@x.example",
        f"mailto:?cc=c@x.example{brk}",
    ):
        with pytest.raises(MailtoError, match="header injection"):
            parse(uri, strict=strict)


@pytest.mark.parametrize("char", [chr(c) for c in (0x0B, 0x0C, 0x1C, 0x85, 0x2028, 0x2029, 0x9B)])
def test_build_refuses_unicode_line_breaks_and_c1_controls_in_headers(char: str) -> None:
    with pytest.raises(MailtoError, match="control character"):
        build("a@x.example", subject=f"hi{char}Bcc: e@x.example")
    with pytest.raises(MailtoError, match="control character"):
        build(headers={"K": char})


def test_the_body_may_hold_unicode_separators_but_not_c1_controls() -> None:
    uri = build(body=f"a{LS}b")
    assert parse(uri, strict=True).body == f"a{LS}b"
    with pytest.raises(MailtoError):
        build(body="a\x85b")
    with pytest.raises(MailtoError, match="control"):
        parse("mailto:?body=a%C2%85b", strict=True)


@pytest.mark.parametrize(
    "name", ["%C2%A0bcc", "%E3%80%80bcc", "bcc%E2%80%83", "%20%20BCC%20", "%1Fbcc"]
)
def test_unicode_padding_cannot_hide_a_bcc(name: str) -> None:
    assert parse(f"mailto:a@x.example?{name}=s@e.example").bcc == ("s@e.example",)


@pytest.mark.parametrize("name", ["Bcc:spy@evil.example", "%07bcc", "caf%C3%A9", "a%20b"])
def test_lenient_mode_drops_fields_whose_name_is_not_a_field_name(name: str) -> None:
    assert parse(f"mailto:a@x.example?{name}=1") == Mailto("a@x.example")


def test_strict_mode_refuses_a_percent_encoded_separator() -> None:
    with pytest.raises(MailtoError, match="'@' before the domain") as caught:
        parse("mailto:joe%40ex%61mple.com", strict=True)
    assert caught.value.offset == 7
    assert parse("mailto:joe%40example.com").to == ("joe@example.com",)


@pytest.mark.parametrize(
    ("uri", "offset"),
    [
        ("mailto:a@x?body=xxxxxxxxxx%0Ab", 26),
        ("mailto:a@x?subject=caf%C3%A9%0A", 28),
        ("mailto:a@x?subject=caf%C3%A9x%0A", 29),
        ("mailto:a@x?subject=50%%0A", 22),
        ("mailto:a@x?subject=a%07", 20),
    ],
)
def test_offsets_point_at_the_offending_character(uri: str, offset: int) -> None:
    with pytest.raises(MailtoError) as caught:
        parse(uri, strict="50%" not in uri)
    assert caught.value.offset == offset


def test_safe_drops_recipients_that_are_not_addresses() -> None:
    mail = parse("mailto:x@a.example%2Cspy@evil.example,ok@a.example?cc=Evil%20%3Ce@x%3E")
    assert mail.to == ("x@a.example,spy@evil.example", "ok@a.example")
    assert mail.safe() == Mailto("ok@a.example")


@pytest.mark.parametrize(
    "address",
    [f"{c}@x" if i % 2 else f"a{c}b@x.example" for i, c in enumerate(map(chr, HIDDEN))],
)
def test_hidden_unicode_is_not_an_address(address: str) -> None:
    assert not is_address(address)


def test_joiners_and_visible_unicode_stay_valid() -> None:
    assert is_address(f"a{chr(0x200D)}b@x.example") and is_address("é@x.example")


@pytest.mark.parametrize(
    "call",
    [
        lambda: Mailto(headers=[1]),  # type: ignore[list-item]
        lambda: build(headers=[1]),  # type: ignore[list-item]
    ],
)
def test_a_non_pair_header_names_the_problem(call: object) -> None:
    with pytest.raises(TypeError, match=r"\(name, value\) pairs"):
        call()  # type: ignore[operator]


@pytest.mark.parametrize(
    "call",
    [
        lambda: Mailto(b"a@x"),  # type: ignore[arg-type]
        lambda: build(b"a@x"),  # type: ignore[arg-type]
        lambda: build(cc=bytearray(b"a@x")),  # type: ignore[arg-type]
    ],
)
def test_bytes_are_named_in_the_type_error(call: object) -> None:
    with pytest.raises(TypeError, match="got bytes"):
        call()  # type: ignore[operator]


def test_list_pairs_are_accepted_like_tuples() -> None:
    assert Mailto(headers=[["K", "v"]]).headers == (("K", "v"),)  # type: ignore[list-item]


def test_error_messages_are_bounded() -> None:
    with pytest.raises(MailtoError) as caught:
        parse("mailto:" + "a" * 100_000, strict=True)
    assert len(str(caught.value)) < 200
