"""Seeded random round trips: build then parse, strict and lenient, give the value back."""

from __future__ import annotations

import random
import re

from mailtourl import Mailto, build, is_address, parse

ATEXT = "abcXYZ019!#$%&'*+-/=?^_`{|}~é納"
# Domain atoms avoid the atext characters a URI cannot hold raw: see build's domain rule.
DOMAIN = "abcXYZ019-!$'*+é納"
QTEXT = "a Z9!#$%&'()*+,-./:;<=>?@[]^_`{|}~é"
FIELD = "aZ9 -._~!$&'()*+,;=:@/?#[]%\"<>\\^`{|}\té納\U0001f600"


def _atoms(rng: random.Random, alphabet: str = ATEXT) -> str:
    return ".".join(
        "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 5)))
        for _ in range(rng.randint(1, 3))
    )


def _address(rng: random.Random) -> str:
    if rng.random() < 0.3:
        parts = [rng.choice(['\\"', "\\\\", "\\ ", rng.choice(QTEXT)]) for _ in range(6)]
        local = '"' + "".join(part for part in parts if part != " ") + '"'
    else:
        local = _atoms(rng)
    domain = f"[{rng.choice(['192.0.2.1', 'IPv6:2001:db8::1'])}]" if rng.random() < 0.1 else ""
    return f"{local}@{domain or _atoms(rng, DOMAIN)}"


def _text(rng: random.Random, newlines: bool = False) -> str:
    pool = FIELD + ("\r\n" if newlines else "")
    return "".join(rng.choice(pool) for _ in range(rng.randrange(15)))


def _mailto(rng: random.Random) -> Mailto:
    names = rng.sample(["Keywords", "In-Reply-To", "X-A", "x-b!#$%&'*+-.^_`|~"], rng.randint(0, 3))
    return Mailto(
        [_address(rng) for _ in range(rng.randint(0, 3))],
        cc=[_address(rng) for _ in range(rng.randint(0, 2))],
        bcc=[_address(rng) for _ in range(rng.randint(0, 2))],
        subject=rng.choice([None, _text(rng)]),
        body=rng.choice([None, _text(rng, newlines=True)]),
        headers=[(name, _text(rng)) for name in names],
    )


def _crlf(mail: Mailto) -> Mailto:
    body = None if mail.body is None else re.sub(r"\r\n|\r|\n", "\r\n", mail.body)
    return Mailto(
        mail.to, cc=mail.cc, bcc=mail.bcc, subject=mail.subject, body=body, headers=mail.headers
    )


def test_random_values_round_trip_through_build_and_both_parsers() -> None:
    rng = random.Random(6068)
    for _ in range(3000):
        mail = _mailto(rng)
        assert all(is_address(address) for address in mail.recipients), mail
        uri = mail.to_uri()
        expected = _crlf(mail)
        assert parse(uri, strict=True) == expected, uri
        assert parse(uri) == expected, uri
        assert parse(uri).to_uri() == uri


def test_build_and_to_uri_agree() -> None:
    rng = random.Random(3986)
    for _ in range(200):
        mail = _mailto(rng)
        uri = build(
            mail.to,
            cc=mail.cc,
            bcc=mail.bcc,
            subject=mail.subject,
            body=mail.body,
            headers=mail.headers,
        )
        assert uri == mail.to_uri()
