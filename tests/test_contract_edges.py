"""Edge contracts found missing by the 1.0.0 mutation round."""

from __future__ import annotations

import pytest

from mailtourl import MailtoError, build, is_address, parse

# Unicode noncharacters: U+FDD0 to U+FDEF and the last two code points of every plane.
NONCHARACTERS = [0xFDD0, 0xFDDF, 0xFDEF, 0xFFFE, 0xFFFF, 0x1FFFE, 0x1FFFF, 0x10FFFE, 0x10FFFF]


@pytest.mark.parametrize("code", NONCHARACTERS, ids=[f"U+{code:04X}" for code in NONCHARACTERS])
def test_noncharacters_are_refused_in_addresses(code: int) -> None:
    text = f"a{chr(code)}@x.example"
    assert not is_address(text)
    assert not is_address(f"a@x{chr(code)}.example")
    with pytest.raises(MailtoError):
        build(text)


@pytest.mark.parametrize("code", [0xFDCF, 0xFDF0, 0xFFFD, 0x1FFFD])
def test_the_code_points_next_to_the_noncharacters_are_allowed(code: int) -> None:
    assert is_address(f"a{chr(code)}@x.example")


@pytest.mark.parametrize("blank", ["", " ", "\t\n\r", " \x00\x1f "])
def test_blank_input_reports_offset_zero(blank: str) -> None:
    with pytest.raises(MailtoError) as caught:
        parse(blank)
    assert (caught.value.reason, caught.value.offset) == ("not a mailto: URI", 0)


def test_a_wrong_scheme_after_spaces_points_at_its_first_character() -> None:
    with pytest.raises(MailtoError) as caught:
        parse("  \thttp://x ")
    assert caught.value.offset == 3
