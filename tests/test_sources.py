"""Check the library against the pinned RFC 6068, 3986, 5322, 6532 and WHATWG URL texts.

The files are read from tests/upstream (URL, size and sha256 in MANIFEST.json); these
tests skip until `python scripts/fetch_upstream.py` has fetched them.
"""

from __future__ import annotations

import re
import string

import pytest

from mailtourl import Mailto, MailtoError, build, parse
from mailtourl._chars import (
    DTEXT,
    FTEXT,
    PCHAR,
    QCHAR,
    SOME_DELIMS,
    SUB_DELIMS,
    UNRESERVED,
    is_atext,
    is_qtext,
)

_ALNUM = set(string.ascii_letters + string.digits)


def _examples(rfc6068: str) -> list[str]:
    """Every <mailto:...> in the RFC, joined across line breaks (RFC 3986 appendix C)."""
    return [re.sub(r"\s+", "", found) for found in re.findall(r"<(mailto:[^<>]*)>", rfc6068)]


def _quoted(rule: str) -> set[str]:
    return set(re.findall(r'"(.)"', rule))


def _ranges(rule: str) -> set[str]:
    chars: set[str] = set()
    for low, high in re.findall(r"%d(\d+)(?:-(\d+))?", rule):
        chars |= {chr(code) for code in range(int(low), int(high or low) + 1)}
    return chars


def test_the_examples_parse_strictly_and_rebuild_byte_for_byte(rfc6068: str) -> None:
    examples = _examples(rfc6068)
    assert len(examples) == 22
    wrong = "mailto:joe@example.com?cc=bob@example.com?body=hello"
    equivalent = {"mailto:?to=addr1@an.example,addr2@an.example"}
    equivalent.add("mailto:addr1@an.example?to=addr2@an.example")
    for example in examples:
        if example == wrong:
            continue
        mail = parse(example, strict=True)
        assert mail.to_uri() == example or example in equivalent, example
    assert len({parse(example) for example in equivalent}) == 1


def test_the_example_marked_wrong_fails_strict_parsing(rfc6068: str) -> None:
    assert "<mailto:joe@example.com?cc=bob@example.com?body=hello> ; WRONG!" in rfc6068
    with pytest.raises(MailtoError, match="'\\?' must be percent-encoded"):
        parse("mailto:joe@example.com?cc=bob@example.com?body=hello", strict=True)


def test_the_complicated_addresses_of_section_6_2(rfc6068: str) -> None:
    pairs = re.findall(r"Email address: (.+?); corresponding\s+'mailto' URI:\s*<([^>]+)>", rfc6068)
    assert len(pairs) == 3
    for address, uri in pairs:
        assert parse(uri, strict=True).to == (address,)
        assert build(address) == uri


def test_the_addresses_named_in_the_prose(rfc6068: str) -> None:
    pairs = re.findall(r'(?:address|mail to) "([^"]+)"[^<"]*<(mailto:[^>]+)>', rfc6068)
    assert [address for address, _ in pairs] == [
        "gorby%kremvax@example.com",
        "unlikely?address@example.com",
        "Mike&family@example.org",
    ]
    for address, uri in pairs:
        assert parse(uri, strict=True).to[0] == address


def test_the_two_line_body_and_the_html_example(rfc6068: str) -> None:
    body = next(e for e in _examples(rfc6068) if "%0D%0A" in e)
    assert parse(body, strict=True).body == "send current-issue\r\nsend index"
    href = re.findall(r'href="([^"]+)"', rfc6068)[0]
    # The HTML example escapes "&" as "&amp;"; unescaped it is an ordinary URI.
    assert parse(href.replace("&amp;", "&"), strict=True) == Mailto(
        "joe@an.example", cc="bob@an.example", body="hello"
    )


def test_the_encoded_word_subject_matches_the_composed_message(rfc6068: str) -> None:
    subject = re.findall(r"^      Subject: (=\?utf-8\?.+)$", rfc6068, flags=re.MULTILINE)[0]
    uri = next(e for e in _examples(rfc6068) if "%3Futf-8" in e)
    assert parse(uri, strict=True).subject == subject


def test_the_natto_domain_converts_to_the_a_label_in_the_example(rfc6068: str) -> None:
    to_line = re.findall(r"^      To: (user@xn--.+)$", rfc6068, flags=re.MULTILINE)[0]
    uri = next(e for e in _examples(rfc6068) if "NATTO" in e)
    local, domain = parse(uri, strict=True).to[0].split("@")
    assert f"{local}@{domain.encode('idna').decode()}" == to_line


def test_qchar_and_some_delims_match_the_abnf(rfc6068: str) -> None:
    rule = rfc6068.split("some-delims  =", 1)[1].split("<addr-spec>", 1)[0]
    assert _quoted(rule) == set(SOME_DELIMS)
    assert QCHAR == UNRESERVED | SOME_DELIMS
    dtext = rfc6068.split("dtext-no-obs =", 1)[1].split("qchar", 1)[0]
    assert _ranges(dtext) == set(DTEXT)


def test_uri_character_classes_match_rfc_3986(rfc3986: str) -> None:
    unreserved = re.findall(r"^   unreserved    = (.+)$", rfc3986, flags=re.MULTILINE)[0]
    assert _quoted(unreserved) | _ALNUM == set(UNRESERVED)
    sub_delims = rfc3986.split("   sub-delims    =", 1)[1].split("Appendix B", 1)[0]
    assert _quoted(sub_delims) == set(SUB_DELIMS)
    assert UNRESERVED | SUB_DELIMS | {":", "@"} == PCHAR


def test_address_classes_match_rfc_5322_and_rfc_6532(rfc5322: str, rfc6532: str) -> None:
    atext = rfc5322.split("   atext           =", 1)[1].split("atom   ", 1)[0]
    expected = _quoted(atext) | _ALNUM
    assert {chr(c) for c in range(128) if is_atext(chr(c))} == expected
    qtext = rfc5322.split("   qtext           =", 1)[1].split("obs-qtext", 1)[0]
    assert {chr(c) for c in range(128) if is_qtext(chr(c))} == _ranges(qtext)
    ftext = rfc5322.split("   ftext           =", 1)[1].split(';  ":"', 1)[0]
    assert _ranges(ftext) == set(FTEXT)
    for rule in ("atext", "qtext", "dtext"):
        assert re.search(rf"^   {rule} +=/  UTF8-non-ascii$", rfc6532, flags=re.MULTILINE)
    assert is_atext("é") and is_qtext("納")
    assert "header field names are not on this list" in rfc6532


def test_field_values_leave_raw_exactly_the_qchar_minus_plus(rfc6068: str) -> None:
    rule = rfc6068.split("some-delims  =", 1)[1].split("<addr-spec>", 1)[0]
    raw = _quoted(rule) | _ALNUM | set("-._~")
    for code in range(0x20, 0x7F):
        char = chr(code)
        encoded = build(subject=char).removeprefix("mailto:?subject=")
        assert (encoded == char) == (char in raw - {"+"}), repr(char)


def test_browser_preprocessing_matches_the_url_standard(url_standard: str) -> None:
    assert "Remove any leading and trailing <a>C0 control or space</a>" in url_standard
    assert "Remove all <a>ASCII tab or newline</a> from <var>input</var>." in url_standard
    controls = "".join(chr(code) for code in range(0x21))
    uri = f"{controls}mailto:a@x.\texample?subject=h\ni\r{controls}"
    assert parse(uri) == Mailto("a@x.example", subject="hi")


def test_built_uris_hold_nothing_a_browser_would_re_encode(url_standard: str) -> None:
    rule = url_standard.split("<dfn>query percent-encode set</dfn>", 1)[1].split("<p", 1)[0]
    query_set = {chr(int(code, 16)) for code in re.findall(r"U\+([0-9A-F]{4})", rule)}
    assert query_set == {" ", '"', "#", "<", ">"}
    values = ["\t", *(chr(code) for code in range(0x20, 0x300) if code != 0x7F), "\U0001f600"]
    for value in values:
        uri = build("a@x.example", subject=value, body=value, headers={"X-Value": value})
        assert all(0x20 < ord(char) <= 0x7E and char not in query_set for char in uri), value
