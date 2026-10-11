import pytest

from mailtourl import Mailto, MailtoError, build, parse


def test_parse_single_recipient() -> None:
    result = parse("mailto:jane@example.com")
    assert result == Mailto(to=["jane@example.com"])


def test_parse_to_subject_and_body() -> None:
    result = parse("mailto:jane@example.com?subject=Hello&body=Line%20one")
    assert result.to == ["jane@example.com"]
    assert result.subject == "Hello"
    assert result.body == "Line one"


def test_parse_multiple_recipients_in_path() -> None:
    result = parse("mailto:a@example.com,b@example.com")
    assert result.to == ["a@example.com", "b@example.com"]


def test_parse_to_from_query_and_path_accumulate() -> None:
    result = parse("mailto:a@example.com?to=b@example.com")
    assert result.to == ["a@example.com", "b@example.com"]


def test_parse_cc_and_bcc() -> None:
    result = parse("mailto:a@example.com?cc=c@example.com&bcc=d@example.com")
    assert result.cc == ["c@example.com"]
    assert result.bcc == ["d@example.com"]


def test_parse_percent_encoded_values() -> None:
    result = parse("mailto:a@example.com?subject=Re%3A%20caf%C3%A9&body=%26%20more")
    assert result.subject == "Re: café"
    assert result.body == "& more"


def test_parse_keeps_unknown_headers() -> None:
    result = parse("mailto:a@example.com?In-Reply-To=%3Cabc%40x%3E")
    assert result.headers == {"In-Reply-To": "<abc@x>"}


def test_parse_empty_mailto() -> None:
    assert parse("mailto:") == Mailto()


def test_parse_is_case_insensitive_for_scheme_and_fields() -> None:
    result = parse("MAILTO:a@example.com?SUBJECT=Hi")
    assert result.to == ["a@example.com"]
    assert result.subject == "Hi"


def test_parse_tolerates_segment_without_value() -> None:
    result = parse("mailto:a@example.com?draft&subject=Hi")
    assert result.headers == {"draft": ""}
    assert result.subject == "Hi"


def test_parse_rejects_other_schemes() -> None:
    with pytest.raises(MailtoError):
        parse("http://example.com")


def test_build_single_recipient() -> None:
    assert build("jane@example.com") == "mailto:jane@example.com"


def test_build_with_subject_and_body() -> None:
    uri = build("jane@example.com", subject="Hello there", body="Line one\nLine two")
    assert uri == "mailto:jane@example.com?subject=Hello%20there&body=Line%20one%0ALine%20two"


def test_build_multiple_recipients_and_cc_bcc() -> None:
    uri = build(
        ["a@example.com", "b@example.com"],
        cc="c@example.com",
        bcc=["d@example.com"],
    )
    assert uri == "mailto:a@example.com,b@example.com?cc=c@example.com&bcc=d@example.com"


def test_build_percent_encodes_reserved_characters() -> None:
    uri = build("a@example.com", subject="Re: a&b?")
    assert uri == "mailto:a@example.com?subject=Re:%20a%26b%3F"


def test_build_custom_headers() -> None:
    uri = build("a@example.com", headers={"In-Reply-To": "<abc@x>"})
    assert uri == "mailto:a@example.com?In-Reply-To=%3Cabc@x%3E"


def test_build_empty() -> None:
    assert build() == "mailto:"


def test_round_trip_preserves_every_field() -> None:
    original = Mailto(
        to=["a@example.com", "b@example.com"],
        cc=["c@example.com"],
        bcc=["d@example.com"],
        subject="Re: café & tea",
        body="Hello\nWorld",
        headers={"In-Reply-To": "<id@host>"},
    )
    uri = build(
        original.to,
        cc=original.cc,
        bcc=original.bcc,
        subject=original.subject,
        body=original.body,
        headers=original.headers,
    )
    assert parse(uri) == original
