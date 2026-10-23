"""The command with missing streams, odd arguments and the help it prints."""

from __future__ import annotations

import io
import sys

import pytest

from mailtourl._cli import main


def test_no_standard_input_exits_2_with_one_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # sys.stdin is None under a closed descriptor, pythonw, a service or a scheduled task.
    monkeypatch.setattr(sys, "stdin", None)
    assert main(["parse"], stdout=io.StringIO()) == 2
    assert capsys.readouterr().err == "mailtourl: no standard input\n"


@pytest.mark.parametrize(
    "argv", [["build", "--to", "a@x.example"], ["parse", "mailto:a@x.example"]]
)
def test_no_standard_output_exits_2_with_one_line(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    assert main(argv) == 2
    assert capsys.readouterr().err == "mailtourl: no standard output\n"


def test_without_standard_error_the_reason_never_lands_on_standard_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stderr", None)
    assert main(["parse", "not a uri"]) == 2
    assert capsys.readouterr().out == ""


def test_no_standard_streams_at_all_still_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("stdin", "stdout", "stderr"):
        monkeypatch.setattr(sys, name, None)
    assert main(["parse"]) == 2


def test_a_header_without_equals_never_echoes_its_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = ["build", "--to", "a@x.example", "--header", "X-Auth-Token: s3cr3t-0123456789abcdef"]
    assert main(argv, stdout=io.StringIO()) == 2
    err = capsys.readouterr().err
    assert err == "mailtourl: --header expects NAME=VALUE\n"
    assert "s3cr3t" not in err


def test_a_header_name_that_is_not_a_field_name_never_echoes_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = ["build", "--header", "Authorization: Bearer s3cr3t=1"]
    assert main(argv, stdout=io.StringIO()) == 2
    err = capsys.readouterr().err
    assert err == "mailtourl: character ':' not allowed in a header field name\n"


def test_the_bad_byte_is_counted_from_the_start_of_the_input_bom_included(
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdin = io.TextIOWrapper(io.BytesIO(b"\xef\xbb\xbfmailto:?subject=\xff"), encoding="utf-8")
    assert main(["parse"], stdin=stdin, stdout=io.StringIO()) == 2
    assert capsys.readouterr().err == "mailtourl: standard input is not UTF-8 at byte 19\n"


def test_an_empty_uri_argument_is_parsed_not_replaced_by_stdin(
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = io.StringIO()
    assert main(["parse", ""], stdin=io.StringIO("mailto:a@x.example\n"), stdout=out) == 2
    assert out.getvalue() == ""
    assert capsys.readouterr().err == "mailtourl: not a mailto: URI at offset 0\n"


def test_the_safe_option_says_it_applies_mailto_safe(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["parse", "--help"])
    shown = " ".join(capsys.readouterr().out.split())
    assert "--safe apply Mailto.safe(): keep only what is safe in general and to_uri writes" in (
        shown
    )
