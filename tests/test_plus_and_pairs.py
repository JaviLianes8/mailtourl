"""A "+" written into the query, header pairs read one way, and the allow list of safe()."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest

from mailtourl import Mailto, MailtoError, build, is_address, parse


def test_a_plus_in_a_cc_or_bcc_address_is_encoded() -> None:
    uri = build("bill+ietf@example.org", cc="bill+ietf@example.org", bcc="x+y@example.org")
    assert uri == "mailto:bill+ietf@example.org?cc=bill%2Bietf@example.org&bcc=x%2By@example.org"
    # A form decoder reads "+" as a space (RFC 6068 section 5): it must see none.
    assert parse_qsl(urlsplit(uri).query) == [
        ("cc", "bill+ietf@example.org"),
        ("bcc", "x+y@example.org"),
    ]
    assert (
        parse(uri, strict=True)
        == parse(uri)
        == Mailto("bill+ietf@example.org", cc="bill+ietf@example.org", bcc="x+y@example.org")
    )


def test_a_plus_in_a_domain_literal_of_the_query_is_encoded() -> None:
    uri = build(cc='"a+b"@[x+y]')
    assert uri == "mailto:?cc=%22a%2Bb%22@%5Bx%2By%5D"
    assert parse(uri, strict=True).cc == ('"a+b"@[x+y]',)


def test_a_plus_in_a_domain_name_cannot_be_written() -> None:
    # Encoded, a domain name breaks RFC 6068 section 2; raw, a form decoder reads a space.
    assert not is_address("a@x+y.example")
    with pytest.raises(MailtoError, match=r"'\+' cannot be written in a domain name"):
        build("a@x+y.example")
    with pytest.raises(MailtoError, match=r"cc: '\+' cannot be written in a domain name"):
        build(cc="a@x+y.example")
    assert parse("mailto:a@x+y.example", strict=True).safe().to == ()


class IterationLies(tuple):  # type: ignore[type-arg]
    def __iter__(self) -> Any:
        return iter(("Keywords", "a", "extra"))


class IndexingLies(tuple):  # type: ignore[type-arg]
    def __getitem__(self, index: Any) -> Any:
        return "X-Lie"


class ListIterationLies(list):  # type: ignore[type-arg]
    def __iter__(self) -> Any:
        return iter(("Keywords", "a", "extra"))


class LengthLies(list):  # type: ignore[type-arg]
    def __len__(self) -> int:
        return 2


@pytest.mark.parametrize(
    "pair",
    [
        IterationLies(("Keywords", "a")),
        IndexingLies(("Keywords", "a")),
        ListIterationLies(["Keywords", "a"]),
    ],
)
def test_build_and_mailto_read_a_pair_from_what_it_holds(pair: Any) -> None:
    assert build(headers=[pair]) == "mailto:?Keywords=a"
    assert Mailto(headers=[pair]).headers == (("Keywords", "a"),)


def test_a_pair_that_lies_about_its_length_is_a_type_error_in_both() -> None:
    pair: Any = LengthLies(["Keywords", "a", "b"])
    for call in (lambda: build(headers=[pair]), lambda: Mailto(headers=[pair])):
        with pytest.raises(TypeError, match=r"\(name, value\) pairs"):
            call()


def test_a_header_name_that_is_not_a_field_name_is_named_by_its_character() -> None:
    with pytest.raises(MailtoError) as caught:
        build(headers={"X-Auth-Token: s3cr3t": "v"})
    assert caught.value.reason == "character ':' not allowed in a header field name"
    with pytest.raises(MailtoError, match="empty header field name"):
        build(headers={"": "v"})


def test_safe_takes_no_none_for_its_allow_list() -> None:
    with pytest.raises(TypeError, match="allow must be str or an iterable of str, got NoneType"):
        Mailto(headers={"Keywords": "k"}).safe(allow=None)  # type: ignore[arg-type]
