"""The Mailto value: frozen, hashable, typed, with lookups and to_uri."""

from __future__ import annotations

import copy
import dataclasses
import pickle

import pytest

from mailtourl import Mailto, MailtoError, parse


def test_defaults_are_empty() -> None:
    mail = Mailto()
    assert (mail.to, mail.cc, mail.bcc, mail.headers) == ((), (), (), ())
    assert mail.subject is None and mail.body is None


def test_lists_strings_and_mappings_are_stored_as_tuples() -> None:
    mail = Mailto(["a@x.example"], cc="c@x.example", bcc=iter(["d@x.example"]), headers={"K": "v"})
    assert mail.to == ("a@x.example",)
    assert mail.cc == ("c@x.example",)
    assert mail.bcc == ("d@x.example",)
    assert mail.headers == (("K", "v"),)


def test_it_is_frozen_and_hashable() -> None:
    mail = Mailto("a@x.example", headers=[("K", "v")])
    with pytest.raises(dataclasses.FrozenInstanceError):
        mail.subject = "x"  # type: ignore[misc]
    assert hash(mail) == hash(Mailto(["a@x.example"], headers={"K": "v"}))
    assert {mail, Mailto("a@x.example", headers={"K": "v"})} == {mail}


def test_it_pickles_and_copies() -> None:
    mail = Mailto("a@x.example", subject="s", headers=[("K", "v")])
    assert pickle.loads(pickle.dumps(mail)) == mail
    assert copy.deepcopy(mail) == mail
    assert dataclasses.replace(mail, subject="t").subject == "t"


def test_recipients_lists_to_cc_and_bcc_in_order() -> None:
    mail = Mailto(["a@x.example", "b@x.example"], cc="c@x.example", bcc="d@x.example")
    assert mail.recipients == ("a@x.example", "b@x.example", "c@x.example", "d@x.example")


def test_header_lookup_ignores_case_and_returns_the_first() -> None:
    mail = Mailto(headers=[("X-A", "1"), ("x-a", "2"), ("X-B", "3")])
    assert mail.header("x-A") == "1"
    assert mail.header_all("X-A") == ("1", "2")
    assert mail.header("missing") is None
    assert mail.header_all("missing") == ()


def test_to_uri_builds_with_the_same_rules() -> None:
    mail = Mailto("a@x.example", cc="c@x.example", subject="Hi", body="b", headers={"K": "v"})
    assert mail.to_uri() == "mailto:a@x.example?cc=c@x.example&subject=Hi&body=b&K=v"
    assert parse(mail.to_uri()) == mail
    with pytest.raises(MailtoError):
        Mailto("not an address").to_uri()


@pytest.mark.parametrize(
    "call",
    [
        lambda: Mailto(b"a@x.example"),  # type: ignore[arg-type]
        lambda: Mailto([1]),  # type: ignore[list-item]
        lambda: Mailto(cc=[None]),  # type: ignore[list-item]
        lambda: Mailto(bcc=[1]),  # type: ignore[list-item]
        lambda: Mailto(subject=1),  # type: ignore[arg-type]
        lambda: Mailto(body=b"x"),  # type: ignore[arg-type]
        lambda: Mailto(headers=[("a", 1)]),  # type: ignore[list-item]
        lambda: Mailto(headers=[(1, "a")]),  # type: ignore[list-item]
        lambda: Mailto(headers=["ab"]),  # type: ignore[list-item]
        lambda: Mailto(headers=[("a",)]),  # type: ignore[list-item]
        lambda: Mailto().safe([1]),  # type: ignore[list-item]
    ],
)
def test_wrong_types_raise_type_error(call: object) -> None:
    with pytest.raises(TypeError):
        call()  # type: ignore[operator]


def test_the_error_carries_reason_and_offset_and_pickles() -> None:
    error = MailtoError("bad", 4)
    assert (error.reason, error.offset, str(error)) == ("bad", 4, "bad at offset 4")
    assert isinstance(error, ValueError)
    again = pickle.loads(pickle.dumps(error))
    assert (again.reason, again.offset, str(again)) == ("bad", 4, "bad at offset 4")
    assert str(MailtoError("plain")) == "plain" and MailtoError("plain").offset is None
