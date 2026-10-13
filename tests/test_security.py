"""Header injection, smuggled recipients and the header safety helper."""

from __future__ import annotations

import pytest

from mailtourl import Mailto, MailtoError, build, parse

INJECTIONS = [
    "mailto:a@x.example?subject=Hi%0D%0ABcc:%20spy@evil.example",
    "mailto:a@x.example?subject=Hi%0ABcc:%20spy@evil.example",
    "mailto:a@x.example?subject=Hi%0D",
    "mailto:a@x.example?In-Reply-To=x%0D%0AFrom:%20boss@x.example",
    "mailto:a@x.example?X%0D%0ABcc=spy@evil.example",
    "mailto:a@x.example%0D%0ABcc:spy@evil.example",
    "mailto:?cc=c@x.example%0A",
    "mailto:?subject=a%00b",
]


@pytest.mark.parametrize("uri", INJECTIONS)
@pytest.mark.parametrize("strict", [False, True])
def test_a_line_break_or_nul_outside_the_body_raises_in_every_mode(uri: str, strict: bool) -> None:
    with pytest.raises(MailtoError) as caught:
        parse(uri, strict=strict)
    assert caught.value.offset is not None


def test_the_injection_error_points_at_the_field() -> None:
    uri = "  mailto:a@x.example?subject=Hi%0D%0ABcc:x"
    with pytest.raises(MailtoError) as caught:
        parse(uri)
    assert caught.value.offset == uri.index("%0D")
    assert "header injection" in str(caught.value)


def test_line_breaks_are_fine_in_the_body() -> None:
    assert parse("mailto:a@x.example?body=one%0D%0Atwo").body == "one\r\ntwo"


def test_raw_newlines_are_removed_like_a_browser_does_not_injected() -> None:
    result = parse("mailto:a@x.example?subject=Hi\r\nBcc:%20spy@evil.example")
    assert result.subject == "HiBcc: spy@evil.example"
    assert result.bcc == ()


@pytest.mark.parametrize("name", ["bcc", "BCC", "%62cc", "%42%43%43", "%20bcc", "bcc%09"])
def test_an_encoded_or_padded_bcc_name_still_lands_in_bcc(name: str) -> None:
    result = parse(f"mailto:a@x.example?{name}=spy@evil.example")
    assert result.bcc == ("spy@evil.example",)
    assert result.headers == ()


def test_safe_keeps_recipients_subject_body_and_keywords_only() -> None:
    mail = parse(
        "mailto:a@x.example?cc=c@x.example&subject=s&body=b&Keywords=k"
        "&From=boss@x.example&Content-Type=text/html&X-Custom=1"
    )
    assert mail.safe() == Mailto(
        "a@x.example", cc="c@x.example", subject="s", body="b", headers=[("Keywords", "k")]
    )


def test_safe_accepts_a_wider_allow_list_ignoring_case() -> None:
    mail = Mailto(headers=[("In-Reply-To", "<i@h>"), ("X-A", "1"), ("Keywords", "k")])
    assert mail.safe(["in-reply-to"]).headers == (("In-Reply-To", "<i@h>"),)
    assert mail.safe("X-a").headers == (("X-A", "1"),)
    assert mail.safe(()).headers == ()


@pytest.mark.parametrize(
    "name",
    [
        "From",
        "sender",
        "Reply-To",
        "Date",
        "Apparently-To",
        "Resent-From",
        "Received",
        "Return-Path",
        "MIME-Version",
        "Content-Transfer-Encoding",
    ],
)
def test_build_refuses_fields_rfc_6068_says_clients_must_ignore(name: str) -> None:
    with pytest.raises(MailtoError, match="MUST ignore"):
        build("a@x.example", headers={name: "x"})


@pytest.mark.parametrize("value", ["a\r\nBcc: x@y.example", "a\nb", "a\rb", "a\x00b", "a\x7fb"])
def test_build_refuses_controls_in_subject_and_headers(value: str) -> None:
    with pytest.raises(MailtoError, match="control character"):
        build("a@x.example", subject=value)
    with pytest.raises(MailtoError, match="control character"):
        build("a@x.example", headers={"X-Test": value})


def test_build_refuses_a_control_in_a_header_name() -> None:
    with pytest.raises(MailtoError):
        build(headers={"X\r\nBcc": "y"})


def test_build_keeps_a_tab_in_a_subject() -> None:
    assert build(subject="a\tb") == "mailto:?subject=a%09b"


def test_build_refuses_a_nul_in_the_body() -> None:
    with pytest.raises(MailtoError):
        build(body="a\x00b")
