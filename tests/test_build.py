"""The builder: canonical encoding, CRLF bodies and the input it refuses."""

from __future__ import annotations

import pytest

from mailtourl import MailtoError, build, is_address, parse


def test_build_single_recipient() -> None:
    assert build("jane@example.com") == "mailto:jane@example.com"


def test_build_empty() -> None:
    assert build() == "mailto:"
    assert build([], cc=[], bcc=None, headers={}) == "mailto:"


def test_build_with_subject_and_body() -> None:
    uri = build("jane@example.com", subject="Hello there", body="Line one")
    assert uri == "mailto:jane@example.com?subject=Hello%20there&body=Line%20one"


def test_every_body_line_break_becomes_crlf() -> None:
    uri = build(body="a\nb\r\nc\rd\n\ne")
    assert uri == "mailto:?body=a%0D%0Ab%0D%0Ac%0D%0Ad%0D%0A%0D%0Ae"
    assert parse(uri, strict=True).body == "a\r\nb\r\nc\r\nd\r\n\r\ne"


def test_build_multiple_recipients_and_cc_bcc() -> None:
    uri = build(["a@example.com", "b@example.com"], cc="c@example.com", bcc=["d@example.com"])
    assert uri == "mailto:a@example.com,b@example.com?cc=c@example.com&bcc=d@example.com"


def test_build_accepts_any_iterable_of_addresses() -> None:
    uri = build(iter(["a@x.example"]), cc=("b@x.example", "c@x.example"))
    assert uri == "mailto:a@x.example?cc=b@x.example,c@x.example"


def test_field_values_encode_the_reserved_characters() -> None:
    uri = build(subject="Re: a&b?c=d/e#f %g+h")
    assert uri == "mailto:?subject=Re:%20a%26b%3Fc%3Dd%2Fe%23f%20%25g%2Bh"


def test_field_values_keep_some_delims_raw() -> None:
    assert build(subject="!$'()*,;:@-._~") == "mailto:?subject=!$'()*,;:@-._~"


def test_addresses_encode_comma_and_the_sub_delims_the_rfc_named() -> None:
    uri = build(['"a,b"@x.example', "a&b@x.example", "a=b@x.example", "bill+ietf@x.example"])
    assert uri == "mailto:%22a%2Cb%22@x.example,a%26b@x.example,a%3Db@x.example,bill+ietf@x.example"


def test_an_at_sign_inside_the_local_part_is_encoded() -> None:
    assert build('"not@me"@example.org') == "mailto:%22not%40me%22@example.org"


def test_a_domain_literal_has_its_brackets_encoded() -> None:
    assert build("a@[192.0.2.1]") == "mailto:a@%5B192.0.2.1%5D"


@pytest.mark.parametrize("char", list("#%&/=?^`{|}"))
def test_build_refuses_a_domain_char_that_would_need_an_ascii_escape(char: str) -> None:
    address = f"a@x{char}y.example"
    assert not is_address(address)
    with pytest.raises(MailtoError, match="cannot be written in a domain name"):
        build(address)
    assert build(f"{char}@[x{char}]") == f"mailto:%{ord(char):02X}@%5Bx%{ord(char):02X}%5D"


def test_non_ascii_is_utf8_percent_encoded_with_upper_case_hex() -> None:
    uri = build("café@é.example", subject="ñ")
    assert uri == "mailto:caf%C3%A9@%C3%A9.example?subject=%C3%B1"


def test_build_custom_headers_from_a_mapping_or_pairs() -> None:
    expected = "mailto:a@x.example?In-Reply-To=%3Cabc@x%3E&Keywords=k"
    assert build("a@x.example", headers={"In-Reply-To": "<abc@x>", "Keywords": "k"}) == expected
    assert build("a@x.example", headers=[("In-Reply-To", "<abc@x>"), ("Keywords", "k")]) == expected


def test_header_names_keep_every_printable_ascii_but_colon() -> None:
    name = "".join(chr(code) for code in range(33, 127) if chr(code) != ":")
    uri = build(headers={name: "v"})
    assert parse(uri, strict=True).headers == ((name, "v"),)


@pytest.mark.parametrize("name", ["", "a:b", "a b", "café"])
def test_build_refuses_names_that_are_not_field_names(name: str) -> None:
    with pytest.raises(MailtoError, match="field name"):
        build(headers={name: "v"})


@pytest.mark.parametrize("name", ["to", "CC", "Bcc", "subject", "BODY"])
def test_build_refuses_a_header_owned_by_a_dedicated_argument(name: str) -> None:
    with pytest.raises(MailtoError, match="own argument"):
        build(headers={name: "a@x.example"})


def test_build_refuses_a_repeated_header() -> None:
    with pytest.raises(MailtoError, match="twice"):
        build(headers=[("Keywords", "a"), ("keywords", "b")])


@pytest.mark.parametrize(
    "address", ["", "Jane <jane@x.example>", "jane", "a b@x.example", "a@b@x.example", "a@"]
)
@pytest.mark.parametrize("slot", ["to", "cc", "bcc"])
def test_build_refuses_what_is_not_an_addr_spec(address: str, slot: str) -> None:
    with pytest.raises(MailtoError, match=f"^{slot}: "):
        build(**{slot: address})  # type: ignore[arg-type]


def test_build_refuses_an_unencodable_code_point() -> None:
    with pytest.raises(MailtoError, match="UTF-8"):
        build(subject="\ud800")
    with pytest.raises(MailtoError, match="UTF-8"):
        build(headers={"K": "\ud800"})
    with pytest.raises(MailtoError, match="UTF-8"):
        build(body="\udfff")
    with pytest.raises(MailtoError, match="not allowed"):
        build('"\ud800"@x.example')


@pytest.mark.parametrize(
    "call",
    [
        lambda: build(b"a@x.example"),  # type: ignore[arg-type]
        lambda: build([1]),  # type: ignore[list-item]
        lambda: build(subject=1),  # type: ignore[arg-type]
        lambda: build(body=1),  # type: ignore[arg-type]
        lambda: build(headers=[("a", 1)]),  # type: ignore[list-item]
        lambda: build(headers=["ab"]),  # type: ignore[list-item]
        lambda: build(headers=[("a", "b", "c")]),  # type: ignore[list-item]
    ],
)
def test_build_refuses_wrong_types_with_type_error(call: object) -> None:
    with pytest.raises(TypeError):
        call()  # type: ignore[operator]


def test_build_output_is_strictly_valid_and_reads_back() -> None:
    uri = build(
        ['"oh\\\\no"@example.org', "x@y.example"],
        cc="c@x.example",
        bcc="d@x.example",
        subject="Re: café & tea",
        body="Hello\r\nWorld",
        headers={"In-Reply-To": "<id@host>"},
    )
    result = parse(uri, strict=True)
    assert result.to == ('"oh\\\\no"@example.org', "x@y.example")
    assert result.subject == "Re: café & tea"
    assert result.body == "Hello\r\nWorld"
