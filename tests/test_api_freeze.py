"""API details fixed before 1.0.0 and edges a mutation round found unguarded."""

from __future__ import annotations

import doctest
import inspect
import pickle
import pydoc
import tracemalloc

import pytest

import mailtourl
from mailtourl import Mailto, MailtoError, build, is_address, parse


def test_mailto_takes_none_like_build() -> None:
    assert Mailto(None) == Mailto() == Mailto(cc=None, bcc=None, headers=None)
    mail = Mailto("a@x.example", cc=None, bcc=None, headers=None)
    assert mail.to_uri() == build("a@x.example", cc=None, bcc=None, headers=None)
    for name in ("to", "cc", "bcc", "headers"):
        assert inspect.signature(Mailto).parameters[name].default is None
        assert inspect.signature(build).parameters[name].default is None


@pytest.mark.parametrize("name", ["build", "parse", "is_address"])
def test_public_functions_live_under_the_package_name(name: str) -> None:
    function = getattr(mailtourl, name)
    assert function.__module__ == "mailtourl"
    assert b"mailtourl._" not in pickle.dumps(function)
    assert pickle.loads(pickle.dumps(function)) is function
    shown = pydoc.render_doc(function)
    assert "mailtourl._" not in shown
    assert "Addresses" not in shown and "Headers" not in shown


def test_every_public_docstring_example_runs_in_a_fresh_namespace() -> None:
    finder, runner = doctest.DocTestFinder(recurse=False), doctest.DocTestRunner()
    for name in mailtourl.__all__:
        for test in finder.find(getattr(mailtourl, name), name, globs={}):
            runner.run(test)
    assert runner.summarize(verbose=False).failed == 0


def test_mailto_error_takes_its_reason_by_name() -> None:
    error = MailtoError(reason="bad", offset=3)
    assert (error.reason, error.offset, str(error)) == ("bad", 3, "bad at offset 3")
    assert list(inspect.signature(MailtoError).parameters) == ["reason", "offset"]
    copy = pickle.loads(pickle.dumps(MailtoError(reason="bad")))
    assert (copy.reason, copy.offset) == ("bad", None)


def test_the_error_for_offset_zero_still_names_the_offset() -> None:
    with pytest.raises(MailtoError) as caught:
        parse("x")
    assert str(caught.value) == "not a mailto: URI at offset 0"


@pytest.mark.parametrize("escaped", ["\x7f", "\x00", "\x1f", "\x85", "\x9f"])
def test_a_quoted_pair_cannot_escape_a_control(escaped: str) -> None:
    assert not is_address(f'"a\\{escaped}"@x.example')
    assert is_address('"a\\~"@x.example') and is_address('"a\\ "@x.example')


@pytest.mark.parametrize("pair", [("X-A", "X-A"), ("X-A", "x-A"), ("KEYWORDS", "Keywords")])
def test_build_refuses_a_header_repeated_in_any_case(pair: tuple[str, str]) -> None:
    with pytest.raises(MailtoError, match="given twice"):
        build(headers=[(pair[0], "1"), (pair[1], "2")])


@pytest.mark.parametrize("key", ["to", "cc", "bcc"])
def test_strict_refuses_a_raw_equals_sign_in_a_recipient_field(key: str) -> None:
    with pytest.raises(MailtoError, match="'=' must be percent-encoded") as caught:
        parse(f"mailto:?{key}=a=b@x.example", strict=True)
    assert caught.value.offset == len(f"mailto:?{key}=a")


def test_messages_quote_sixty_characters_whole_and_cut_sixty_one() -> None:
    sixty, sixty_one = "a" * 59 + ":", "a" * 60 + ":"
    with pytest.raises(MailtoError) as caught:
        build(headers=[(sixty, "v")])
    assert str(caught.value) == f"{sixty!r} is not an RFC 5322 header field name"
    with pytest.raises(MailtoError) as caught:
        build(headers=[(sixty_one, "v")])
    assert str(caught.value) == "'" + "a" * 59 + "... is not an RFC 5322 header field name"


def test_strict_messages_name_a_field_of_sixty_characters_whole() -> None:
    for name, shown in (("a" * 60, "a" * 60), ("a" * 61, "a" * 60 + "...")):
        with pytest.raises(MailtoError) as caught:
            parse(f"mailto:?{name}=x y", strict=True)
        assert caught.value.reason == f"' ' must be percent-encoded in the {shown} value"


def _peak(uri: str, *, strict: bool = False) -> int:
    tracemalloc.start()
    try:
        parse(uri, strict=strict)
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


SUBJECT = "mailto:a@x.example?subject=" + "a" * 1_000_000
RECIPIENTS = "mailto:" + ",".join(["a@x.example"] * 80_000)
TABS = "mailto:a@x.example?subject=" + "a\t" * 500_000
ESCAPES = "mailto:a@x.example?body=" + "%41" * 333_333


@pytest.mark.parametrize("uri", [SUBJECT, RECIPIENTS, TABS], ids=["subject", "to", "tabs"])
def test_the_default_mode_needs_memory_of_a_few_times_the_input(uri: str) -> None:
    peak = _peak(uri)
    assert peak < 12 * len(uri), peak / len(uri)


@pytest.mark.parametrize("uri", [SUBJECT, RECIPIENTS, ESCAPES], ids=["subject", "to", "escapes"])
def test_the_default_mode_needs_no_more_memory_than_strict(uri: str) -> None:
    # Decoding many escapes costs what urllib.parse.unquote_to_bytes costs, in both modes.
    assert _peak(uri) <= 1.1 * _peak(uri, strict=True)
