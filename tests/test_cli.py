"""The mailtourl command, driven in process with injected streams."""

from __future__ import annotations

import io
import json

import pytest

from mailtourl._cli import main


def _run(*argv: str, stdin: str = "") -> tuple[int, str]:
    out = io.StringIO()
    status = main(list(argv), stdin=io.StringIO(stdin), stdout=out)
    return status, out.getvalue()


def test_parse_prints_every_field_as_json() -> None:
    status, out = _run("parse", "mailto:a@x.example?cc=c@x.example&subject=caf%C3%A9&K=v")
    assert status == 0
    assert out.endswith("\n") and out.isascii()
    assert json.loads(out) == {
        "to": ["a@x.example"],
        "cc": ["c@x.example"],
        "bcc": [],
        "subject": "café",
        "body": None,
        "headers": [["K", "v"]],
    }


def test_parse_reads_standard_input_when_the_uri_is_left_out() -> None:
    status, out = _run("parse", stdin="  mailto:a@x.example?body=hi\n")
    assert status == 0
    assert json.loads(out)["body"] == "hi"


def test_parse_safe_drops_unsafe_headers() -> None:
    status, out = _run("parse", "--safe", "mailto:?From=x@y.example&Keywords=k")
    assert status == 0
    assert json.loads(out)["headers"] == [["Keywords", "k"]]


def test_parse_strict_reports_the_error_and_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    status, out = _run("parse", "--strict", "mailto:a@x.example#top")
    assert (status, out) == (2, "")
    assert capsys.readouterr().err == "mailtourl: a mailto: URI takes no fragment at offset 18\n"


def test_parse_reports_header_injection(capsys: pytest.CaptureFixture[str]) -> None:
    status, _ = _run("parse", "mailto:?subject=a%0Ab")
    assert status == 2
    assert "header injection" in capsys.readouterr().err


def test_build_writes_the_uri() -> None:
    status, out = _run(
        "build",
        "--to",
        "a@x.example",
        "--to",
        "b@x.example",
        "--cc",
        "c@x.example",
        "--bcc",
        "d@x.example",
        "--subject",
        "Hi there",
        "--body",
        "one\ntwo",
        "--header",
        "In-Reply-To=<id@h>",
        "--header",
        "X-Eq=a=b",
    )
    assert status == 0
    assert out == (
        "mailto:a@x.example,b@x.example?cc=c@x.example&bcc=d@x.example&subject=Hi%20there"
        "&body=one%0D%0Atwo&In-Reply-To=%3Cid@h%3E&X-Eq=a%3Db\n"
    )


def test_build_with_nothing_prints_the_bare_scheme() -> None:
    assert _run("build") == (0, "mailto:\n")


@pytest.mark.parametrize(
    ("argv", "words"),
    [
        (["build", "--header", "NoEquals"], "NAME=VALUE"),
        (["build", "--to", "Jane <j@x.example>"], "to: "),
        (["build", "--subject", "a\nb"], "control character"),
    ],
)
def test_build_errors_exit_2(
    argv: list[str], words: str, capsys: pytest.CaptureFixture[str]
) -> None:
    status, out = _run(*argv)
    assert (status, out) == (2, "")
    err = capsys.readouterr().err
    assert err.startswith("mailtourl: ") and words in err


def test_a_command_is_required(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2
    assert "required" in capsys.readouterr().err
