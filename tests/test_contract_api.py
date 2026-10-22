"""The complete promise of every public name: signature, result and failure types."""

from __future__ import annotations

import dataclasses
import inspect
import pickle
from typing import Any

import pytest

import mailtourl
from mailtourl import Mailto, MailtoError, build, is_address, parse

SIGNATURES = {
    "parse": "(uri: 'str', *, strict: 'bool' = False) -> 'Mailto'",
    "build": "(to: 'str | Iterable[str] | None' = None, *, "
    "cc: 'str | Iterable[str] | None' = None, bcc: 'str | Iterable[str] | None' = None, "
    "subject: 'str | None' = None, body: 'str | None' = None, "
    "headers: 'Mapping[str, str] | Iterable[tuple[str, str]] | None' = None) -> 'str'",
    "is_address": "(text: 'str') -> 'bool'",
}
METHODS = {
    "__init__": "(self, to: 'str | Iterable[str] | None' = None, *, "
    "cc: 'str | Iterable[str] | None' = None, bcc: 'str | Iterable[str] | None' = None, "
    "subject: 'str | None' = None, body: 'str | None' = None, "
    "headers: 'Mapping[str, str] | Iterable[tuple[str, str]] | None' = None) -> 'None'",
    "header": "(self, name: 'str') -> 'str | None'",
    "header_all": "(self, name: 'str') -> 'tuple[str, ...]'",
    "safe": "(self, allow: 'Iterable[str]' = ('keywords',)) -> 'Mailto'",
    "to_uri": "(self) -> 'str'",
}


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_function_signatures_are_pinned(name: str) -> None:
    assert str(inspect.signature(getattr(mailtourl, name))) == SIGNATURES[name]


@pytest.mark.parametrize("name", sorted(METHODS))
def test_method_signatures_are_pinned(name: str) -> None:
    assert str(inspect.signature(getattr(Mailto, name))) == METHODS[name]


def test_mailto_is_a_frozen_hashable_dataclass_with_pinned_fields() -> None:
    names = [field.name for field in dataclasses.fields(Mailto)]
    assert names == ["to", "cc", "bcc", "subject", "body", "headers"]
    mail = Mailto("a@x.example", subject="s", headers={"K": "v"})
    with pytest.raises(dataclasses.FrozenInstanceError):
        mail.subject = "t"  # type: ignore[misc]
    assert hash(mail) == hash(Mailto(["a@x.example"], subject="s", headers=[("K", "v")]))
    assert dataclasses.replace(mail, subject="t") == Mailto(
        "a@x.example", subject="t", headers={"K": "v"}
    )
    assert isinstance(Mailto.recipients, property)


def test_public_classes_live_and_pickle_under_the_package_name() -> None:
    mail = Mailto("a@x.example", cc="b@x.example", body="b", headers={"K": "v"})
    error = MailtoError("bad", 7)
    for value in (mail, error):
        assert type(value).__module__ == "mailtourl"
        assert b"mailtourl._" not in pickle.dumps(value)
    assert pickle.loads(pickle.dumps(mail)) == mail
    copy = pickle.loads(pickle.dumps(error))
    assert (copy.reason, copy.offset, str(copy)) == ("bad", 7, "bad at offset 7")
    assert str(MailtoError("bad")) == "bad" and MailtoError("bad").offset is None


def test_mailto_error_is_a_value_error() -> None:
    assert issubclass(MailtoError, ValueError)
    with pytest.raises(ValueError):
        parse("http://x")


def test_the_constructor_stores_tuples_of_plain_str() -> None:
    class Text(str):
        def __eq__(self, other: object) -> bool:
            return True

        __hash__ = str.__hash__

    mail = Mailto(
        Text("a@x"),
        cc=[Text("b@x")],
        subject=Text("s"),
        body=Text("b"),
        headers=[(Text("K"), Text("v"))],
    )
    values = [*mail.to, *mail.cc, mail.subject, mail.body, *mail.headers[0]]
    assert all(type(value) is str for value in values)
    assert mail != Mailto("x@x", cc="b@x", subject="s", body="b", headers={"K": "v"})
    assert Mailto(iter(["a@x"]), cc=(x for x in ["b@x"])).recipients == ("a@x", "b@x")


WRONG_TYPES: list[tuple[str, Any]] = [
    ("parse(b'mailto:')", lambda: parse(b"mailto:")),  # type: ignore[arg-type]
    ("parse(None)", lambda: parse(None)),  # type: ignore[arg-type]
    ("is_address(1)", lambda: is_address(1)),  # type: ignore[arg-type]
    ("build(to=5)", lambda: build(5)),  # type: ignore[arg-type]
    ("build(to=bytes)", lambda: build(b"a@x")),  # type: ignore[arg-type]
    ("build(to=[1])", lambda: build([1])),  # type: ignore[list-item]
    ("build(subject=1)", lambda: build(subject=1)),  # type: ignore[arg-type]
    ("build(body=1)", lambda: build(body=1)),  # type: ignore[arg-type]
    ("build(headers=str)", lambda: build(headers="ab")),  # type: ignore[arg-type]
    ("build(headers=5)", lambda: build(headers=5)),  # type: ignore[arg-type]
    ("build(header triple)", lambda: build(headers=[("a", "b", "c")])),  # type: ignore[list-item]
    ("build(header value)", lambda: build(headers={"K": None})),  # type: ignore[arg-type]
    ("build(header name)", lambda: build(headers={1: "v"})),  # type: ignore[arg-type]
    ("Mailto(5)", lambda: Mailto(5)),  # type: ignore[arg-type]
    ("Mailto(bytes)", lambda: Mailto(b"a@x")),  # type: ignore[arg-type]
    ("Mailto(cc=[1])", lambda: Mailto(cc=[1])),  # type: ignore[list-item]
    ("Mailto(subject=1)", lambda: Mailto(subject=1)),  # type: ignore[arg-type]
    ("Mailto(body=b'')", lambda: Mailto(body=b"")),  # type: ignore[arg-type]
    ("Mailto(headers=str)", lambda: Mailto(headers="ab")),  # type: ignore[arg-type]
    ("Mailto(headers={1: 2})", lambda: Mailto(headers={1: 2})),  # type: ignore[arg-type]
    ("header(1)", lambda: Mailto().header(1)),  # type: ignore[arg-type]
    ("header_all(None)", lambda: Mailto().header_all(None)),  # type: ignore[arg-type]
    ("safe(allow=[1])", lambda: Mailto().safe(allow=[1])),  # type: ignore[list-item]
    ("safe(allow=bytes)", lambda: Mailto().safe(allow=b"k")),  # type: ignore[arg-type]
]


@pytest.mark.parametrize(("label", "call"), WRONG_TYPES, ids=[label for label, _ in WRONG_TYPES])
def test_arguments_of_the_wrong_type_raise_type_error(label: str, call: Any) -> None:
    with pytest.raises(TypeError) as caught:
        call()
    assert not isinstance(caught.value, MailtoError)
    assert "object is not iterable" not in str(caught.value)


def test_safe_accepts_a_single_name_and_ignores_case() -> None:
    mail = Mailto(headers=[("X-A", "1"), ("x-b", "2"), ("Keywords", "k")])
    assert mail.safe(allow="x-a").headers == (("X-A", "1"),)
    assert mail.safe(allow=["X-B", "KEYWORDS"]).headers == (("x-b", "2"), ("Keywords", "k"))
    assert mail.safe(allow=[]).headers == ()
