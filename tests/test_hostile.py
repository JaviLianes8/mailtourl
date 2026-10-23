"""Huge and adversarial input: linear time and short error messages on every path."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable

import pytest

from mailtourl import Mailto, MailtoError, build, is_address, parse

BIG = 100_000

ERRORS: list[tuple[str, Callable[[], object]]] = [
    ("long name, injected value", lambda: parse(f"mailto:?{'N' * BIG}=%0A")),
    ("long name, strict raw value", lambda: parse(f"mailto:?{'N' * BIG}=a b", strict=True)),
    ("long name, strict control", lambda: parse(f"mailto:?{'N' * BIG}=%01", strict=True)),
    (
        "long name, strict repeat",
        lambda: parse(f"mailto:?{'N' * BIG}=a&{'n' * BIG}=b", strict=True),
    ),
    ("long invalid name", lambda: parse(f"mailto:?{'N:' * BIG}=a", strict=True)),
    ("long address", lambda: parse(f"mailto:{'a' * BIG}", strict=True)),
    ("long quoted address", lambda: parse(f"mailto:%22{'a' * BIG}", strict=True)),
    ("long domain literal", lambda: parse(f"mailto:a@[{'%5C' * BIG}]", strict=True)),
    ("long scheme", lambda: parse("x" * BIG)),
    ("long bad escape", lambda: parse(f"mailto:?subject={'%E2' * BIG}", strict=True)),
    ("long injected address", lambda: parse(f"mailto:{'a' * BIG}%0A@x")),
    ("build long address", lambda: build("a" * BIG)),
    ("build long display name", lambda: build(f"{'J' * BIG} <j@x.example>")),
    ("build long domain", lambda: build(f"a@{'&' * BIG}")),
    ("build long header name", lambda: build(headers={"N:" * BIG: "v"})),
    ("build ignored header", lambda: build(headers={"Resent-" + "x" * BIG: "v"})),
    ("build repeated header", lambda: build(headers=[("N" * BIG, "a"), ("n" * BIG, "b")])),
    ("build header control", lambda: build(headers={"N" * BIG: "\r"})),
    ("build surrogate", lambda: build(subject="\ud800" * BIG)),
    ("to_uri long name", lambda: Mailto(headers={"N" * BIG: "\n"}).to_uri()),
]


@pytest.mark.parametrize(("label", "call"), ERRORS, ids=[label for label, _ in ERRORS])
def test_error_messages_stay_short_for_huge_input(label: str, call: Callable[[], object]) -> None:
    with pytest.raises(MailtoError) as caught:
        call()
    assert len(str(caught.value)) < 300, label


SHAPES: dict[str, Callable[[int], object]] = {
    "many recipients": lambda n: parse("mailto:" + "a@x.example," * n),
    "many recipients strict": lambda n: parse("mailto:" + "a@x.example," * n + "a@x", strict=True),
    "many empty fields": lambda n: parse("mailto:?" + "&" * n),
    "many fields": lambda n: parse("mailto:?" + "k=v&" * n),
    "repeated subject": lambda n: parse("mailto:?" + "subject=v&" * n),
    "body line breaks": lambda n: parse("mailto:?body=" + "%0D%0A" * n, strict=True),
    "percent signs": lambda n: parse("mailto:" + "%" * n),
    "broken utf-8": lambda n: parse("mailto:?subject=" + "%E2" * n),
    "whitespace around": lambda n: parse(" " * n + "mailto:" + "\t" * n + "a@x" + "\x01" * n),
    "late strict error": lambda n: parse("mailto:?subject=" + "a" * n + " ", strict=True),
    "late injection": lambda n: parse("mailto:?subject=" + "%41" * n + "%0A"),
    "late lenient error": lambda n: parse("\t" * n + "mailto:?subject=" + "a\n" * n + "%0A"),
    "quoted local part": lambda n: is_address('"' + '\\"' * n + '"@x.example'),
    "long dot atom": lambda n: is_address("a." * n + "a@x.example"),
    "header lookup": lambda n: Mailto(headers=[("K", "v")] * n).header_all("k"),
    "safe filter": lambda n: Mailto(["a@x.example"] * n).safe(),
    "build body": lambda n: build(body="a\r\n\n\r" * n),
    "build recipients": lambda n: build(["a@x.example"] * n),
}


def _cost(call: Callable[[int], object], size: int) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        with contextlib.suppress(MailtoError):
            call(size)
        best = min(best, time.perf_counter() - start)
    return best


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_time_grows_linearly_with_input_size(shape: str) -> None:
    small, large = _cost(SHAPES[shape], 4_000), _cost(SHAPES[shape], 64_000)
    # Sixteen times the input: linear work takes about 16 times longer, quadratic 256.
    assert large < max(small, 0.002) * 64, (shape, small, large)
