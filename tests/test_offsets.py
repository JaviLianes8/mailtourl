"""MailtoError.offset points at the offending character, after broken escapes too."""

from __future__ import annotations

import random
from urllib.parse import unquote

import pytest

from mailtourl import MailtoError, parse
from mailtourl._positions import char_starts


def _offset(uri: str, *, strict: bool = False) -> int | None:
    with pytest.raises(MailtoError) as caught:
        parse(uri, strict=strict)
    return caught.value.offset


@pytest.mark.parametrize(
    ("uri", "offset"),
    [
        ("mailto:a@x?subject=%FF%0A", 22),
        ("mailto:%FF%0A@x", 10),
        ("mailto:a@x?subject=x%E2%82%0Atail", 26),
        ("mailto:%FF%FF%FF%0Aabcdefgh@x.example", 16),
        ("mailto:?subject=%FF%0A", 19),
        ("mailto:?subject=%FF%0Axyz", 19),
        ("mailto:?cc=%FF%0Aa@x.example", 14),
        ("mailto:a%FF%0A@x.example", 11),
        ("mailto:?subject=%E2%82%0A", 22),
        ("mailto:?subject=%F0%90%80A%0A", 26),
        ("mailto:?subject=%ED%A0%80%0A", 25),
        ("mailto:?subject=%EF%BF%BD%0A", 25),
        ("mailto:?subject=\ufffd%FF%0A", 20),
        ("mailto:?subject=é%FF\u2028", 20),
        ("mailto:?subject=%C3é%0A", 20),
        ("mailto:?subject=%%4%G1%FF%0A", 25),
        ("mailto:?subject=%E0%80%0A", 22),
        ("mailto:?subject=%F0%80%80%0A", 25),
        ("mailto:?subject=%F4%90%80%0A", 25),
        ("mailto:?subject=%ED%9F%BF%C2%0A", 28),
        ("mailto:?subject=%C2%0A", 19),
    ],
)
def test_lenient_offsets_survive_bytes_that_are_not_utf_8(uri: str, offset: int) -> None:
    assert _offset(uri) == offset


def test_lenient_offsets_count_the_characters_the_browser_removes() -> None:
    assert _offset("mailto:?sub\tject=%FF%0A") == 20
    assert _offset("  mailto:?subject=%FF%0A \n") == 21
    assert _offset("mailto:?subject=%FF%0A ") == 19


PREFIX_TOKENS = ["a", "é", "\ufffd", "%FF", "%E2%82", "%C3%A9", "%F0%90%80", "%ED%A0%80"]
PREFIX_TOKENS += ["%", "%4", "%G1", "%EF%BF%BD", "%C3", "%80", "%e2%82", "\U0001f600", "%2C"]
PREFIX_TOKENS += ["%E0%80", "%E0%A0", "%F4%90", "%F4%8F", "%F0%80", "%F0%90", "%ED%9F", "%C2"]


def test_character_starts_agree_with_the_standard_library_decoder() -> None:
    rng = random.Random(3629)
    for _ in range(20000):
        raw = "".join(rng.choice(PREFIX_TOKENS) for _ in range(rng.randrange(10)))
        value = unquote(raw)
        starts = list(char_starts(raw))
        assert len(starts) == len(value), raw
        for index, start in enumerate(starts):
            assert unquote(raw[:start]) == value[:index], (raw, index)


@pytest.mark.parametrize("seed", [6068, 20261022])
def test_an_injected_line_break_is_found_after_any_prefix(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(2000):
        prefix = "".join(rng.choice(PREFIX_TOKENS) for _ in range(rng.randrange(8)))
        brk = rng.choice(["%0A", "%0d", "%00", "%C2%85", "%E2%80%A8", "\u2028", "\x85"])
        field = rng.choice(["subject=", "X-Tag=", "cc="])
        uri = f"mailto:?{field}{prefix}{brk}tail"
        assert _offset(uri) == len("mailto:?") + len(field) + len(prefix), uri


@pytest.mark.parametrize(
    ("uri", "offset"),
    [
        ("mailto:a@x.example?subject=ok%FFtail", 29),
        ("mailto:a@x.example?subject=caf%C3%A9%FFtail", 36),
        ("mailto:a@x.example?Keywords=ok%C3tail", 30),
        ("mailto:?subject=ab%C3", 18),
        ("mailto:a%FF@x.example", 8),
        ("mailto:a@x.example?body=%E2%82x", 24),
    ],
)
def test_strict_points_at_the_escape_that_is_not_utf_8(uri: str, offset: int) -> None:
    with pytest.raises(MailtoError, match="not UTF-8") as caught:
        parse(uri, strict=True)
    assert caught.value.offset == offset


@pytest.mark.parametrize(
    ("uri", "offset"),
    [
        ("mailto:%22a@b%22%40%5B192.0.2.1%5D", 16),
        ("mailto:%22a@b%22%40x.example", 16),
        ("mailto:joe%40ex%61mple.com", 10),
        ("mailto:?cc=x@y.example,%22@%22%40x.example", 30),
    ],
)
def test_strict_refuses_an_encoded_separator_and_points_at_it(uri: str, offset: int) -> None:
    with pytest.raises(MailtoError, match="'@' before the domain") as caught:
        parse(uri, strict=True)
    assert caught.value.offset == offset


def test_strict_still_takes_a_raw_at_sign_inside_quotes() -> None:
    assert parse("mailto:%22a@b%22@x.example", strict=True).to == ('"a@b"@x.example',)
    assert parse("mailto:%22a%40b%22@%5B192.0.2.1%5D", strict=True).to == ('"a@b"@[192.0.2.1]',)
