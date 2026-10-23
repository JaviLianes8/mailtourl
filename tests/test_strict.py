"""Strict mode: the RFC 6068 grammar, with the offset of the first problem."""

from __future__ import annotations

import pytest

from mailtourl import Mailto, MailtoError, parse

VALID = [
    "mailto:",
    "mailto:a@x.example",
    "mailto:a@x.example,b@x.example?cc=c@x.example&bcc=d@x.example",
    "mailto:?to=a@x.example&subject=&body=",
    "mailto:a@x.example?to=b@x.example",
    "mailto:Mike&family@example.org",
    "mailto:a=b&c@x.example",
    "mailto:a@%5B192.0.2.1%5D",
    "mailto:a@%5BIPv6:2001:db8::1%5D",
    "mailto:%22a%20b%22@x.example".replace("%20", "%5C%20"),
    "mailto:%22%22@x.example",
    "mailto:caf%C3%A9@%C3%A9.example",
    "mailto:a@x.example?body=one%0D%0Atwo%09three",
    "mailto:a@x.example?cc=",
    "mailto:a@x.example?X-Custom!$'()*+,;@=v!$'()*+,;:@-._~",
]


@pytest.mark.parametrize("uri", VALID)
def test_valid_uris_pass_and_mean_the_same_as_the_lenient_reading(uri: str) -> None:
    assert parse(uri, strict=True) == parse(uri)


INVALID = [
    ("mailto:a@x.example#frag", 18, "fragment"),
    (" mailto:a@x.example", 0, "not a mailto"),
    ("mailto:a@x.example ", 18, "percent-encoded"),
    ("mailto:a b@x.example", 8, "percent-encoded"),
    ("mailto:a/b@x.example", 8, "percent-encoded"),
    ("mailto:café@x.example", 10, "percent-encoded"),
    ("mailto:a@x.example?subject=a/b", 28, "percent-encoded"),
    ("mailto:a@x.example?subject=a?b", 28, "percent-encoded"),
    ("mailto:a@x.example?subject=a=b", 28, "percent-encoded"),
    ("mailto:a@x.example?sub/ject=a", 22, "percent-encoded"),
    ("mailto:a@x.example?subject=50%", 29, "incomplete"),
    ("mailto:a@x.example?subject=%G0", 27, "incomplete"),
    ("mailto:a@x.example?subject=%C3", 27, "UTF-8"),
    ("mailto:%FF@x.example", 7, "UTF-8"),
    ("mailto:a@x.example?draft", 24, "without '='"),
    ("mailto:a@x.example?", 19, "empty header field"),
    ("mailto:a@x.example?subject=a&&body=b", 29, "empty header field"),
    ("mailto:a@x.example?=v", 19, "field name"),
    ("mailto:a@x.example?a%3Ab=v", 20, "field name"),
    ("mailto:a@x.example?a%20b=v", 20, "field name"),
    ("mailto:a@x.example?caf%C3%A9=v", 22, "field name"),
    ("mailto:a@x.example?subject=a&Subject=b", 29, "repeated"),
    ("mailto:a@x.example?cc=b@x.example&CC=c@x.example", 34, "repeated"),
    ("mailto:a@x.example?body=a%0Ab", 25, "line break"),
    ("mailto:a@x.example?body=a%0D", 25, "line break"),
    ("mailto:a@x.example?body=a%07", 25, "control"),
    ("mailto:a@x.example?subject=a%07", 28, "control"),
    ("mailto:a@x.example?subject=a%09b%7F", 32, "control"),
    ("mailto:a@x.example,", 19, "empty address"),
    ("mailto:a;b@x.example", 8, "not allowed in local part"),
    ("mailto:ax.example", 17, "missing '@'"),
    ("mailto:a@", 9, "empty domain"),
    ("mailto:a..b@x.example", 9, "empty dot-separated"),
    ("mailto:.a@x.example", 7, "empty dot-separated"),
    ("mailto:a@x.example.", 19, "empty dot-separated"),
    ("mailto:a@b@x.example", 10, "not allowed in domain"),
    ("mailto:%22a%20b%22@x.example", 11, "bare whitespace"),
    ("mailto:%22a%22b@x.example", 14, "expected '@'"),
    ("mailto:%22ab@x.example", 22, "unterminated"),
    ("mailto:%22a%5C%01%22@x.example", 11, "quoted-pair"),
    ("mailto:%22a%5C", 11, "quoted-pair"),
    ("mailto:%22a%01%22@x.example", 11, "quoted local part"),
    ("mailto:a(comment)@x.example", 8, "not allowed in local part"),
    ("mailto:a@ex%61mple.com", 11, "domain"),
    ("mailto:a@%5B1.2.3.4", 19, "unterminated domain literal"),
    ("mailto:a@%5Bx%5Cy%5D", 13, "domain literal"),
    ("mailto:a@%5B%C3%A9%5D", 12, "domain literal"),
]


@pytest.mark.parametrize(("uri", "offset", "words"), INVALID)
def test_invalid_uris_raise_with_offset(uri: str, offset: int, words: str) -> None:
    with pytest.raises(MailtoError) as caught:
        parse(uri, strict=True)
    assert words in caught.value.reason
    assert caught.value.offset == offset


def test_every_invalid_uri_but_the_leading_space_parses_leniently() -> None:
    for uri, _, words in INVALID:
        if words != "not a mailto":
            assert isinstance(parse(uri), Mailto), uri


def test_strict_keeps_the_rfc_example_with_both_path_and_to_field() -> None:
    result = parse("mailto:addr1@an.example?to=addr2@an.example", strict=True)
    assert result.to == ("addr1@an.example", "addr2@an.example")


def test_the_error_message_carries_the_offset() -> None:
    with pytest.raises(MailtoError, match=r"at offset 18$"):
        parse("mailto:a@x.example#", strict=True)


def test_strict_rejects_bytes_with_a_type_error() -> None:
    with pytest.raises(TypeError):
        parse(b"mailto:", strict=True)  # type: ignore[arg-type]
