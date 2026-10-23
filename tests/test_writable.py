"""is_address means build can write it, and safe() always gives a value to_uri can write."""

from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Any

import pytest

from mailtourl import Mailto, MailtoError, build, is_address, parse

NEEDS_AN_ESCAPE = "#%&/=?^`{|}"


@pytest.mark.parametrize("char", NEEDS_AN_ESCAPE)
def test_a_domain_char_that_needs_an_ascii_escape_is_not_an_address(char: str) -> None:
    text = f"a@x{char}y.example"
    assert not is_address(text)
    with pytest.raises(MailtoError, match="cannot be written in a domain name"):
        build(text)
    assert is_address(f"a{char}b@x.example")
    assert parse(build(f"a{char}b@x.example"), strict=True).to == (f"a{char}b@x.example",)


def test_is_address_agrees_with_build_on_random_candidates() -> None:
    rng = random.Random(5322)
    pieces = [*"aZ9.-_~!$'*+#%&/=?^`{|}@\"\\ []:", "é", "x.example", "[192.0.2.1]", "\u200b"]
    for _ in range(20000):
        text = "".join(rng.choice(pieces) for _ in range(rng.randrange(1, 9)))
        try:
            build(text)
        except MailtoError:
            assert not is_address(text), text
        else:
            assert is_address(text), text


def test_strict_takes_an_ampersand_domain_in_the_path_but_safe_drops_it() -> None:
    # Erratum 7919 lets "&" and "=" stay raw in the path; build never writes them there.
    mail = parse("mailto:a@x&y.example,b@x.example", strict=True)
    assert mail.to == ("a@x&y.example", "b@x.example")
    with pytest.raises(MailtoError, match="'&' cannot be written"):
        mail.to_uri()
    assert mail.safe().to_uri() == "mailto:b@x.example"


@pytest.mark.parametrize(
    ("uri", "kept"),
    [
        ("mailto:a@x.example?subject=%01", Mailto("a@x.example")),
        ("mailto:a@x.example?body=%00", Mailto("a@x.example")),
        ("mailto:a@x.example?body=a%0D%0Ab", Mailto("a@x.example", body="a\r\nb")),
        ("mailto:a@x.example?Keywords=%7F&subject=s", Mailto("a@x.example", subject="s")),
        ("mailto:?Keywords=a&keywords=b", Mailto(headers=[("Keywords", "a")])),
        ("mailto:?Keywords=%01&keywords=b", Mailto(headers=[("keywords", "b")])),
        ("mailto:?to=a@x%2Fy.example", Mailto()),
        ("mailto:a@x#y.example", Mailto("a@x")),
    ],
)
def test_safe_keeps_only_what_to_uri_can_write(uri: str, kept: Mailto) -> None:
    safe = parse(uri).safe()
    assert safe == kept
    assert parse(safe.to_uri()) == kept


def test_safe_drops_allowed_headers_that_build_refuses() -> None:
    mail = Mailto(headers=[("From", "x@y.example"), ("Subject", "s"), ("X A", "1"), ("K", "v")])
    assert mail.safe(allow=["from", "subject", "x a", "k"]).headers == (("K", "v"),)
    strict = parse("mailto:a@x.example?From=b@x.example", strict=True)
    with pytest.raises(MailtoError, match="MUST ignore"):
        strict.to_uri()
    assert strict.safe(allow=["from"]).to_uri() == "mailto:a@x.example"


TOKENS = [*"aZ@.,;=&?#%+ \t", "%0", "%00", "%01", "%0D%0A", "%0A", "%7F", "%C2%80", "%FF"]
TOKENS += ["%2F", "%40", "%22", "%5C", "x.example", "subject=", "body=", "Keywords=", "keywords="]
TOKENS += ["cc=", "bcc=", "From=", "X-A=", "\x01", "é", "\u200b", "\ufffd", "%E2%80%8B"]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_safe_always_builds_whatever_the_default_mode_reads(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(4000):
        uri = "mailto:" + "".join(rng.choice(TOKENS) for _ in range(rng.randrange(20)))
        try:
            mail = parse(uri)
        except MailtoError:
            continue
        for allow in (("keywords",), ("keywords", "x-a", "from")):
            built = mail.safe(allow=allow).to_uri()
            assert parse(built, strict=True).to_uri() == built, uri


class LyingIter(str):
    def __iter__(self) -> Iterator[str]:
        return iter("")


class LyingLen(LyingIter):
    def __len__(self) -> int:
        return 0


@pytest.mark.parametrize("kind", [LyingIter, LyingLen])
def test_build_reads_a_str_subclass_as_plain_str(kind: type[str]) -> None:
    hostile = kind("x\r\nBcc: e@v.example")
    cases: list[dict[str, Any]] = [
        {"subject": hostile},
        {"body": kind("a\x00b")},
        {"headers": {"X-A": hostile}},
        {"headers": {kind("X\r\nBcc"): "v"}},
        {"to": hostile},
        {"cc": [hostile]},
    ]
    for arguments in cases:
        with pytest.raises(MailtoError):
            build(**arguments)
    assert build(kind("a@x.example"), subject=kind("s")) == "mailto:a@x.example?subject=s"
    assert not is_address(kind("a b@x.example"))
    with pytest.raises(MailtoError, match="header injection"):
        parse(kind("mailto:?subject=%0A"))
    assert parse(kind("mailto:a@x.example")).to == ("a@x.example",)
