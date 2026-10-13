"""is_address: RFC 5322 addr-spec as RFC 6068 restricts it, UTF-8 per RFC 6532."""

from __future__ import annotations

import pytest

from mailtourl import is_address

# Hand-written cases derived from the ABNF in RFC 5322 section 3.2.3, 3.2.4 and 3.4.1,
# RFC 6068 section 2 and RFC 6532 section 3.2.
VALID = [
    "a@b",
    "jane.doe@example.com",
    "bill+ietf@example.org",
    "!#$%&'*+-/=?^_`{|}~@x.example",
    '"not@me"@example.org',
    '"oh\\\\no"@example.org',
    '"\\\\\\"it\'s\\ ugly\\\\\\""@example.org',
    '""@x.example',
    '"(a),[b]"@x.example',
    "a@[192.0.2.1]",
    "a@[IPv6:2001:db8::1]",
    "a@[]",
    "josé@éxample.example",
    "用户@例子.广告",
    "a@x.\U0001f600",
]

INVALID = [
    "",
    "plain",
    "@x.example",
    "a@",
    "a@b@c",
    ".a@x.example",
    "a.@x.example",
    "a..b@x.example",
    "a@x..example",
    "a@.x",
    "a b@x.example",
    "a@x example",
    '"a b"@x.example',
    '"a\tb"@x.example',
    '"a"b@x.example',
    '"a@x.example',
    '"a\\',
    '"a\\\x01"@x.example',
    '"a\x7f"@x.example',
    "a(c)@x.example",
    "a@x.example(c)",
    "Jane <jane@x.example>",
    "a,b@x.example",
    "a;b@x.example",
    "a@[1.2.3.4",
    "a@[x[y]",
    "a@[x\\y]",
    "a@[é]",
    "a\x00@x.example",
    "a@x\ud800.example",
]


@pytest.mark.parametrize("text", VALID)
def test_valid_addresses(text: str) -> None:
    assert is_address(text)


@pytest.mark.parametrize("text", INVALID)
def test_invalid_addresses(text: str) -> None:
    assert not is_address(text)


def test_is_address_refuses_non_strings() -> None:
    with pytest.raises(TypeError):
        is_address(b"a@b")  # type: ignore[arg-type]
