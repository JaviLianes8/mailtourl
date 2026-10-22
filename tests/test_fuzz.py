"""Seeded random hostile input: only MailtoError escapes, and every result keeps the promises.

The cases are generated from fixed seeds, so a failure always reproduces.
"""

from __future__ import annotations

import random
import re

import pytest

from mailtourl import Mailto, MailtoError, build, is_address, parse
from mailtourl._chars import LINE_BREAKS

TOKENS = [
    *"aZ09-._~!$'()*+,;:@/?#[]&=%\"\\<>` \t\r\n",
    *("%0", "%0D", "%0A", "%0d%0a", "%00", "%0B", "%1C", "%85", "%C2%85", "%E2%80%A8", "%7F"),
    *("%C3%A9", "%C3", "%FF", "%ED%A0%80", "%22", "%40", "%26", "%3D", "%3F", "%2C", "%20"),
    *("\x00", "\x01", "\x1f", "\x7f", "\x85", "\u2028", "\u200b", "\ud800", "\ufeff"),
    *("é", "納", "\U0001f600", "x.example", "[192.0.2.1]", "to=", "cc=", "bcc=", "%62cc="),
    *("subject=", "body=", "From=", "Keywords=", "?to=", "&cc=", "&body=", "mailto:", "a@x"),
]


def _hostile(rng: random.Random) -> str:
    text = "".join(rng.choice(TOKENS) for _ in range(rng.randrange(25)))
    head = rng.choice(["mailto:", "mailto:", "mailto:", "MAILTO:", " \x01mailto:", "mail\tto:", ""])
    return head + text


def _crlf(mail: Mailto) -> Mailto:
    body = None if mail.body is None else re.sub(r"\r\n|\r|\n", "\r\n", mail.body)
    return Mailto(
        mail.to, cc=mail.cc, bcc=mail.bcc, subject=mail.subject, body=body, headers=mail.headers
    )


def _check_result(mail: Mailto) -> None:
    single_line = [*mail.recipients, *(text for pair in mail.headers for text in pair)]
    single_line.append(mail.subject or "")
    for text in single_line:
        assert not LINE_BREAKS & set(text), mail
    assert all(is_address(address) for address in mail.safe().recipients)
    try:
        uri = mail.to_uri()
    except MailtoError:
        return
    assert parse(uri, strict=True) == _crlf(mail), uri
    assert parse(uri) == _crlf(mail), uri


def _check_error(error: MailtoError, text: str) -> None:
    assert error.offset is not None and 0 <= error.offset <= len(text), (error, text)
    assert str(error).startswith(error.reason)
    assert len(str(error)) < 300


@pytest.mark.parametrize("seed", [6068, 3986, 5322])
def test_random_input_raises_only_mailto_error_and_keeps_the_promises(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(6000):
        text = _hostile(rng)
        try:
            strict = parse(text, strict=True)
        except MailtoError as error:
            _check_error(error, text)
            strict = None
        try:
            lenient = parse(text)
        except MailtoError as error:
            _check_error(error, text)
            assert strict is None, text
            continue
        _check_result(lenient)
        if strict is not None:
            # Whatever the grammar accepts reads the same way in the default mode.
            assert lenient == strict, text


@pytest.mark.parametrize("seed", [1, 2])
def test_random_builder_input_gives_a_strict_uri_or_mailto_error(seed: int) -> None:
    rng = random.Random(seed)
    pieces = [token for token in TOKENS if "%" not in token or rng.random() < 0.5]
    for _ in range(4000):

        def text(limit: int = 12) -> str:
            return "".join(rng.choice(pieces) for _ in range(rng.randrange(limit)))

        to = [text() for _ in range(rng.randrange(3))]
        cc = text() if rng.random() < 0.3 else None
        subject, body = rng.choice([None, text()]), rng.choice([None, text(20)])
        headers = [(text(4), text()) for _ in range(rng.randrange(3))]
        try:
            uri = build(to, cc=cc, subject=subject, body=body, headers=headers)
        except MailtoError as error:
            assert error.offset is None and len(str(error)) < 300
            continue
        assert all(0x20 < ord(char) < 0x7F for char in uri), uri
        mail = parse(uri, strict=True)
        assert mail.to == tuple(to) and mail.subject == subject
        assert mail.to_uri() == uri
