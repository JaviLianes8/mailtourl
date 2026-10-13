"""The default parser: RFC 6068 fields, browser preprocessing, merge rules."""

from __future__ import annotations

import pytest

from mailtourl import Mailto, MailtoError, parse


def test_parse_single_recipient() -> None:
    assert parse("mailto:jane@example.com") == Mailto("jane@example.com")


def test_parse_to_subject_and_body() -> None:
    result = parse("mailto:jane@example.com?subject=Hello&body=Line%20one")
    assert result.to == ("jane@example.com",)
    assert result.subject == "Hello"
    assert result.body == "Line one"


def test_parse_multiple_recipients_in_path() -> None:
    assert parse("mailto:a@example.com,b@example.com").to == ("a@example.com", "b@example.com")


def test_to_from_the_path_and_every_to_field_accumulate_in_order() -> None:
    result = parse("mailto:a@example.com?to=b@example.com,c@example.com&to=d@example.com")
    assert result.to == ("a@example.com", "b@example.com", "c@example.com", "d@example.com")


def test_cc_and_bcc_fields_accumulate_in_order() -> None:
    result = parse("mailto:?cc=a@x.example&bcc=b@x.example&cc=c@x.example&bcc=d@x.example")
    assert result.cc == ("a@x.example", "c@x.example")
    assert result.bcc == ("b@x.example", "d@x.example")


def test_an_encoded_comma_stays_inside_one_address() -> None:
    assert parse("mailto:%22a%2Cb%22@x.example").to == ('"a,b"@x.example',)


def test_parse_percent_encoded_values() -> None:
    result = parse("mailto:a@example.com?subject=Re%3A%20caf%C3%A9&body=%26%20more")
    assert result.subject == "Re: café"
    assert result.body == "& more"


def test_a_plus_sign_is_never_read_as_a_space() -> None:
    result = parse("mailto:bill+ietf@example.org?subject=1+1")
    assert result.to == ("bill+ietf@example.org",)
    assert result.subject == "1+1"


def test_the_first_subject_and_body_win() -> None:
    result = parse("mailto:a@x.example?subject=one&body=first&subject=two&body=second")
    assert result.subject == "one"
    assert result.body == "first"


def test_other_headers_keep_order_spelling_and_repeats() -> None:
    result = parse("mailto:a@x.example?Keywords=a&In-Reply-To=%3Cid%40h%3E&keywords=b")
    assert result.headers == (("Keywords", "a"), ("In-Reply-To", "<id@h>"), ("keywords", "b"))
    assert result.header("KEYWORDS") == "a"
    assert result.header_all("keywords") == ("a", "b")


def test_parse_empty_mailto() -> None:
    assert parse("mailto:") == Mailto()


def test_parse_is_case_insensitive_for_scheme_and_field_names() -> None:
    result = parse("MAILTO:a@example.com?SUBJECT=Hi&Cc=c@x.example&BODY=b")
    assert result == Mailto("a@example.com", cc="c@x.example", subject="Hi", body="b")


def test_a_segment_without_value_is_an_empty_header() -> None:
    result = parse("mailto:a@example.com?draft&subject=Hi")
    assert result.headers == (("draft", ""),)
    assert result.subject == "Hi"


def test_empty_segments_and_empty_names_are_skipped() -> None:
    assert parse("mailto:a@x.example?&&=x&subject=Hi&") == Mailto("a@x.example", subject="Hi")


def test_the_fragment_is_ignored() -> None:
    result = parse("mailto:a@x.example?body=hi#top")
    assert result.body == "hi"
    assert parse("mailto:a@x.example#top") == Mailto("a@x.example")


def test_browser_preprocessing_strips_and_removes_tabs_and_newlines() -> None:
    uri = "\x00 \tmailto:a@x.\nexample?sub\tject=hi\r\n \x1f"
    assert parse(uri) == Mailto("a@x.example", subject="hi")


def test_whitespace_around_addresses_is_trimmed() -> None:
    assert parse("mailto:%20a@x.example%20,%20,b@x.example").to == ("a@x.example", "b@x.example")


def test_invalid_utf8_decodes_to_the_replacement_character() -> None:
    assert parse("mailto:?subject=%FF").subject == "�"


def test_a_lone_percent_sign_stays_literal() -> None:
    assert parse("mailto:?subject=100%").subject == "100%"


def test_parse_rejects_other_schemes() -> None:
    with pytest.raises(MailtoError) as caught:
        parse("http://example.com")
    assert caught.value.offset == 0


def test_parse_rejects_a_scheme_without_its_colon() -> None:
    with pytest.raises(MailtoError):
        parse("mailto")


def test_parse_rejects_bytes_with_a_type_error() -> None:
    with pytest.raises(TypeError):
        parse(b"mailto:a@x.example")  # type: ignore[arg-type]
