"""The command reads standard input as UTF-8 bytes, whatever the locale, like an argument."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import mailtourl
from mailtourl._cli import main


def _pipe(data: bytes, *argv: str, encoding: str = "cp1252") -> tuple[int, str]:
    # A text stream over bytes, decoded by default with a code page, as on a Windows console.
    out = io.StringIO()
    stdin = io.TextIOWrapper(io.BytesIO(data), encoding=encoding)
    status = main(["parse", *argv], stdin=stdin, stdout=out)
    return status, out.getvalue()


@pytest.mark.parametrize("encoding", ["cp1252", "utf-8", "ascii"])
def test_piped_utf_8_reads_like_the_argument(encoding: str) -> None:
    uri = "mailto:a@x.example?subject=café ☃"
    status, out = _pipe(uri.encode() + b"\n", encoding=encoding)
    assert status == 0
    assert json.loads(out)["subject"] == "café ☃"


def test_a_byte_order_mark_is_skipped() -> None:
    status, out = _pipe(b"\xef\xbb\xbfmailto:a@x.example?subject=Hi\r\n", "--strict")
    assert status == 0
    assert json.loads(out)["subject"] == "Hi"


def test_bytes_that_are_not_utf_8_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    status, out = _pipe(b"mailto:a@x.example?subject=\xff\xfe", encoding="utf-8")
    assert (status, out) == (2, "")
    assert capsys.readouterr().err == "mailtourl: standard input is not UTF-8 at byte 27\n"


@pytest.mark.parametrize("pad", [" ", "\xa0", "\u3000", "\t"])
def test_strict_input_keeps_its_padding_on_standard_input(pad: str) -> None:
    for uri in (pad + "mailto:a@x.example", "mailto:a@x.example" + pad):
        assert _pipe(uri.encode(), "--strict")[0] == 2
        assert main(["parse", "--strict", uri], stdout=io.StringIO()) == 2


@pytest.mark.parametrize("end", ["", "\n", "\r\n"])
def test_one_line_ending_is_dropped(end: str) -> None:
    assert _pipe(f"mailto:a@x.example{end}".encode(), "--strict")[0] == 0


@pytest.mark.parametrize("end", ["\n\n", "\r\n\r\n", " \n", "\n\r\n"])
def test_more_than_one_line_ending_stays(end: str) -> None:
    assert _pipe(f"mailto:a@x.example{end}".encode(), "--strict")[0] == 2


def test_repeated_headers_all_reach_the_json() -> None:
    status, out = _pipe(b"mailto:?X=1&X=2&x=3")
    assert status == 0
    assert json.loads(out)["headers"] == [["X", "1"], ["X", "2"], ["x", "3"]]


def test_the_installed_command_reads_utf_8_from_a_pipe() -> None:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    env["PYTHONPATH"] = str(Path(mailtourl.__file__).resolve().parents[1])
    run = [sys.executable, "-m", "mailtourl", "parse"]
    good = subprocess.run(
        run, input="mailto:a@x.example?subject=café".encode(), capture_output=True, env=env
    )
    assert (good.returncode, json.loads(good.stdout)["subject"]) == (0, "café")
    bad = subprocess.run(run, input=b"mailto:?subject=\xff", capture_output=True, env=env)
    assert bad.returncode == 2
    assert bad.stderr.decode().strip() == "mailtourl: standard input is not UTF-8 at byte 16"
